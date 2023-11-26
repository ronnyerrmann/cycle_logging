FROM python:3.8-slim-buster

# Install nginx - update and install in same line, as otherwise different caches
# Don't install vim as a standard, way too many dep
RUN apt-get update -y && apt-get install -y nginx libgdal-dev # vim
COPY nginx_server.conf /etc/nginx/sites-enabled

# Install Django
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# EXPOSE 8314

#WORKDIR /cycle_logging/cycle_django
WORKDIR /cycle_django_int

# Only last CMD will be executed

# Without /bin/bash the script wouldn't be executed locally;
CMD service nginx restart & /bin/sh -c "sh /cycle_logging/cycle_django/docker_startup.sh >> docker_run.log 2>&1"
