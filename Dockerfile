FROM python:3.8-slim-buster

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Can't clone a private repository
# RUN git clone https://github.com/ronnyerrmann/webjourney.git
WORKDIR /cycle_logging/cycle_django
CMD [ "gunicorn", "cycle_django.wsgi", "-b", "0.0.0.0:8314" ]
