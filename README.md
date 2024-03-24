# cycle_logging
App to log daily exercise and and to analyse the data.

This is the Django based version. Initially, I started with a MySQL Database and a PHP and Javascript front-end.
That version can be fund under https://github.com/ronnyerrmann/cycle_logging_mysql_based.
This repository has not yet been cleaned up from some of the old code.

### Show results in a Webbrowser:
To install Django you can follow: [https://developer.mozilla.org/en-US/docs/Learn/Server-side/Django/development_environment]

The following packages are required
```
pip install requests urllib3 django pandas plotly gpxpy django-leaflet psutil
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
In the deploy script, the `SETTINGS_FOLDERS` needs to be adjusted to give a path that contains `django_admin_password.txt` and `django_secret_key.txt`.
The files contain a single line with a good password and key, respectively.
In the deploy script the `DATABASE_BACKUP_FOLDER` needs to be adjusted if a database dump should be read on startup of the gunicorn server.
The backup of the database will be stored in the folder from which the deploy script was executed, under `cycle_logging/cycle_django/backup_database/`.
The log of the migrations and the gunicorn server are stored under `cycle_logging/cycle_django/docker_run.log`.

### Live version
The website runs on a test server: [Cycle Results](http://109.123.245.13:8314).

### Learnings
* Django makes the development easier only if it can manage tables
* If the apt version of docker can't connect to the internet inside the container (e.g. when running pip), use the snap version instead of spending hours.

### Final notes:
If you tried some or all of the scripts, let me know how it went: Ronny Errmann: ronny.errmann@gmail.com

