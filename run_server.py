import multiprocessing
import os

cpu_cores = multiprocessing.cpu_count()

threads = cpu_cores * 2

connection_limit = threads * 50

command = (
    f"waitress-serve "
    f"--threads={threads} "
    f"--connection-limit={connection_limit} "
    f"--host=127.0.0.1 "
    f"--port=8000 "
    f"project.wsgi:application"
)

print("=" * 50)
print(f"CPU cores: {cpu_cores}")
print(f"Threads: {threads}")
print(f"Connection limit: {connection_limit}")
print("=" * 50)

os.system(command)
