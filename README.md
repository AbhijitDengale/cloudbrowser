# Cloud Browser

A lightweight cloud-based web browser service optimized to run on Render's free tier with 500MB RAM constraints. This application allows users to browse external websites through a proxy server.

## Features

- **Low Resource Usage**: Optimized to run on Render's free tier (500MB RAM)
- **Web Proxy**: Browse any website through the proxy service
- **Link Transformation**: All links are automatically rewritten to work through the proxy
- **Form Support**: Handles both GET and POST form submissions
- **Resource Proxying**: Images, stylesheets, and scripts are proxied through the service

## How It Works

This cloud browser works as a proxy service that:

1. Fetches web pages on behalf of the user
2. Transforms HTML content to route all links and resources through the proxy
3. Renders the transformed content in the user's browser
4. Provides a simple navigation interface at the top of each page

## Enhanced Version

A more powerful Selenium-based version is also included in this repository:

- **Full Browser Engine**: Uses headless Chrome to render pages server-side
- **Session Support**: Maintains browser state between requests
- **JavaScript Support**: Fully executes JavaScript on the server
- **Complex Applications**: Supports applications like Google Colab and Gmail
- **Interactive Controls**: Provides click/keyboard interaction with remote pages

The enhanced version requires more resources (standard plan on Render) but provides a much more complete browsing experience.

## Choosing the Right Version

- **Basic Version (app.py)**: Use for simple websites with low resource requirements
- **Enhanced Version (selenium_app.py)**: Use for complex applications (Colab, Gmail, etc.)

The enhanced version allows you to interact with any website that works in Chrome, including those requiring login, complex JavaScript, and session management.

## Local Development

### Prerequisites

- Python 3.8 or higher

### Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Run the application: `python app.py`
6. Open your browser and navigate to `http://localhost:5000`

## Deployment to Render

### Method 1: Manual Deployment

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Set the following:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Environment Variables: `PYTHON_VERSION=3.9.0`
4. Select the Free plan
5. Click "Create Web Service"

### Method 2: Using render.yaml (Infrastructure as Code)

1. Push the code to GitHub including the `render.yaml` file
2. Go to your Render dashboard
3. Click "Blueprint" to create a new Blueprint Instance
4. Connect to your GitHub repository
5. Click "Apply" to create the service as defined in `render.yaml`

## Limitations

- **JavaScript Support**: Complex JavaScript-heavy sites may not function correctly
- **Streaming Content**: Video streaming sites may not work properly
- **Authentication**: Some sites with advanced authentication mechanisms might block proxy access
- **Performance**: The free tier has limited resources, so performance may be affected for complex sites
- **Usage Limits**: Render's free tier has monthly usage limits

## Architecture

- **Flask**: Web framework
- **BeautifulSoup**: HTML parsing and transformation
- **Requests**: HTTP client for fetching web content
- **Flask-CORS**: Cross-Origin Resource Sharing support
- **Gunicorn**: WSGI HTTP Server for production deployment

## Security Considerations

This is a basic implementation and may not provide complete security. Consider the following:

- The service proxies all content, including potentially malicious scripts
- No content sanitization is implemented
- User data may be visible to the service

## Future Enhancements

- Add user authentication
- Implement content caching for better performance
- Add cookie and session management
- Improve JavaScript support
- Add HTTPS enforcement
- Implement rate limiting
