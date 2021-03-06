Flask based application for downloading mp3 from youtube/soundcloud. This application download files thru youtube-dl, convert them using ffmpeg/ffplay/ffprobe, provides opportunity to insert some tags using Spotify and Itunes API to receive this information and also some functional to download playlists(available only for youtube).

# Installation

Ensure that you have installed one of specified file converters and python 3.8+

### Installing required libraries
```
pip3 install -r requirments.txt
```

### Database initialization
```
flask db init
flask db migrate
flask db upgrade
```

### Variables configurating
Before start you should create .env file and set some variables in it or set them directly in config.py

Filling .env example
```
SECRET_KEY='secret'
YOUTUBE_API_KEY=
MAIL_SERVER=smtp.googlemail.com
MAIL_PORT=587
MAIL_USE_TLS=1
MAIL_USERNAME=
MAIL_PASSWORD=
SPOTIFY_UID=
SPOTIFY_SECRET=
```

## config.py settings
* ALLOWED_DURATION - max file duration time
* EXPIRATION_TIME - user token expiration time
* MAX_PLAYLIST_ITEMS - max number of playlist items to be downloaded at once
* PLAYLIST_PART_SIZE - size of part archive in files
* PLAYLIST_LIVE_TIME - time interval for playlist items to be guaranteed available for downloading
* MAIN_TIMER_DELTA - time interval for triggering main timer
* UNCONFIRMED_ACC_EXPIRATION_TIME - time interval for unconfirmed accounts to be in database

# Tests
```
pytest -v
```

Some tests use information from the Internet and changing it may cause them to fail

# Background tasks
If you want to run background tasks using celery you should install redis or other service(in case if that is not redis change configuration in config.py).

Celery worker start:
```
celery worker -A app.celery -c 2 -l info
```
There also support for background tasks in thread mode, if you want it just disable celery in config.py

# Entry point
```
python3 run_app.py
```
