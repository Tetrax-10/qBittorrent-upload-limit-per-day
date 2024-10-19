# qBittorrent-upload-limit-per-day

A Python script that automatically runs in the background on startup to track qBittorrent's upload data usage. It pauses all seeding torrents if the upload limit is reached. The script resets at 12:01 AM daily and resumes all torrents.

## Setup

1. Download the [qb_upload_limit_per_day.py](https://github.com/Tetrax-10/qBittorrent-upload-limit-per-day/blob/main/qb_upload_limit_per_day.py) script.
2. Place it inside **`C:\qBittorrent-upload-limit-per-day`** folder.
3. Download the [requirements.txt](https://github.com/Tetrax-10/qBittorrent-upload-limit-per-day/blob/main/requirements.txt), place it in the same folder, and run **`pip install -r requirements.txt`** to install the necessary libraries. 
3. Download the [qBittorrent-upload-limit-per-day startup.xml](https://github.com/Tetrax-10/qBittorrent-upload-limit-per-day/blob/main/qBittorrent-upload-limit-per-day%20startup.xml) file.
4. Now open the xml file and replace `C:\path\to\your\python.exe` with your python.exe path. Tip: Run **`where python`** in cmd to get python.exe path.
5. Import this xml as a task in **task scheduler**.
6. To change the script's configuration open `qb_upload_limit_per_day.py` and edit the **Configuration** part.
7. Run `pip install requests schedule` and restart your system.
8. Done, the script will start running in background on startup.

*Note*: Make sure qBittorrent's WebUI is enabled and **Bypass authentication for clients on localhost** is checked inside `qBittorrent settings => Web UI => Authentication`.

To check if the script has been installed and working properly, go to `C:\qBittorrent-upload-limit-per-day` and if you see a file named `qb_upload_data_usage_cache.json` been created, then the scripts work perfectly fine, else message me on [reddit](https://www.reddit.com/user/Raghavan_Rave10/) I can help you set it up.

This script does work on Linux and Mac. But the Task scheduler (Xml) is limited to Windows only.

## Authentification

In order to allow the script to connect to servers that require authentification, you need to:
1. Change `AUTH_ENABLED` in `qb_upload_limit_per_day.py` to `True`.
2. Create `secrets.json` in the same folder as the script.
3. Add your username and password to `secrets.json` in the following format:
```json
{
    "username" : "<your username>",
    "password" : "<your password>"
}
```

## To do

1. Add instructions for linux and mac scheduler.
