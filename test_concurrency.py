import threading
import requests

BASE_URL = "http://127.0.0.1:8000/api"


def login(user_id):
    response = requests.post(
        f"{BASE_URL}/user/login",
        json={
            "username": f"user{user_id - 1}",
            "password": "password123"
        }
    )
    if response.status_code != 200:
        return None
    return response.json().get("access")


def buy(user_id, user_name):
    token = login(user_id)
    if not token:
        print(f"\n{user_name} - login failed")
        return

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{BASE_URL}/cart/confirm/{user_id}",
        headers=headers
    )

    print(f"\n{user_name}")
    print("Status:", response.status_code)
    print("Response:", response.text)


thread1 = threading.Thread(target=buy, args=(1, "marwa"))
thread2 = threading.Thread(target=buy, args=(2, "Aya"))

thread1.start()
thread2.start()

thread1.join()
thread2.join()
