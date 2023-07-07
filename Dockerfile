FROM python:3.8-slim-buster

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# EXPOSE 8314

WORKDIR /cycle_logging/cycle_django
CMD ["python", "manage.py", "makemigrations"]
CMD ["python", "manage.py", "migrate"]
CMD [ "gunicorn", "cycle_django.wsgi", "-b", "0.0.0.0:8314"]
