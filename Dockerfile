FROM python:3.12-slim-bullseye

# Install nginx - update and install in same line, as otherwise different caches
# Don't install vim as a standard, way too many dep
RUN apt-get update -y && apt-get install -y nginx gdal-bin=3.4.1 libgdal-dev python3-gdal # vim
COPY nginx_server.conf /etc/nginx/sites-enabled

# Install Django
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# EXPOSE 8314

#WORKDIR /cycle_logging/cycle_django
WORKDIR /cycle_django_int

# Only last CMD will be executed

# Without /bin/bash the script wouldn't be executed locally;
CMD service nginx restart & /bin/sh -c "sh /cycle_logging/cycle_django/docker_startup.sh >> /cycle_logging/docker_run.log 2>&1"
