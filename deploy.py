from datetime import datetime
import os
import subprocess

DATABASE_DUMP_FOLDERS = [
    "/home/ronny/Documents/Scripts/cycle_logging/cycle_django/backup_database",
    "/home/roghurt/Ronny_IP330S_home/Documents/Scripts/cycle_logging/cycle_django/backup_database",
]
if not os.path.exists("cycle_logging"):
    cmd = ["git", "clone", "https://github.com/ronnyerrmann/cycle_logging.git"]
    subprocess.run(cmd)

os.chdir("cycle_logging")
cmd = ["git", "pull"]
subprocess.run(cmd)

# Run everything below only there was a pull
docker_tag = f"cycle_django_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
cmd = ["docker", "build", "--tag", docker_tag, "."]
subprocess.run(cmd)

for database_dump_folder in DATABASE_DUMP_FOLDERS:
    if os.path.isfile(os.path.join(database_dump_folder, "FahrradRides_dump.json.gz")):
        break
else:
    print("No database dump found in DATABASE_DUMP_FOLDERS")
# Mount . to /cycle_django in the container
cmd = ["docker", "run", "--detach",
       "-v", ".:/cycle_logging",
       "-v", f"{database_dump_folder}:/cycle_logging/cycle_django/database_dump",
       "-p", "8314:8314",
       docker_tag]
print(" ".join(cmd))
subprocess.run(cmd)
