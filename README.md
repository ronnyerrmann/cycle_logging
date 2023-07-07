# cycle_logging
App to log daily exercise and and to analyse the data.

This is the Django based version. Initially, I started with a MySQL Database and a PHP and Javascript front-end.
That version can be fund under https://github.com/ronnyerrmann/cycle_logging_mysql_based.
This repository has not yet been cleaned up from some of the old code.

### Show results in a Webbrowser:
To install Django you can follow: [https://developer.mozilla.org/en-US/docs/Learn/Server-side/Django/development_environment]

The following packages are required
```
pip install requests urllib3 django pandas plotly
```

The tests can be executed by running in folder `cycle_logging/cycle_django`:
```commandline
python manage.py test
```

To start a test server (`DEBUG = True`):
```commandline
python3 manage.py runserver 127.0.0.1:8000
```

For production (`DEBUG = False`) and a Gunicorn server:
```commandline
gunicorn cycle_django.wsgi -b  0.0.0.0:8002
```

To allow connections from outside the host machine (example for port 8002)
```commandline
sudo ufw allow 8002
```

The website runs on a test server: [Cycle Results (Django)](http://ronnyerrmann.ddns.net:8000).

### Learnings
* Django makes the development easier only if it can manage tables

### Final notes:
If you tried some or all of the scripts, let me know how it went: Ronny Errmann: ronny.errmann@gmail.com

