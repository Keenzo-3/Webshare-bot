import os
import json
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from .utils import rand_str, log_message

def create_proxy_extension(ip, port, username, password, scheme):
    """Create Chrome extension for proxy authentication"""
    ext_dir = os.path.join("/tmp", f"proxy_ext_{rand_str(8)}")
    os.makedirs(ext_dir, exist_ok=True)
    
    # Manifest V3
    manifest = {
        "version": "1.0.0",
        "manifest_version": 3,
        "name": "ProxyAuth",
        "permissions": [
            "proxy",
            "webRequest",
            "webRequestAuthProvider",
            "storage"
        ],
        "host_permissions": ["<all_urls>"],
        "background": {
            "service_worker": "background.js"
        }
    }
    
    with open(os.path.join(ext_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    
    # Background script
    background_js = f"""
const proxyConfig = {{
    mode: "fixed_servers",
    rules: {{
        singleProxy: {{
            scheme: "{scheme}",
            host: "{ip}",
            port: {port}
        }}
    }}
}};

chrome.proxy.settings.set(
    {{value: proxyConfig, scope: "regular"}},
    function() {{}}
);

chrome.webRequest.onAuthRequired.addListener(
    function(details) {{
        return {{
            authCredentials: {{
                username: "{username}",
                password: "{password}"
            }}
        }};
    }},
    {{urls: ["<all_urls>"]}},
    ["blocking"]
);
"""
    
    with open(os.path.join(ext_dir, "background.js"), "w") as f:
        f.write(background_js)
    
    return ext_dir

def create_driver(proxy_str=None, scheme="http"):
    """Create and configure undetected Chrome driver"""
    
    chrome_options = Options()
    
    # Headless mode for server
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    
    # Memory optimization
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-sync")
    chrome_options.add_argument("--disable-translate")
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--single-process")
    
    # Anti-detection
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # Window size
    chrome_options.add_argument("--window-size=1920,1080")
    
    # User agent
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    
    # Additional preferences
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_setting_values.notifications": 2
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Proxy setup
    ext_dir = None
    if proxy_str and scheme != "none":
        parts = proxy_str.split(":")
        if len(parts) == 4:  # ip:port:username:password
            ip, port, user, pwd = parts
            ext_dir = create_proxy_extension(ip, port, user, pwd, scheme)
            chrome_options.add_argument(f"--load-extension={ext_dir}")
        elif len(parts) == 2:  # ip:port
            chrome_options.add_argument(f"--proxy-server={scheme}://{proxy_str}")
    
    # Create driver
    try:
        # For Render/cloud environment
        chrome_path = None
        if os.path.exists("/opt/render/project/.render/chrome/opt/google/chrome"):
            chrome_path = "/opt/render/project/.render/chrome/opt/google/chrome"
            chrome_options.binary_location = chrome_path
        
        service = Service(ChromeDriverManager(chrome_type=ChromeType.GOOGLE).install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Execute anti-detection scripts
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        driver.execute_script(
            "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})"
        )
        driver.execute_script(
            "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})"
        )
        
        return driver, ext_dir
    
    except Exception as e:
        log_message(f"Driver creation failed: {e}", "ERROR")
        raise

def cleanup_driver(driver=None, ext_dir=None):
    """Safely close driver and clean up files"""
    try:
        if driver:
            driver.quit()
    except Exception as e:
        log_message(f"Driver cleanup error: {e}", "WARNING")
    
    if ext_dir and os.path.exists(ext_dir):
        try:
            shutil.rmtree(ext_dir, ignore_errors=True)
        except Exception as e:
            log_message(f"Extension cleanup error: {e}", "WARNING")
