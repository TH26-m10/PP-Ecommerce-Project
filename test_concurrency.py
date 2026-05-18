import threading
import requests

URL_A = "http://127.0.0.1:8000/api/cart/confirm/1"
URL_B = "http://127.0.0.1:8000/api/cart/confirm/2"

def buy(url, user_name):
    response = requests.post(url)

    print(f"\n{user_name}")
    print("Status:", response.status_code)
    print("Response:", response.text)

thread1 = threading.Thread(target=buy, args=(URL_A, "marwa"))
thread2 = threading.Thread(target=buy, args=(URL_B, "Aya"))

thread1.start()
thread2.start()

thread1.join()
thread2.join()