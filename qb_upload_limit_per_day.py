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
AUTH_ENABLED = False
TIMEOUT = 10

PAUSED_TORRENT_SAVE_FILE = "qb_torrents.json"
# Global vars
qb_online_status = True
initial_upload_data_today = None
update_job = None
reset_job = None


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
        return func(*args, **kwargs, timeout=TIMEOUT)
    if not exists("cookies.json"):
        res = login()
        if not res[0]:
            print_login_failure(res)
            exit(1)
    with open("cookies.json") as f:
        cookies = json.load(f)

    response = func(*args, **kwargs, cookies=cookies, timeout=TIMEOUT)
    
    if response.status_code == 403:
        print("Token expired, requesting new one")
        res = login()
        if not res[0]:
            print_login_failure(res)
            exit(1)
        with open("cookies.json") as f:
            cookies = json.load(f)
        response = func(*args, **kwargs, cookies=cookies, timeout=TIMEOUT)
    
    return response


def get_upload_data_usage():
    response = request_with_login(requests.get, f"{QB_URL}/api/v2/sync/maindata")

    if response.ok:
        resp_json = response.json()
        upload_data_gbs = resp_json.get("server_state").get("alltime_ul") / (1024**3)
        return upload_data_gbs
    else:
        raise Exception("Response wan't ok")

  
def pause_all_seeding_torrents():
    try:
        seeding_torrents = request_with_login(requests.get, f"{QB_URL}/api/v2/torrents/info?filter=seeding").json()
        hashes = set([torrent["hash"] for torrent in seeding_torrents])
        if exists(PAUSED_TORRENT_SAVE_FILE):
            with open(PAUSED_TORRENT_SAVE_FILE) as f:
                previous_hashes = set(json.load(f))
            hashes = hashes.union(previous_hashes)
        with open(PAUSED_TORRENT_SAVE_FILE, "w") as file:
            json.dump(list(hashes), file)

        if len(seeding_torrents):
            for torrent in seeding_torrents:
                request_with_login(requests.post, f"{QB_URL}/api/v2/torrents/pause", data={"hashes": torrent["hash"]})
            print("Daily upload data usage limit reached, all seeding torrents paused")
        return True
    except:
        return False  # qBittorrent is offline


def resume_all_paused_torrents():
    try:
        paused_torrents = request_with_login(requests.get, f"{QB_URL}/api/v2/torrents/info?filter=paused").json()
        paused_hashes = set([torrent["hash"] for torrent in paused_torrents])
        hashes = paused_hashes
        if exists(PAUSED_TORRENT_SAVE_FILE):
            with open(PAUSED_TORRENT_SAVE_FILE) as f:
                seeding_hashes = set(json.load(f))
            with open(PAUSED_TORRENT_SAVE_FILE,"w") as f:
                f.write("[]")
            preserved_hashed = paused_hashes.intersection(seeding_hashes)
            hashes = preserved_hashed
        
        if len(hashes):
            for hash in hashes:
                request_with_login(requests.post, f"{QB_URL}/api/v2/torrents/resume", data={"hashes": hash})
        return True
    except:
        return False  # qBittorrent is offline


def load_data_from_cache():
    try:
        with open("qb_upload_data_usage_cache.json", "r") as file:
            return json.load(file)
    except:
        print("can't load data from cache, so creating one...")
        data = []
        save_data_to_cache(data)
        return data


def save_data_to_cache(data):
    with open("qb_upload_data_usage_cache.json", "w") as file:
        json.dump(data, file)


def update_usage_for_date(date):
    global initial_upload_data_today

    date_str = str(date)
    data = load_data_from_cache()
    initial_usage_today = get_upload_data_usage()

    # a safety check to ensure we don't add current date twice
    date_present = False
    for values in data:
        if values["date"] == date_str:
            date_present = True
            if values["uploaded"] > initial_usage_today:
                values["uploaded"] = initial_usage_today
            else:
                initial_usage_today = values["uploaded"]
            break
    
    if not date_present:
        data.append({"date": date_str, "uploaded": initial_usage_today})
    
    initial_upload_data_today = initial_usage_today
    save_data_to_cache(data)


def check_saved_torrents():
    if not exists(PAUSED_TORRENT_SAVE_FILE):
        return
    
    with open(PAUSED_TORRENT_SAVE_FILE) as f:
        saved_torrents = json.load(f)
    total_upload_data = get_upload_data_usage()
    today_upload = total_upload_data - initial_upload_data_today
    if len(saved_torrents) > 0 and today_upload < UPLOAD_LIMIT:
        resume_all_paused_torrents()
        print("Paused torrents that should be running were found and resumed.")

      
def check_previous_session_upload_data_usage():
    global initial_upload_data_today

    data = load_data_from_cache()

    cur_date = datetime.date.today()  
    cur_time = datetime.datetime.now().strftime('%H:%M:%S')
    if cur_time < RESET_TIME:
        # if reset haven't happened today yet, we need to check
        # the usage from yesterday, not today
        cur_date -= datetime.timedelta(1)
    # if the current date is not saved, we save the current 
    # upload as a baseline
    if len(data) == 0 or data[-1]["date"] != str(cur_date):
        update_usage_for_date(cur_date)
    else:
        initial_upload_data_today = data[-1]["uploaded"]


def get_normal_update_job():
    return schedule.every(CHECK_INTERVAL).seconds.do(check_and_update_upload_data_usage)


def get_normal_reset_job():
    return schedule.every().day.at(RESET_TIME).do(reset_daily_usage)


def check_and_update_upload_data_usage():
    global initial_upload_data_today, update_job
    try:
        total_upload_data = get_upload_data_usage()
    except requests.Timeout:
        print("Request time-out: qBittorrent appears to be offline")
        return
    except requests.exceptions.ConnectionError as e:
        print("Request failed, qBittorrent appears to be offline:\n", e)
        return
    
    upload_data_today = total_upload_data - initial_upload_data_today

    if upload_data_today >= UPLOAD_LIMIT:
        if not pause_all_seeding_torrents():
            print("qBittorrent seems to be offline, can't stop torrents.")
            return

    now = datetime.datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

    print(dt_string)
    print(f"Total upload: {total_upload_data:.2f}")
    print(f"Today's upload data usage: {upload_data_today:.2f}")
    print("---------------------------")


def reset_daily_usage():
    global update_job, reset_job, qb_online_status

    # try except is necessary if qBittorrent is offline when reset_daily_usage
    # is called. In such case we retry the reset_daily_usage until the requests
    # are successful
    try:
        # make sure that the update is canceled to avoid collisions
        schedule.cancel_job(update_job)
        date = datetime.date.today()
        update_usage_for_date(date)

        if resume_all_paused_torrents():
            if not qb_online_status:
                # if the serfver was offline, we need to cancel the rerty job
                schedule.cancel_job(reset_job)
                reset_job = get_normal_reset_job()
                qb_online_status = True
            update_job = get_normal_update_job()
            update_job.run()
            print("Daily upload data usage reset, all torrents resumed")
        else:
            raise Exception()
    except Exception:
        print("qBittorrent seems to be offline, can't restart torrents.")
        if qb_online_status:
            qb_online_status = False
            reset_job = schedule.every(CHECK_INTERVAL).seconds.do(reset_daily_usage).run()


if __name__ == "__main__":
    check_previous_session_upload_data_usage()
    check_saved_torrents()
    
    update_job = get_normal_update_job()
    reset_job = get_normal_reset_job()

    update_job.run()
    # schedule.every(5).minutes.do(reset_daily_usage)  # reset schedule for development

    while True:
        schedule.run_pending()
        time.sleep(CHECK_INTERVAL)
