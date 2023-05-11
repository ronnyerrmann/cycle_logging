. ~/.virtualenvs/my_django_environment/bin/activate
sleep 2
cd ~/Documents/Scripts/cycle_logging/cycle_django
# Start with 0.0.0.0:8000 to listens on the network interface
# Start with --insecure to lazily not host static files in a webserver
python3 manage.py runserver 0.0.0.0:8000 --insecure
