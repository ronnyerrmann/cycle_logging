# cycle_logging
App to log daily exercise and and to analyse the data.

This is the Django based version. Initially, I started with a MySQL Database and a PHP and Javascript front-end.
That version can be fund under https://github.com/ronnyerrmann/cycle_logging_mysql_based.
This repository has not yet been cleaned up from some of the old code.

### Show results in a Webbrowser:
To install Django you can follow: [https://developer.mozilla.org/en-US/docs/Learn/Server-side/Django/development_environment]

The following packages are required
```
pip install requests urllib3 django pandas plotly gpxpy django-leaflet psutil python-srtm Pillow
```

To create the environment:
```commandline
python manage.py makemigrations
python manage.py migrate
```

The tests can be executed by running in folder `cycle_logging/cycle_django`:
```commandline
python manage.py test
```

To start a test server (`DEBUG = True`):
```commandline
python3 manage.py runserver 127.0.0.1:8000
```

For production (`DEBUG = False`, which can be set by environment `IS_PRODUCTION=True`) and a Gunicorn server:
```commandline
gunicorn cycle_django.wsgi -b  0.0.0.0:8002
```

To allow connections from outside the host machine (example for port 8002)
```commandline
sudo ufw allow 8002
```
### Deploy to production in a Docker environment
The deploy process, including git clone, pull, creation of a docker container, and start of the gunicorn server can be done with
```commandline
python3 path/to/deploy.py
```
The repository will be cloned into the current folder. 
In the deployment script, the `SETTINGS_FOLDERS` needs to be adjusted to give a path that contains `django_admin_password.txt` and `django_secret_key.txt`.
The files contain a single line with a good password and key, respectively.
In the deployment script the `DATABASE_BACKUP_FOLDER` needs to be adjusted if a database dump should be read on startup of the gunicorn server.
If optional own pictures should be shown, `PHOTO_FOLDER` needs to be adjusted.
If optional SRTM tiles (or other tiles) should be shown, the `TILES_FOLDERS` variable needs to be adjusted. 
The backup of the database will be stored in the folder from which the deployment script was executed, under `cycle_logging/cycle_django/backup_database/`. If the application is run in a docker environment, this folder should be backed up before the container is destroyed.
The log of the migrations and the gunicorn server are stored under `cycle_logging/cycle_django/docker_run.log`.

### Live version
The website runs on a test server: [Cycle Results](http://109.123.245.13:8314).

### Using SRTM:
* There was a time, when the SRTM data could be accessed from a US government server through an API. That option is long gone.
* The implemented solution uses https://pypi.org/project/python-srtm/ and requires the path to the SRTM data being set: `export SRTM1_DIR=/path/to/srtm1/` and `export SRTM3_DIR=/path/to/srtm3/` .
* The SRTM data needs to be stored as htg or htg.zip files. I used `get_srtm_hgt_files.py` to download the files.
* Finally, the SRTM htg files can be zipped using `for file in *.htg; do zip "${file}.zip" "$file" && rm "$file" && echo "$file has been zipped into ${file}.zip"; done` .
* GPS files that were loaded without SRTM data won't get SRTM data automatically. They need to be removed, so they will be loaded again.
* Elevations below 0 will have an unsigned integer (16 bit) buffer underflow, elevations without a reading will end up with 32k.
* **Create Tiles**
  * run `./create_tiles.sh` after adjusting the top parameters and the areas you want to serve at the bottom of the file
  * if run in development mode, the tiles folder will be linked under `cycle_django/cycle/static/tiles`

### Learnings
* Django makes the development easier only if it can manage tables
* If the apt version of docker can't connect to the internet inside the container (e.g. when running pip), use the snap version instead of spending hours.

### Final notes:
If you tried some or all of the scripts, let me know how it went: Ronny Errmann: ronny.errmann@gmail.com

