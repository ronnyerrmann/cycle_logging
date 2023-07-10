FROM python:3.8-slim-buster

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# EXPOSE 8314

WORKDIR /cycle_logging/cycle_django
# Only last CMD will be executed
#CMD ["python", "manage.py", "makemigrations"]
#CMD ["python", "manage.py", "migrate"]
#CMD [ "gunicorn", "cycle_django.wsgi", "-b", "0.0.0.0:8314"]

# Without /bin/bash the script wouldn't be executed locally;
CMD /bin/sh -c "sh docker_startup.sh >> docker_run.log 2>&1"
