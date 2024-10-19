import requests
import json
import time
import datetime
import schedule

from os.path import exists

# Configuration
UPLOAD_LIMIT = 50  # Upload limit in GB (per day)
QB_URL = "http://localhost:8080"  # qBittorrent Web UI URL
CHECK_INTERVAL = 10  # In seconds
RESET_TIME = "00:01"  # HH:MM ("00:01" will reset exactly at 12:01.AM)
AUTH_ENABLED = False  # True | False

# Global vars
previous_session_upload_data_usage = 0.0
current_session_upload_data_usage = 0.0
last_event_upload_data_usage = 0.0
current_session_previous_day_upload_data_usage = 0.0
qb_online_status = False

def login():
    """
    Performs login to qBittorrent WebUI using data from secrets.json
    If login is successful, the resulting cookies are stored in 
    cookies.json file, so that the other methods can access them 
    for authentification
    """
    file_name = "secrets.json"
    if not exists(file_name):
        return False, f"{file_name} with your username and password doesn't exist."
    try:
        with open(file_name) as f:
            secrets = json.load(f)
            if "username" not in secrets:
                return False, f"username field is not in {file_name}"
            if "password" not in secrets:
                return False, f"password field is not in {file_name}"
    except Exception as e:
        return False, f"Error {e} occured while reading JSON"

    response = requests.post(f"{QB_URL}/api/v2/auth/login",data={"username":secrets["username"],"password":secrets["password"]})
    if response.status_code != 200:
        return False, response.text
    if not response.text.lower().startswith("ok"):
        return False, "Wrong username or password"
    
    with open("cookies.json","w") as f:
        json.dump(response.cookies.get_dict(), f)
    
    return True, ""

def print_login_failure(login_res):
    """
    Prints the reason the login failed and a template for secrets.json

    :param login_res: -- tuple of two elements, where first - if login
    was successful, second - failure message  
    """
    print("Login failed: ", login_res[1])
    print('Make sure secrets.json has the following format\n'
        '{\n'
        '    "username" : "<your username>",\n'
        '    "password" : "<your password>"\n'
        '}')
    
def request_with_login(func, *args, **kwargs):
    """
    Performs a request with the added information for authentification.
    If the request fails with 403, the function does a second login attempt
    to generate new cookies. If after that the authentification still fails,
    the program exits, as the user need to fix the credentials.

    AUTH_ENABLED is False, the reqular request is performed instead.
    :param func: -- function to perform the request, such as requests.get
    :param args: -- fuction parameters
    :param kwargs: -- function keyword parameters
    """
    if not AUTH_ENABLED:
        return func(*args, **kwargs)
    if not exists("cookies.json"):
        res = login()
        if not res[0]:
            print_login_failure(res)
            exit(1)
    with open("cookies.json") as f:
        cookies = json.load(f)

    response = func(*args, **kwargs, cookies=cookies)
    
    if response.status_code == 403:
        print("Token expired, requesting new one")
        res = login()
        if not res[0]:
            print_login_failure(res)
            exit(1)
        with open("cookies.json") as f:
            cookies = json.load(f)
        response = func(*args, **kwargs, cookies=cookies)
    
    return response

def get_upload_data_usage():
    global qb_online_status, current_session_previous_day_upload_data_usage

    try:
        response = request_with_login(requests.get, f"{QB_URL}/api/v2/transfer/info")

        qb_online_status = True

        if response.ok:
            return (response.json().get("up_info_data", 0)) / (1024**3)  # Convert bits to GB
        else:
            raise Exception("Response wan't ok")
    except:
        qb_online_status = False
        current_session_previous_day_upload_data_usage = 0.0
        print("Failed to get upload data usage!")
        return 0.0


def pause_all_seeding_torrents():
    try:
        seeding_torrents = request_with_login(requests.get, f"{QB_URL}/api/v2/torrents/info?filter=seeding").json()
        if len(seeding_torrents):
            for torrent in seeding_torrents:
                request_with_login(requests.post, f"{QB_URL}/api/v2/torrents/pause", data={"hashes": torrent["hash"]})
            print("Daily upload data usage limit reached, all seeding torrents paused")
    except:
        pass  # qBittorrent is offline


def resume_all_paused_torrents():
    try:
        paused_torrents = request_with_login(requests.get, f"{QB_URL}/api/v2/torrents/info?filter=paused").json()
        if len(paused_torrents):
            for torrent in paused_torrents:
                request_with_login(requests.post, f"{QB_URL}/api/v2/torrents/resume", data={"hashes": torrent["hash"]})
            print("Daily upload data usage reseted, all torrents resumed")
    except:
        pass  # qBittorrent is offline


def load_data_from_cache():
    try:
        with open("qb_upload_data_usage_cache.json", "r") as file:
            return json.load(file)
    except:
        print("can't load data from cache")
        return {"date": str(datetime.date.today()), "uploaded": 0.0}


def save_data_to_cache(data):
    with open("qb_upload_data_usage_cache.json", "w") as file:
        json.dump(data, file)


def check_previous_session_upload_data_usage():
    global previous_session_upload_data_usage

    data = load_data_from_cache()
    if data["date"] == str(datetime.date.today()):
        previous_session_upload_data_usage = data["uploaded"]


def check_and_update_upload_data_usage():
    global previous_session_upload_data_usage, current_session_upload_data_usage, qb_online_status, last_event_upload_data_usage

    data = load_data_from_cache()
    today = str(datetime.date.today())

    current_session_upload_data_usage = get_upload_data_usage()

    # if qbittorrent session continues past midnight then subtract the previous day usage
    if current_session_previous_day_upload_data_usage != 0.0:
        current_session_upload_data_usage = current_session_upload_data_usage - current_session_previous_day_upload_data_usage

    total_upload_data_usage = 0.0

    if qb_online_status == False:
        # If qBittorrent went offline then consider the last upload data usage recorded when it was online
        total_upload_data_usage = previous_session_upload_data_usage = previous_session_upload_data_usage + last_event_upload_data_usage
    else:
        total_upload_data_usage = previous_session_upload_data_usage + current_session_upload_data_usage

    last_event_upload_data_usage = current_session_upload_data_usage

    if total_upload_data_usage >= UPLOAD_LIMIT:
        pause_all_seeding_torrents()

    print("Today's upload data usage:")
    print(f"Previous sessions: {previous_session_upload_data_usage}")
    print(f"Current session: {current_session_upload_data_usage}")
    print(f"Total: {total_upload_data_usage}")
    print("---------------------------")

    data["date"] = today
    data["uploaded"] = total_upload_data_usage
    save_data_to_cache(data)


def reset_daily_usage():
    global previous_session_upload_data_usage, current_session_upload_data_usage, last_event_upload_data_usage, current_session_previous_day_upload_data_usage

    data = {"date": str(datetime.date.today()), "uploaded": 0.0}
    save_data_to_cache(data)

    current_session_previous_day_upload_data_usage += current_session_upload_data_usage

    previous_session_upload_data_usage = 0.0
    current_session_upload_data_usage = 0.0
    last_event_upload_data_usage = 0.0

    resume_all_paused_torrents()


if __name__ == "__main__":
    check_previous_session_upload_data_usage()
    schedule.every(CHECK_INTERVAL).seconds.do(check_and_update_upload_data_usage).run()
    schedule.every().day.at(RESET_TIME).do(reset_daily_usage)
    # schedule.every(5).minutes.do(reset_daily_usage)  # reset schedule for development

    while True:
        schedule.run_pending()
        time.sleep(CHECK_INTERVAL)
