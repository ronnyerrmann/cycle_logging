cd ~/Documents/Scripts/cycle_logging/cycle_django
. ../cycle_django_env/bin/activate
export SRTM1_DIR=/media/ronny/Backup500GB/srtm/1/   # to load srtm data. If not set the gpx files won't be stored with srtm elevation
export SRTM3_DIR=/media/ronny/Backup500GB/srtm/3/
sleep 2
# Start with 0.0.0.0:8000 to listens on the network interface
# Start with --insecure to lazily not host static files in a webserver
python3 manage.py runserver 0.0.0.0:8000
