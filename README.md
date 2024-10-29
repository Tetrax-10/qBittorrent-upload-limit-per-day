# qBittorrent-upload-limit-per-day

A Python script that automatically runs in the background on startup to track qBittorrent's upload data usage. It pauses all seeding torrents if the upload limit is reached. The script resets at 12:01 AM daily and resumes all torrents.

## Running the script

The script requires Python 3.8+ to run. You can use [pyenv](https://github.com/pyenv/pyenv) in case you can't install a higher Python version system-wide.

The script requires qBittorrent WebUI to be activated: Tools -> Options -> Web UI -> Enable "Web User Interface (Remote Control)"

1. Install the libraries with `pip install -r requirements.txt`
2. Run `python python qb_upload_limit_per_day.py`

In case you want to run the script on Linux unattended, you can use `nohup`:

`nohup python -u qb_upload_limit_per_day.py >> run.log 2>&1 `

This will allow the script to keep running even after a shell was killed. `stdout` and `stderr` are redirected to `run.log`. 

## Setup for Windows scheduler

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

## Authentication 

In order to allow the script to connect to servers that require authentication, you need to change the `[AUTH]` section of `config.conf`:
```ini
[AUTH]
username = <your username>
password = <your password>
```

## Config parameters
The config parameters are stored in `config.conf`.

Settings section:
- `upload_limit` - maximum number of data in GBs that can be uploaded per day. (Default: `50` Gb) 
- `qb_url` - qBittorent Web UI URL (Default: `http://localhost:8080`)
- `check_interval` - how often the script checks upload usage, in seconds. It is not recommended to set to lower than 60 seconds, as qBittorrent doesn't update its statistics often (Default: `60` s) 
- `reset_time` - time when the daily usage is reset. The format is HH:MM (Default: `00:01`)
authentication for clients on localhost" (Default: `false`)
- `timeout` - when requests to WebUI timeout, in s. Raise it if the connection to the qBittorrent server is slow (Default: `10` s)

Auth section:
- `username` - a username used for authentication (blank for no authentication) (Default: blank)
- `password` - a password used for authentication (blank for no authentication) (Default: blank)


Default config:

```ini
[SETTINGS]
upload_limit = 50
qb_url = http://localhost:8080
check_interval = 60
reset_time = 00:01
timeout = 10

[AUTH]
username = 
password = 
```

## To do

1. Add instructions for linux and mac scheduler.
