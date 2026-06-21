import threading
import random
import time

servers = {
    "Server-1": {"requests": 0, "load": 0},
    "Server-2": {"requests": 0, "load": 0},
    "Server-3": {"requests": 0, "load": 0},
}

current_index = 0
lock = threading.Lock()


def simulate_load():
    for s in servers:
        servers[s]["load"] = random.randint(1, 100)


def get_next_server():

    global current_index

    with lock:

        simulate_load()

        server_names = list(servers.keys())

        rr_server = server_names[current_index]

        best_server = min(servers.items(), key=lambda x: x[1]["load"])[0]

        current_index = (current_index + 1) % len(server_names)

        servers[rr_server]["requests"] += 1

        return {
            "round_robin_server": rr_server,
            "smart_server": best_server,
            "status": servers
        }