import time
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from .browser import create_driver, cleanup_driver
from .utils import save_account, save_proxies, log_message

MAX_RETRIES = 3
RETRY_DELAY = 5

def fetch_proxies(token, max_pages=3):
    """Fetch proxy list using API token with retries."""
    proxies = []
    headers = {
        "Authorization": f"Token {token}",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    session = requests.Session()
    session.headers.update(headers)
    
    for page in range(1, max_pages + 1):
        for attempt in range(MAX_RETRIES):
            try:
                params = {"mode": "direct", "page": str(page), "page_size": "100"}
                resp = session.get(
                    "https://proxy.webshare.io/api/v2/proxy/list/",
                    params=params,
                    timeout=30
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])
                    if not results:
                        break
                    for proxy in results:
                        auth = f"{proxy['username']}:{proxy['password']}"
                        proxies.append(f"{proxy['proxy_address']}:{proxy['port']}:{auth}")
                    if not data.get("next"):
                        return proxies
                    break  # success
                elif resp.status_code == 403:
                    log_message("No proxy plan available", "WARNING")
                    return proxies
                else:
                    log_message(f"Proxy fetch error {resp.status_code}, retry {attempt+1}", "WARNING")
                    time.sleep(RETRY_DELAY)
            except Exception as e:
                log_message(f"Proxy fetch attempt {attempt+1} failed: {e}", "WARNING")
                time.sleep(RETRY_DELAY)
        else:
            break
    if proxies:
        save_proxies(proxies)
        log_message(f"Saved {len(proxies)} proxies")
    return proxies

def extract_token(driver):
    """Extract token from localStorage, cookies, or sessionStorage."""
    token = driver.execute_script("return localStorage.getItem('token') || '';")
    if token:
        return token
    for cookie in driver.get_cookies():
        if cookie.get('name') == 'token':
            return cookie.get('value', '')
    token = driver.execute_script("return sessionStorage.getItem('token') || '';")
    return token

def register_via_browser(driver, email, password):
    """Register using browser – with robust selectors and retries."""
    wait = WebDriverWait(driver, 20)
    driver.get("https://dashboard.webshare.io/register?source=login_signup_link")
    time.sleep(2)  # initial load
    
    try:
        # Use more reliable selectors
        email_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='email']"))
        )
        email_input.clear()
        email_input.send_keys(email)
        time.sleep(0.5)
        
        pwd_input = driver.find_element(By.CSS_SELECTOR, "input[name='password']")
        pwd_input.clear()
        pwd_input.send_keys(password)
        time.sleep(0.5)
        
        # Accept TOS – try multiple possible selectors
        try:
            tos_check = driver.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
            if not tos_check.is_selected():
                tos_check.click()
        except:
            # try label click
            try:
                driver.find_element(By.XPATH, "//label[contains(text(), 'Terms')]").click()
            except:
                pass
        
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_btn.click()
        
        # Wait for redirect or token
        time.sleep(5)
        
        # Check success by URL or token presence
        if "register" not in driver.current_url and "login" not in driver.current_url:
            token = extract_token(driver)
            if token:
                return {"success": True, "token": token}
        
        # If still on register page, check for errors
        try:
            error = driver.find_element(By.CSS_SELECTOR, ".error, .alert-danger").text
            if "already exists" in error.lower():
                return {"success": False, "error": "Account exists", "code": "EXISTS"}
            return {"success": False, "error": error[:100]}
        except:
            return {"success": False, "error": "Registration failed – unknown error"}
    
    except TimeoutException:
        return {"success": False, "error": "Timeout waiting for form"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def register_via_api(driver, email, password):
    """API registration with proper CSRF handling."""
    cookies = {c['name']: c['value'] for c in driver.get_cookies()}
    csrf = cookies.get('csrftoken') or cookies.get('csrf_token') or ''
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://dashboard.webshare.io",
        "Referer": "https://dashboard.webshare.io/register",
    }
    if csrf:
        headers["X-CSRFToken"] = csrf
    
    session = requests.Session()
    session.headers.update(headers)
    session.cookies.update(cookies)
    
    data = {"email": email, "password": password, "tos_accepted": True}
    
    resp = session.post("https://proxy.webshare.io/api/v2/register/", json=data, timeout=30)
    if resp.status_code in (200, 201):
        token = resp.json().get("token")
        if token:
            return {"success": True, "token": token}
        return {"success": False, "error": "No token in response"}
    
    if "already exists" in resp.text.lower():
        log_message(f"Account exists, attempting login for {email}")
        login_resp = session.post(
            "https://proxy.webshare.io/api/v2/auth/login/",
            json={"email": email, "password": password},
            timeout=30
        )
        if login_resp.status_code == 200:
            token = login_resp.json().get("token")
            if token:
                return {"success": True, "token": token}
        return {"success": False, "error": "Login failed"}
    
    return {"success": False, "error": f"API error {resp.status_code}"}

def create_webshare_account(email, password, proxy_str=None, scheme="http"):
    """Main function – tries browser then API, with retries."""
    result = {"success": False, "proxies": 0, "error": None}
    driver = None
    ext_dir = None
    
    try:
        log_message(f"Creating account: {email}")
        driver, ext_dir = create_driver(proxy_str, scheme)
        
        # Try browser registration with retries
        browser_result = None
        for attempt in range(MAX_RETRIES):
            browser_result = register_via_browser(driver, email, password)
            if browser_result["success"]:
                break
            if browser_result.get("code") == "EXISTS":
                # Account exists – we can try login via API later
                break
            log_message(f"Browser attempt {attempt+1} failed: {browser_result.get('error')}", "WARNING")
            driver.refresh()
            time.sleep(RETRY_DELAY)
        
        if browser_result and browser_result["success"]:
            token = browser_result["token"]
            save_account(email, password)
            proxies = fetch_proxies(token)
            result["success"] = True
            result["proxies"] = len(proxies)
            log_message(f"Browser success: {email}")
            return result
        
        # Fallback: API
        log_message("Trying API registration...")
        api_result = register_via_api(driver, email, password)
        if api_result["success"]:
            token = api_result["token"]
            save_account(email, password)
            proxies = fetch_proxies(token)
            result["success"] = True
            result["proxies"] = len(proxies)
            log_message(f"API success: {email}")
            return result
        
        result["error"] = api_result.get("error", "All methods failed")
        log_message(f"All methods failed for {email}: {result['error']}", "ERROR")
    
    except Exception as e:
        result["error"] = str(e)
        log_message(f"Account creation error: {e}", "ERROR")
    
    finally:
        cleanup_driver(driver, ext_dir)
    
    return result