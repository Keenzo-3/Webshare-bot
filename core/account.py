import time
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from .browser import create_driver, cleanup_driver
from .utils import save_account, save_proxies, log_message

def fetch_proxies(token, max_pages=3):
    """Fetch proxy list using API token"""
    proxies = []
    
    try:
        headers = {
            "Authorization": f"Token {token}",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        session = requests.Session()
        session.headers.update(headers)
        
        for page in range(1, max_pages + 1):
            params = {
                "mode": "direct",
                "page": str(page),
                "page_size": "100"
            }
            
            response = session.get(
                "https://proxy.webshare.io/api/v2/proxy/list/",
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                
                if not results:
                    break
                
                for proxy in results:
                    auth = f"{proxy['username']}:{proxy['password']}"
                    proxy_line = f"{proxy['proxy_address']}:{proxy['port']}:{auth}"
                    proxies.append(proxy_line)
                
                # Check if there are more pages
                if not data.get("next"):
                    break
            
            elif response.status_code == 403:
                log_message("No proxy plan available", "WARNING")
                break
            else:
                log_message(f"Proxy fetch failed: {response.status_code}", "ERROR")
                break
            
            time.sleep(0.5)  # Rate limiting
        
        if proxies:
            save_proxies(proxies)
            log_message(f"Saved {len(proxies)} proxies")
    
    except Exception as e:
        log_message(f"Proxy fetch error: {e}", "ERROR")
    
    return proxies

def extract_token(driver):
    """Extract authentication token from browser storage"""
    token = None
    
    # Method 1: localStorage
    try:
        token = driver.execute_script("return localStorage.getItem('token') || '';")
        if token:
            return token
    except:
        pass
    
    # Method 2: Cookies
    try:
        cookies = driver.get_cookies()
        for cookie in cookies:
            if cookie.get('name') == 'token':
                token = cookie.get('value', '')
                if token:
                    return token
    except:
        pass
    
    # Method 3: sessionStorage
    try:
        token = driver.execute_script("return sessionStorage.getItem('token') || '';")
        if token:
            return token
    except:
        pass
    
    return token

def register_via_browser(driver, email, password):
    """Register account using browser automation"""
    wait = WebDriverWait(driver, 20)
    
    try:
        # Navigate to registration page
        driver.get("https://dashboard.webshare.io/register?source=login_signup_link")
        time.sleep(3)
        
        # Fill email field
        email_field = wait.until(
            EC.presence_of_element_located((By.ID, "email-input"))
        )
        email_field.clear()
        email_field.send_keys(email)
        time.sleep(0.5)
        
        # Verify email was entered
        entered = driver.execute_script("return arguments[0].value;", email_field)
        if not entered:
            driver.execute_script("arguments[0].value = arguments[1];", email_field, email)
        time.sleep(0.3)
        
        # Fill password field
        password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        password_field.clear()
        password_field.send_keys(password)
        time.sleep(0.3)
        
        # Verify password
        entered = driver.execute_script("return arguments[0].value;", password_field)
        if not entered:
            driver.execute_script("arguments[0].value = arguments[1];", password_field, password)
        time.sleep(0.3)
        
        # Accept TOS
        try:
            checkbox = driver.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
            if not checkbox.is_selected():
                driver.execute_script("arguments[0].click();", checkbox)
            time.sleep(0.3)
        except NoSuchElementException:
            log_message("TOS checkbox not found", "WARNING")
        
        # Submit form
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        driver.execute_script("arguments[0].click();", submit_btn)
        
        log_message(f"Form submitted for {email}")
        
        # Wait for processing
        time.sleep(5)
        
        # Check if successful
        current_url = driver.current_url
        if "register" not in current_url and "login" not in current_url:
            token = extract_token(driver)
            if token:
                return {"success": True, "token": token}
        
        return {"success": False, "error": "Browser registration failed"}
    
    except TimeoutException:
        return {"success": False, "error": "Timeout waiting for element"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def register_via_api(driver, email, password):
    """Register account using API (fallback method)"""
    
    try:
        # Get cookies from browser
        cookies = {c['name']: c['value'] for c in driver.get_cookies()}
        cookie_string = "; ".join(f"{k}={v}" for k, v in cookies.items())
        
        # Get CSRF token if exists
        csrf_token = ""
        for cookie in driver.get_cookies():
            if 'csrf' in cookie.get('name', '').lower():
                csrf_token = cookie.get('value', '')
                break
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://dashboard.webshare.io",
            "Referer": "https://dashboard.webshare.io/register",
            "Cookie": cookie_string
        }
        
        if csrf_token:
            headers["X-CSRFToken"] = csrf_token
        
        data = {
            "email": email,
            "password": password,
            "tos_accepted": True
        }
        
        session = requests.Session()
        session.headers.update(headers)
        
        # Try registration
        response = session.post(
            "https://proxy.webshare.io/api/v2/register/",
            json=data,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            token = response.json().get("token", "")
            if token:
                return {"success": True, "token": token}
            return {"success": False, "error": "No token in response"}
        
        # If account exists, try login
        if "already exists" in response.text.lower() or response.status_code == 400:
            log_message(f"Account exists, attempting login for {email}")
            
            login_data = {"email": email, "password": password}
            login_response = session.post(
                "https://proxy.webshare.io/api/v2/auth/login/",
                json=login_data,
                timeout=30
            )
            
            if login_response.status_code == 200:
                token = login_response.json().get("token", "")
                if token:
                    return {"success": True, "token": token}
            
            return {"success": False, "error": "Login failed"}
        
        return {"success": False, "error": f"API Error: {response.status_code}"}
    
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Request failed: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def create_webshare_account(email, password, proxy_str=None, scheme="http"):
    """Main function to create a Webshare.io account"""
    
    driver = None
    ext_dir = None
    result = {
        "success": False,
        "proxies": 0,
        "error": None
    }
    
    try:
        log_message(f"Creating account: {email}")
        
        # Create browser driver
        driver, ext_dir = create_driver(proxy_str, scheme)
        
        # Try browser registration first
        browser_result = register_via_browser(driver, email, password)
        
        if browser_result["success"]:
            token = browser_result["token"]
            save_account(email, password)
            proxies = fetch_proxies(token)
            result["success"] = True
            result["proxies"] = len(proxies)
            log_message(f"Browser registration success: {email}")
        else:
            # Fallback to API
            log_message(f"Browser failed: {browser_result.get('error')}, trying API")
            api_result = register_via_api(driver, email, password)
            
            if api_result["success"]:
                token = api_result["token"]
                save_account(email, password)
                proxies = fetch_proxies(token)
                result["success"] = True
                result["proxies"] = len(proxies)
                log_message(f"API registration success: {email}")
            else:
                result["error"] = api_result.get("error", "All methods failed")
                log_message(f"All methods failed for {email}", "ERROR")
    
    except Exception as e:
        result["error"] = str(e)
        log_message(f"Account creation error: {e}", "ERROR")
    
    finally:
        cleanup_driver(driver, ext_dir)
    
    return result
