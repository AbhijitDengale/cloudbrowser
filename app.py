import os
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import base64
import re
from urllib.parse import urljoin, urlparse

app = Flask(__name__)
CORS(app)

# Track the current URL for relative link resolution
current_url = "https://www.google.com"

def is_valid_url(url):
    """Check if the URL is valid"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def transform_html(html_content, base_url):
    """Transform the HTML to proxy all links through our service"""
    global current_url
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Transform links (a tags)
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href.startswith("#"):  # Skip anchor links
            continue
        
        # Convert relative URLs to absolute
        absolute_url = urljoin(base_url, href)
        
        # Update the href to go through our proxy
        a_tag["href"] = f"/browse?url={absolute_url}"
        a_tag["target"] = "_self"  # Prevent opening in new tab
    
    # Transform forms
    for form in soup.find_all("form", action=True):
        action_url = form["action"]
        if action_url:
            absolute_action = urljoin(base_url, action_url)
            form["action"] = f"/form_submit?url={absolute_action}"
    
    # Handle CSS imports and stylesheets
    for link in soup.find_all("link", rel="stylesheet", href=True):
        href = link["href"]
        absolute_url = urljoin(base_url, href)
        link["href"] = f"/proxy_resource?url={absolute_url}"
    
    # Handle scripts
    for script in soup.find_all("script", src=True):
        src = script["src"]
        absolute_url = urljoin(base_url, src)
        script["src"] = f"/proxy_resource?url={absolute_url}"
    
    # Handle images
    for img in soup.find_all("img", src=True):
        src = img["src"]
        absolute_url = urljoin(base_url, src)
        img["src"] = f"/proxy_resource?url={absolute_url}"
    
    # Inject our control panel
    control_panel = soup.new_tag("div")
    control_panel["class"] = "cloud-browser-controls"
    control_panel["style"] = "position:fixed;top:0;left:0;right:0;background:#f1f1f1;padding:10px;z-index:99999;display:flex;"
    
    url_input = soup.new_tag("input")
    url_input["type"] = "text"
    url_input["id"] = "url-input"
    url_input["value"] = base_url
    url_input["style"] = "flex:1;margin-right:10px;padding:5px;"
    
    go_button = soup.new_tag("button")
    go_button["onclick"] = "window.location.href='/browse?url='+document.getElementById('url-input').value"
    go_button["style"] = "padding:5px 15px;background:#4285f4;color:white;border:none;cursor:pointer;"
    go_button.string = "Go"
    
    back_button = soup.new_tag("button")
    back_button["onclick"] = "window.history.back()"
    back_button["style"] = "padding:5px 15px;margin-right:5px;background:#4285f4;color:white;border:none;cursor:pointer;"
    back_button.string = "Back"
    
    control_panel.append(back_button)
    control_panel.append(url_input)
    control_panel.append(go_button)
    
    # Add the control panel to the body
    if soup.body:
        soup.body.insert(0, control_panel)
    
    return str(soup)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/browse')
def browse():
    global current_url
    url = request.args.get('url', 'https://www.google.com')
    
    if not is_valid_url(url):
        url = "https://www.google.com"
    
    try:
        # Add headers to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        # Update current_url for relative link resolution
        current_url = url
        
        response = requests.get(url, headers=headers)
        content_type = response.headers.get('Content-Type', '')
        
        # If the content is HTML, transform it
        if 'text/html' in content_type:
            transformed_html = transform_html(response.text, url)
            return transformed_html
        else:
            # For non-HTML content, just pass it through
            return response.content, 200, {'Content-Type': content_type}
    
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/proxy_resource')
def proxy_resource():
    url = request.args.get('url')
    if not url:
        return "URL parameter is required", 400
    
    try:
        # Add headers to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': '*/*',
            'Referer': current_url,
        }
        
        response = requests.get(url, headers=headers)
        return response.content, 200, {'Content-Type': response.headers.get('Content-Type', 'text/plain')}
    
    except Exception as e:
        return str(e), 500

@app.route('/form_submit', methods=['POST', 'GET'])
def form_submit():
    url = request.args.get('url')
    if not url:
        return "URL parameter is required", 400
    
    try:
        # Handle both GET and POST form submissions
        if request.method == 'POST':
            # Forward the POST request with its form data
            response = requests.post(url, data=request.form)
        else:
            # Forward the GET request with its query parameters
            response = requests.get(url, params=request.args)
        
        # Process the response
        content_type = response.headers.get('Content-Type', '')
        if 'text/html' in content_type:
            transformed_html = transform_html(response.text, url)
            return transformed_html
        else:
            return response.content, 200, {'Content-Type': content_type}
    
    except Exception as e:
        return render_template('error.html', error=str(e))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
