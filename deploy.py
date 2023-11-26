import argparse
from datetime import datetime
import os
import subprocess

DOCKER_BINS = ["/usr/bin/docker", "/snap/bin/docker"]
SETTINGS_FOLDERS = [
    "/home/ronny/Documents/Scripts/cycle_logging",                      # Test Production locally
    "/home/roghurt/Ronny_IP330S_home/Documents/Scripts/cycle_logging",  # Production
]
CYCLE_BASE_PATH = "cycle_logging"

BASE_PATH = os.getcwd()

for SETTINGS_FOLDER in SETTINGS_FOLDERS:
    DATABASE_BACKUP_FOLDER = os.path.join(SETTINGS_FOLDER, "cycle_django", "backup_database")
    if os.path.isfile(os.path.join(DATABASE_BACKUP_FOLDER, "CycleRides_dump.json.gz")):
        break
else:
    print(f"No database dump found in SETTINGS_FOLDERS, will use {SETTINGS_FOLDER} for settings")

for docker_bin in DOCKER_BINS:
    if os.path.isfile(docker_bin):
        break
else:
    print(f"No docker found in DOCKER_BINS: {DOCKER_BINS}, will use just 'docker'")
    docker_bin = "docker"

# Using a new path for each deployment means that old data is removed from db file each time
cycle_path = CYCLE_BASE_PATH + "_" + datetime.today().strftime("%Y_%m_%d")


def run_with_print(cmd):
    print(" ".join(cmd))
    return subprocess.run(cmd)


parser = argparse.ArgumentParser(description="Deploy to Production")
parser.add_argument("-b", "--branch", help="Optional branch", default="main")
args = parser.parse_args()

new = not os.path.exists(cycle_path)
if new:
    cmd = ["git", "clone", f"https://github.com/ronnyerrmann/{CYCLE_BASE_PATH}.git"]
    run_with_print(cmd)
    cmd = ["mv", CYCLE_BASE_PATH, cycle_path]
    run_with_print(cmd)
os.chdir(cycle_path)
if not new:
    cmd = ["git", "fetch", "origin"]
    run_with_print(cmd)
cmd = ["git", "checkout", args.branch]
run_with_print(cmd)
if not new:
    cmd = ["git", "reset", "--hard", f"origin/{args.branch}"]
    run_with_print(cmd)

# Run everything below only if there was a new commit
docker_tag = f"cycle_django_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
cmd = [docker_bin, "build", "--tag", docker_tag, "."]
run_with_print(cmd)

cmds = ["cp -rp /cycle_logging/* .",    # work in /cycle_django_int
        #"cd cycle_django/",
        "python manage.py makemigrations",
        "python manage.py migrate",
        "python manage.py collectstatic --noinput",
        "gunicorn cycle_django.wsgi -b 0.0.0.0:8315 --timeout 120"
        ]
with open(os.path.join("cycle_django", "docker_startup.sh"), "w") as f:
    f.write("#!/bin/bash\n")
    for cmd in cmds:
        f.write(f"echo '{cmd}'\n{cmd}\n")

cmd = [docker_bin, "kill", "cycle_log"]
run_with_print(cmd)

cmd = [docker_bin, "rm", "cycle_log"]
run_with_print(cmd)

# Mount . to /cycle_django in the container
cmd = [docker_bin, "run", "--detach",
       "-e", "IS_PRODUCTION=True",
       "-v", f"{os.path.abspath('.')}:/{CYCLE_BASE_PATH}",
       "-v", f"{os.path.abspath(SETTINGS_FOLDER)}:/cycle_setup",        # listen to changes in this folder
       "-v", f"{os.path.abspath(DATABASE_BACKUP_FOLDER)}:/{CYCLE_BASE_PATH}/cycle_django/load_db_dump_at_startup",
       "-p", "8314:8314",
       "--name", "cycle_log",
       docker_tag]
run_with_print(cmd)

# Clean old install folders
os.chdir(BASE_PATH)
install_folders = [folder for folder in os.listdir(".") if folder.startswith(CYCLE_BASE_PATH)]
# Delete all but the last two folders
if len(install_folders) > 2:
    install_folders.sort()
    folders_to_delete = install_folders[:-2]
    cmd = ["rm", "-rf"]
    for folder in folders_to_delete:
        cmd += [folder]
    run_with_print(cmd)

# Further improvement: Only kill the old container after the new has started up (and a wget was successful)
# Start with different port and then forward port internally
