import argparse
from datetime import datetime
import os
import subprocess


SETTINGS_FOLDERS = [
    "/home/ronny/Documents/Scripts/cycle_logging",                      # Test Production locally
    "/home/roghurt/Ronny_IP330S_home/Documents/Scripts/cycle_logging",  # Production
]

for SETTINGS_FOLDERS in SETTINGS_FOLDERS:
    DATABASE_BACKUP_FOLDER = os.path.join(SETTINGS_FOLDERS, "cycle_django", "backup_database")
    if os.path.isfile(os.path.join(DATABASE_BACKUP_FOLDER, "CycleRides_dump.json.gz")):
        break
else:
    print("No database dump found in SETTINGS_FOLDERS")

parser = argparse.ArgumentParser(description="Deploy to Production")
parser.add_argument("-b", "--branch", help="Optional branch", default="main")
args = parser.parse_args()
cmd_branch = ["git", "checkout", args.branch]

new = not os.path.exists("cycle_logging")
if new:
    cmd = ["git", "clone", "https://github.com/ronnyerrmann/cycle_logging.git"]
    print(" ".join(cmd))
    subprocess.run(cmd)
os.chdir("cycle_logging")
if not new:
    cmd = ["git", "pull"]
    print(" ".join(cmd))
    subprocess.run(cmd)
print(" ".join(cmd_branch))
subprocess.run(cmd_branch)

# Run everything below only there was a pull
docker_tag = f"cycle_django_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
cmd = ["docker", "build", "--tag", docker_tag, "."]
print(" ".join(cmd))
subprocess.run(cmd)

cmds = ["python manage.py makemigrations", "python manage.py migrate", "python manage.py collectstatic --noinput",
        "gunicorn cycle_django.wsgi -b 0.0.0.0:8314"]
with open(os.path.join("cycle_django", "docker_startup.sh"), "w") as f:
    f.write("#!/bin/bash\n")
    for cmd in cmds:
        f.write(f"echo '{cmd}'\n{cmd}\n")

cmd = ["docker", "kill", "cycle_log"]
print(" ".join(cmd))
subprocess.run(cmd)

cmd = ["docker", "rm", "cycle_log"]
print(" ".join(cmd))
subprocess.run(cmd)

# Mount . to /cycle_django in the container
cmd = ["docker", "run", "--detach",
       "-e", "IS_PRODUCTION=True",
       "-v", f"{os.path.abspath('.')}:/cycle_logging",
       "-v", f"{os.path.abspath(SETTINGS_FOLDERS)}:/cycle_setup",
       "-v", f"{os.path.abspath(DATABASE_BACKUP_FOLDER)}:/cycle_logging/cycle_django/load_db_dump_at_startup",
       "-p", "8314:8314", "-p", "8315:8315",
       "--name", "cycle_log",
       docker_tag]
print(" ".join(cmd))
subprocess.run(cmd)
