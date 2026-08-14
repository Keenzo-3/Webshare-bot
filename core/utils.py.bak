import os
import random
import string
from datetime import datetime

def rand_str(length=8):
    """Generate random lowercase string"""
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def unique_email():
    """Generate unique fake Outlook email"""
    existing = set()
    try:
        accounts_file = os.path.join("data", "accounts.txt")
        if os.path.exists(accounts_file):
            with open(accounts_file) as f:
                for line in f:
                    if ':' in line:
                        existing.add(line.split(':')[0].strip())
    except Exception:
        pass
    
    while True:
        email = f"{rand_str(6)}{random.randint(100,9999)}@outlook.com"
        if email not in existing:
            return email

def generate_password():
    """Generate random strong password"""
    chars = string.ascii_letters + string.digits
    password = ''.join(random.choices(chars, k=10))
    password += random.choice(string.digits)
    password += random.choice(string.ascii_uppercase)
    password += "x"
    return password

def save_account(email, password):
    """Save account credentials to file"""
    os.makedirs("data", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join("data", "accounts.txt"), "a") as f:
        f.write(f"{email}:{password} | {timestamp}\n")

def save_proxies(proxy_list):
    """Save proxies to file"""
    os.makedirs("data", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join("data", "proxy.txt"), "a") as f:
        for proxy in proxy_list:
            f.write(f"{proxy} | {timestamp}\n")

def get_accounts():
    """Read all accounts from file"""
    accounts_file = os.path.join("data", "accounts.txt")
    if os.path.exists(accounts_file):
        with open(accounts_file) as f:
            return f.read().strip()
    return None

def get_proxies():
    """Read all proxies from file"""
    proxy_file = os.path.join("data", "proxy.txt")
    if os.path.exists(proxy_file):
        with open(proxy_file) as f:
            return f.read().strip()
    return None

def count_accounts():
    """Count total accounts"""
    try:
        with open(os.path.join("data", "accounts.txt")) as f:
            return sum(1 for _ in f)
    except FileNotFoundError:
        return 0

def count_proxies():
    """Count total proxies"""
    try:
        with open(os.path.join("data", "proxy.txt")) as f:
            return sum(1 for _ in f)
    except FileNotFoundError:
        return 0

def format_large_number(num):
    """Format large numbers with commas"""
    return f"{num:,}"

def log_message(message, level="INFO"):
    """Simple logging function"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")
