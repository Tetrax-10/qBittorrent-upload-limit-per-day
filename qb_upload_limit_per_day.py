import requests
import json
import time
import datetime
import schedule


# Configuration
UPLOAD_LIMIT = 50  # Upload limit in GB (per day)
QB_URL = "http://localhost:8080"  # qBittorrent Web UI URL
CHECK_INTERVAL = 10  # In seconds
RESET_TIME = "00:01"  # HH:MM ("00:01" will reset exactly at 12:01.AM)


# Global vars
previous_session_upload_data_usage = 0.0
current_session_upload_data_usage = 0.0
last_event_upload_data_usage = 0.0
current_session_previous_day_upload_data_usage = 0.0
qb_online_status = False


def get_upload_data_usage():
    global qb_online_status, current_session_previous_day_upload_data_usage

    try:
        response = requests.get(f"{QB_URL}/api/v2/transfer/info")

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
        seeding_torrents = requests.get(f"{QB_URL}/api/v2/torrents/info?filter=seeding").json()
        if len(seeding_torrents):
            for torrent in seeding_torrents:
                requests.post(f"{QB_URL}/api/v2/torrents/pause", data={"hashes": torrent["hash"]})
            print("Daily upload data usage limit reached, all seeding torrents paused")
    except:
        pass  # qBittorrent is offline


def resume_all_paused_torrents():
    try:
        paused_torrents = requests.get(f"{QB_URL}/api/v2/torrents/info?filter=paused").json()
        if len(paused_torrents):
            for torrent in paused_torrents:
                requests.post(f"{QB_URL}/api/v2/torrents/resume", data={"hashes": torrent["hash"]})
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
