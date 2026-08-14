import os
import json
import shutil
import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from .utils import rand_str, log_message

def create_proxy_extension(ip, port, username, password, scheme):
    ext_dir = os.path.join(tempfile.gettempdir(), f"proxy_ext_{rand_str(8)}")
    os.makedirs(ext_dir, exist_ok=True)
    
    manifest = {
        "version": "1.0.0",
        "manifest_version": 3,
        "name": "ProxyAuth",
        "permissions": ["proxy", "webRequest", "webRequestAuthProvider", "storage"],
        "host_permissions": ["<all_urls>"],
        "background": {"service_worker": "background.js"}
    }
    with open(os.path.join(ext_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    
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
chrome.proxy.settings.set({{value: proxyConfig, scope: "regular"}}, function() {{}});
chrome.webRequest.onAuthRequired.addListener(
    function(details) {{
        return {{authCredentials: {{username: "{username}", password: "{password}"}}}};
    }},
    {{urls: ["<all_urls>"]}},
    ["blocking"]
);
"""
    with open(os.path.join(ext_dir, "background.js"), "w") as f:
        f.write(background_js)
    return ext_dir

def create_driver(proxy_str=None, scheme="http"):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-translate")
    options.add_argument("--disable-default-apps")
    options.add_argument("--mute-audio")
    options.add_argument("--no-first-run")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_setting_values.notifications": 2
    }
    options.add_experimental_option("prefs", prefs)
    
    ext_dir = None
    # FIX: only process proxy_str if it's not None and is a string
    if proxy_str and isinstance(proxy_str, str):
        parts = proxy_str.split(":")
        if len(parts) == 4:
            ip, port, user, pwd = parts
            ext_dir = create_proxy_extension(ip, port, user, pwd, scheme)
            options.add_argument(f"--load-extension={ext_dir}")
        elif len(parts) == 2:
            options.add_argument(f"--proxy-server={scheme}://{proxy_str}")
    
    # Use system Chromium and Chromedriver (no webdriver_manager)
    chromium_binary = "/usr/bin/chromium"
    chromedriver_path = "/usr/bin/chromedriver"
    
    if not os.path.exists(chromium_binary):
        # fallback to common paths
        fallbacks = [
            "/usr/bin/chromium-browser",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/google-chrome"
        ]
        for fb in fallbacks:
            if os.path.exists(fb):
                chromium_binary = fb
                break
    
    if os.path.exists(chromium_binary):
        options.binary_location = chromium_binary
    else:
        raise Exception("Chromium/Chrome binary not found!")
    
    # Use chromedriver from system
    if not os.path.exists(chromedriver_path):
        # fallback: try to find chromedriver
        possible = ["/usr/bin/chromedriver", "/usr/lib/chromium/chromedriver"]
        for p in possible:
            if os.path.exists(p):
                chromedriver_path = p
                break
        else:
            raise Exception("Chromedriver not found!")
    
    service = Service(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)
    
    # Stealth
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
    driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
    
    return driver, ext_dir

def cleanup_driver(driver=None, ext_dir=None):
    try:
        if driver:
            driver.quit()
    except:
        pass
    if ext_dir and os.path.exists(ext_dir):
        try:
            shutil.rmtree(ext_dir, ignore_errors=True)
        except:
            pass