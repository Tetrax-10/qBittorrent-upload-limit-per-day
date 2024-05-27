# qBittorrent-upload-limit-per-day

A python script that runs in background to track the qBittorrent's upload data usage and pauses all seeding torrents if the limit has reached.

## Setup

1. Download the [qb_upload_limit_per_day.py](https://github.com/Tetrax-10/qBittorrent-upload-limit-per-day/blob/main/qb_upload_limit_per_day.py) script.
2. Place it inside **`C:\qBittorrent-upload-limit-per-day`** folder.
3. Download the [qBittorrent-upload-limit-per-day startup.xml](https://github.com/Tetrax-10/qBittorrent-upload-limit-per-day/blob/main/qBittorrent-upload-limit-per-day%20startup.xml) file.
4. Now open the xml file and replace `C:\path\to\your\python.exe` with your python.exe path. Tip: Run **`where python`** in cmd to get python.exe path.
5. Import this xml as a task in **task scheduler**.
6. To change the script's configuration open `qb_upload_limit_per_day.py` and edit the **Configuration** part.
7. Run `pip install requests schedule` and restart your system. Done, the script will be running in background.

Note: Make sure qBittorrent's WebUI is enabled and **Bypass authentication for clients on localhost** is checked inside `qBittorrent settings => Web UI => Authentication`.

To check if the script has been installed and working properly, go to `C:\qBittorrent-upload-limit-per-day` and if you see a file named `qb_upload_data_usage_cache.json` been created, then the scripts work perfectly fine.

This script does work with Linux and Mac. But the Task scheduler is limited to Windows only.

## To do

1. Implement authentication with username and password.
