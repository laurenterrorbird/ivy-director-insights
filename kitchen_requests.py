"""
Alternative: Simple requests-based approach (if PDF URL is directly accessible after login)

This is MUCH faster and simpler if the website allows session-based access.
No browser needed - just HTTP requests.

Install: pip install requests beautifulsoup4
"""

import requests
from datetime import datetime
import os

# Configuration
LOGIN_URL = "https://institutvajrayogini.seminardesk.com/Account/Login"
PDF_URL = "https://institutvajrayogini.seminardesk.com/path/to/report.pdf"  # Direct PDF URL
USERNAME = "lauren@institutvajrayogini.fr"
PASSWORD = "taralauren888"
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")

def ensure_download_dir():
    """Create downloads directory if it doesn't exist"""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    return DOWNLOAD_DIR

def login_and_download_pdf():
    """Login using requests session and download PDF"""
    ensure_download_dir()
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    try:
        # Step 1: Get login page to retrieve any CSRF tokens or cookies
        print("Fetching login page...")
        login_page = session.get(LOGIN_URL)
        login_page.raise_for_status()
        
        # Step 2: Login (adjust form field names as needed)
        print("Logging in...")
        login_data = {
            "txtUser": USERNAME,
            "txtPass": PASSWORD,
            # Add any other required fields (CSRF tokens, etc.)
        }
        
        login_response = session.post(LOGIN_URL, data=login_data)
        login_response.raise_for_status()
        
        # Verify login success (check for redirect or success indicator)
        if "Default.aspx" in login_response.url or login_response.status_code == 200:
            print("✓ Login successful")
        else:
            print("⚠️ Login may have failed - check credentials")
            return
        
        # Step 3: Download PDF using the authenticated session
        print(f"Downloading PDF from: {PDF_URL}")
        pdf_response = session.get(PDF_URL, stream=True)
        pdf_response.raise_for_status()
        
        # Check if we got a PDF
        content_type = pdf_response.headers.get('Content-Type', '')
        if 'pdf' not in content_type.lower():
            print(f"⚠️ Warning: Expected PDF but got {content_type}")
            print("This might mean the URL requires JavaScript or browser interaction.")
            print("Consider using the Playwright version instead.")
        
        # Save the PDF
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"kitchen_report_{timestamp}.pdf"
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        
        with open(filepath, 'wb') as f:
            for chunk in pdf_response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✓ PDF downloaded to: {filepath}")
        print(f"  File size: {os.path.getsize(filepath)} bytes")
        
    except requests.exceptions.RequestException as e:
        print(f"\nAn error occurred: {str(e)}")
        print("\nIf this fails, the site likely requires JavaScript execution.")
        print("Use the Playwright version (kitchen.py) instead.")
        raise

if __name__ == "__main__":
    login_and_download_pdf()






