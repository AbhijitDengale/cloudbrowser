import os
import time
import base64
import json
import threading
import urllib.parse
import subprocess
import shutil
from io import BytesIO
from flask import Flask, render_template, request, jsonify, Response, session
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)

# Session timeout in seconds (30 minutes)
SESSION_TIMEOUT = 1800

# Store browser sessions
browser_sessions = {}
session_last_used = {}

# Install chromedriver if running on Render
if os.environ.get('RENDER'):
    try:
        print("Setting up ChromeDriver for Render environment...")
        # Download ChromeDriver
        subprocess.run([
            "wget", "-q", "https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip"
        ], check=True)
        
        # Unzip ChromeDriver
        subprocess.run(["unzip", "-q", "chromedriver_linux64.zip"], check=True)
        
        # Make it executable
        subprocess.run(["chmod", "+x", "chromedriver"], check=True)
        
        # Move to a directory in PATH
        os.environ["CHROMEDRIVER_PATH"] = os.path.join(os.getcwd(), "chromedriver")
        
        print(f"ChromeDriver set up at: {os.environ['CHROMEDRIVER_PATH']}")
    except Exception as e:
        print(f"Error setting up ChromeDriver: {str(e)}")

def cleanup_old_sessions():
    """Periodically clean up old browser sessions to free resources"""
    while True:
        current_time = time.time()
        sessions_to_remove = []
        
        for session_id, last_used in list(session_last_used.items()):
            if current_time - last_used > SESSION_TIMEOUT:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            if session_id in browser_sessions:
                try:
                    browser_sessions[session_id].quit()
                except:
                    pass
                del browser_sessions[session_id]
            if session_id in session_last_used:
                del session_last_used[session_id]
                
        time.sleep(60)  # Check every minute

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_sessions, daemon=True)
cleanup_thread.start()

def get_browser_for_session():
    """Get or create a browser instance for the current session"""
    session_id = session.get('id')
    
    if not session_id or session_id not in browser_sessions:
        # Create new session ID if needed
        if not session_id:
            session_id = os.urandom(16).hex()
            session['id'] = session_id
        
        # Setup Chrome options for headless browsing
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--single-process")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("--disable-software-rasterizer")
        
        try:
            # Check if we're running on Render
            if os.environ.get('RENDER'):
                # Use our downloaded ChromeDriver
                chrome_driver_path = os.environ.get('CHROMEDRIVER_PATH', os.path.join(os.getcwd(), "chromedriver"))
                print(f"Using ChromeDriver at: {chrome_driver_path}")
                
                if not os.path.exists(chrome_driver_path):
                    raise Exception(f"ChromeDriver not found at {chrome_driver_path}")
                
                service = Service(executable_path=chrome_driver_path)
                browser = webdriver.Chrome(service=service, options=chrome_options)
            else:
                # For local development, use webdriver_manager
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                browser = webdriver.Chrome(service=service, options=chrome_options)
            
            browser_sessions[session_id] = browser
            print("Chrome browser instance created successfully")
        except Exception as e:
            print(f"Error initializing Chrome: {str(e)}")
            # Try method without service object
            try:
                print("Trying alternative Chrome initialization...")
                browser = webdriver.Chrome(options=chrome_options)
                browser_sessions[session_id] = browser
                print("Alternative initialization succeeded")
            except Exception as e2:
                print(f"All initialization methods failed: {str(e2)}")
                raise
    
    # Update last used time
    session_last_used[session_id] = time.time()
    return browser_sessions[session_id]

@app.route('/')
def index():
    return render_template('selenium_index.html')

@app.route('/browse')
def browse():
    url = request.args.get('url', 'https://www.google.com')
    
    # Validate URL
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    try:
        browser = get_browser_for_session()
        browser.get(url)
        
        # Wait for page to load
        time.sleep(2)
        
        # Capture screenshot
        screenshot = browser.get_screenshot_as_png()
        screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
        
        # Get current URL (might have redirected)
        current_url = browser.current_url
        
        # Get page title
        title = browser.title
        
        return render_template('selenium_view.html', 
                              screenshot=screenshot_b64, 
                              current_url=current_url,
                              title=title)
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/action', methods=['POST'])
def perform_action():
    action_type = request.form.get('type')
    
    try:
        browser = get_browser_for_session()
        
        if action_type == 'click':
            x = int(request.form.get('x'))
            y = int(request.form.get('y'))
            
            # Execute JavaScript to click at coordinates
            browser.execute_script(f"document.elementFromPoint({x}, {y}).click();")
            time.sleep(1)  # Wait for page to update
            
        elif action_type == 'type':
            text = request.form.get('text', '')
            selector = request.form.get('selector', 'body')
            
            # Find element and type text
            element = browser.find_element(By.CSS_SELECTOR, selector)
            element.send_keys(text)
            
        elif action_type == 'enter':
            selector = request.form.get('selector', 'body')
            
            # Find element and press Enter
            element = browser.find_element(By.CSS_SELECTOR, selector)
            element.send_keys(Keys.RETURN)
            time.sleep(1)  # Wait for page to update
            
        elif action_type == 'navigate':
            url = request.form.get('url')
            if url:
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                browser.get(url)
                time.sleep(2)  # Wait for page to load
        
        # Capture new screenshot
        screenshot = browser.get_screenshot_as_png()
        screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
        
        # Get current URL and title
        current_url = browser.current_url
        title = browser.title
        
        return jsonify({
            'screenshot': screenshot_b64,
            'current_url': current_url,
            'title': title
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/keyboard', methods=['POST'])
def keyboard_input():
    key = request.form.get('key')
    
    try:
        browser = get_browser_for_session()
        active_element = browser.switch_to.active_element
        
        # Map special keys
        if key == 'Enter':
            active_element.send_keys(Keys.RETURN)
        elif key == 'Backspace':
            active_element.send_keys(Keys.BACKSPACE)
        elif key == 'Tab':
            active_element.send_keys(Keys.TAB)
        elif key == 'Escape':
            active_element.send_keys(Keys.ESCAPE)
        else:
            active_element.send_keys(key)
        
        time.sleep(0.5)  # Short wait for page update
        
        # Capture new screenshot
        screenshot = browser.get_screenshot_as_png()
        screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
        
        return jsonify({
            'screenshot': screenshot_b64,
            'current_url': browser.current_url,
            'title': browser.title
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/viewport')
def get_viewport():
    try:
        browser = get_browser_for_session()
        viewport_width = browser.execute_script("return window.innerWidth")
        viewport_height = browser.execute_script("return window.innerHeight")
        
        return jsonify({
            'width': viewport_width,
            'height': viewport_height
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
