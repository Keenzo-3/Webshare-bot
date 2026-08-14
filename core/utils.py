import os
import random
import string
from datetime import datetime
import threading

_file_lock = threading.Lock()

def rand_str(length=8):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def unique_email():
    existing = set()
    accounts_file = os.path.join("data", "accounts.txt")
    if os.path.exists(accounts_file):
        with open(accounts_file) as f:
            for line in f:
                if ':' in line:
                    existing.add(line.split(':')[0].strip())
    while True:
        email = f"{rand_str(6)}{random.randint(100,9999)}@outlook.com"
        if email not in existing:
            return email

def generate_password():
    chars = string.ascii_letters + string.digits
    p = ''.join(random.choices(chars, k=10))
    p += random.choice(string.digits) + random.choice(string.ascii_uppercase) + "x"
    return p

def save_account(email, password):
    os.makedirs("data", exist_ok=True)
    with _file_lock:
        with open(os.path.join("data", "accounts.txt"), "a") as f:
            f.write(f"{email}:{password} | {datetime.now()}\n")

def save_proxies(proxy_list):
    os.makedirs("data", exist_ok=True)
    with _file_lock:
        with open(os.path.join("data", "proxy.txt"), "a") as f:
            for proxy in proxy_list:
                f.write(f"{proxy} | {datetime.now()}\n")

def get_accounts():
    path = os.path.join("data", "accounts.txt")
    if os.path.exists(path):
        with open(path) as f:
            return f.read().strip()
    return None

def get_proxies():
    path = os.path.join("data", "proxy.txt")
    if os.path.exists(path):
        with open(path) as f:
            return f.read().strip()
    return None

def count_accounts():
    try:
        with open(os.path.join("data", "accounts.txt")) as f:
            return sum(1 for _ in f)
    except FileNotFoundError:
        return 0

def count_proxies():
    try:
        with open(os.path.join("data", "proxy.txt")) as f:
            return sum(1 for _ in f)
    except FileNotFoundError:
        return 0

def format_large_number(num):
    return f"{num:,}"

def log_message(message, level="INFO"):
    print(f"[{datetime.now()}] [{level}] {message}")