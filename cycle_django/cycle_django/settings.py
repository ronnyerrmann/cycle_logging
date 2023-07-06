"""
Django settings for cycle_django project.

Generated by 'django-admin startproject' using Django 3.2.12.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""
import os
import requests
import socket
import sys
import urllib3
from typing import Union, List

from my_base import BASE_DIR, Logging, Mysqlset, MYSQL_SETTINGS_DIR

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

logger = Logging.setup_logger(__name__)


def current_public_ip() -> Union[str, None]:
    """ Returns the public IP
    """
    endpoint = 'https://ipinfo.io/json'
    try:
        response = requests.get(endpoint, verify=True)
    except (ConnectionError, requests.exceptions.ConnectionError, urllib3.exceptions.MaxRetryError,
            urllib3.exceptions.NewConnectionError, socket.gaierror) as e:
        logger.warning(f"Can't connect to {endpoint}, Problem: {e}")
        return None

    if response.status_code != 200:
        logger.warning(f"Status: {response.status_code} Problem with the request.")
        return None

    data = response.json()
    logger.info(f"data: {data}, ip: {data.get('ip')}")

    return data.get("ip")

def current_local_hostname_ip() -> List[str]:
    hostname = socket.getfqdn()
    local_ip = socket.gethostbyname_ex(hostname)[2][0]  # 127.0.0.1
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(('10.254.254.254', 1))
        network_ip = s.getsockname()[0]
    except Exception:
        network_ip = '127.0.0.1'
    finally:
        s.close()
    return [hostname, local_ip, network_ip]


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
DEBUG = False

# Public IP might update while the server is up
ALLOWED_HOSTS = ["ronnyerrmann.ddns.net", current_public_ip()] + current_local_hostname_ip()
logger.info(f"Allowed hosts: {ALLOWED_HOSTS}")

if DEBUG:
    SECRET_KEY = 'django-insecure-ka^qzl%4!36p1xn(losx#7bu5_@%ropmewdj#)cnoha4m@-qxf'
else:
    with open(MYSQL_SETTINGS_DIR + "/django_secret_key.txt") as f:
        SECRET_KEY = f.read().strip()

if 'runserver' not in sys.argv and False:
    # SSL does not work, but as long as I won't use the remote version, that's ok
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    logger.info("Enabled secure settings: "
                "SECURE_SSL_REDIRECT, SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE, SECURE_HSTS_SECONDS, "
                "SECURE_HSTS_PRELOAD, SECURE_HSTS_INCLUDE_SUBDOMAINS"
                )


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Add our new application
    'cycle.apps.CycleConfig',
]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cycle_django.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'cycle_django.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


"""# Read settings file
mysqlset = Mysqlset()
mysqlset.read_settings_file(MYSQL_SETTINGS_DIR + os.sep + 'fahrrad_mysql.params')
mysqldata = mysqlset.get_settings()
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': mysqldata['database'],
        'USER': mysqldata['user'],
        'PASSWORD': mysqldata['password'],
        'HOST': mysqldata['host'],
        'PORT': '3306',
        'TEST': {
            'NAME': 'cycle_test',
        },
    }
}"""

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Europe/London'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = '/static/'

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STATIC_ROOT = os.path.join(PROJECT_ROOT, 'staticfiles')
