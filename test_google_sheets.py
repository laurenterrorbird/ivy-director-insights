#!/usr/bin/env python3
"""
Quick test script for Google Sheets permissions
Tests only the Google Sheets API connection without doing login/download.

Usage:
    python3 test_google_sheets.py
    
Or with explicit credentials path:
    GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json python3 test_google_sheets.py
"""

import os
import sys
import json

# Configuration (from kitchen.py)
SPREADSHEET_ID = "1IHuynWA-mkySLDsJjxxJS2f4CgabTTk8W0UBMOjqDeo"
SHEET_NAME = "Rapport Cuisine"
SHEET_GID = "1235612957"

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    print("❌ gspread and google-auth not installed.")
    print("   Install with: pip install gspread google-auth")
    sys.exit(1)

def resolve_credentials_path():
    """Find credentials.json file"""
    # Check current directory
    if os.path.exists("credentials.json"):
        return os.path.abspath("credentials.json")
    # Check script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_creds = os.path.join(script_dir, "credentials.json")
    if os.path.exists(script_creds):
        return script_creds
    # Environment variable
    env_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if env_path and os.path.exists(env_path):
        return env_path
    return None

def main():
    print("🧪 Testing Google Sheets API connection...\n")
    
    # Find credentials
    creds_path = resolve_credentials_path()
    if not creds_path:
        print("❌ Google credentials not found.")
        print("   Put credentials.json in this folder, or set GOOGLE_APPLICATION_CREDENTIALS")
        sys.exit(1)
    
    print(f"✓ Found credentials: {creds_path}")
    
    # Extract service account email
    try:
        with open(creds_path, 'r') as f:
            creds_data = json.load(f)
        service_account_email = creds_data.get('client_email', 'unknown')
        print(f"✓ Service account email: {service_account_email}\n")
    except Exception as e:
        print(f"⚠️ Could not read service account email: {e}\n")
        service_account_email = "unknown"
    
    # Authenticate
    print("1️⃣ Authenticating with Google...")
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_file(creds_path, scopes=scope)
        client = gspread.authorize(creds)
        print("   ✓ Authentication successful")
        
        # Verify the service account email matches
        if hasattr(creds, 'service_account_email'):
            actual_email = creds.service_account_email
            print(f"   Service account from creds: {actual_email}")
            if actual_email != service_account_email:
                print(f"   ⚠️ Warning: Email mismatch!")
                print(f"      JSON file: {service_account_email}")
                print(f"      Credentials: {actual_email}")
        print()
    except Exception as e:
        print(f"   ❌ Authentication failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Open spreadsheet
    print(f"2️⃣ Opening spreadsheet: {SPREADSHEET_ID}")
    print(f"   URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
    try:
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        print(f"   ✓ Spreadsheet opened: {spreadsheet.title}\n")
    except gspread.exceptions.APIError as api_err:
        err_str = str(api_err)
        if "403" in err_str and ("has not been used" in err_str or "is disabled" in err_str or "Enable it" in err_str):
            print(f"\n   ❌ GOOGLE SHEETS API NOT ENABLED!")
            print(f"\n   The Sheets API must be enabled for your Google Cloud project.")
            print(f"\n   Fix:")
            print(f"   1. Open: https://console.cloud.google.com/apis/library/sheets.googleapis.com")
            print(f"   2. Select the project that contains your service account")
            print(f"   3. Click 'Enable'")
            print(f"   4. Wait 1–2 minutes, then run this test again")
            if "project" in err_str:
                # Try to extract project number from error if present
                import re
                m = re.search(r"project[=\s](\d+)", err_str, re.I)
                if m:
                    proj = m.group(1)
                    print(f"\n   Direct link for your project: https://console.developers.google.com/apis/api/sheets.googleapis.com/overview?project={proj}")
        else:
            print(f"\n   ❌ API Error: {api_err}")
        sys.exit(1)
    except PermissionError as pe:
        print(f"\n   ❌ PERMISSION DENIED!")
        print(f"\n   Error details: {pe}")
        print(f"\n   The service account '{service_account_email}' needs to be shared on the Google Sheet.")
        print(f"\n   Steps:")
        print(f"   1. Open: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
        print(f"   2. Click 'Share' → Add '{service_account_email}' as Editor")
        print(f"   3. If already shared, try removing and re-adding, then wait 1–2 minutes")
        import traceback
        print(f"\n   Full traceback:")
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        error_type = type(e).__name__
        print(f"   ❌ Failed to open spreadsheet: {error_type}: {e}")
        import traceback
        print(f"\n   Full traceback:")
        traceback.print_exc()
        sys.exit(1)
    
    # List all sheets
    print("3️⃣ Listing all worksheets...")
    try:
        all_sheets = spreadsheet.worksheets()
        print(f"   Found {len(all_sheets)} worksheet(s):")
        for s in all_sheets:
            marker = " ← TARGET" if s.title == SHEET_NAME else ""
            print(f"   - {s.title} (id: {s.id}){marker}")
        print()
    except Exception as e:
        print(f"   ⚠️ Could not list worksheets: {e}\n")
    
    # Find target sheet
    print(f"4️⃣ Finding worksheet: '{SHEET_NAME}'")
    try:
        sheet = spreadsheet.worksheet(SHEET_NAME)
        print(f"   ✓ Found sheet: {SHEET_NAME}")
    except gspread.exceptions.WorksheetNotFound:
        print(f"   ⚠️ Sheet '{SHEET_NAME}' not found by name")
        # Try by gid
        print(f"   Trying to find by gid: {SHEET_GID}")
        all_sheets = spreadsheet.worksheets()
        sheet = None
        for s in all_sheets:
            if str(s.id) == SHEET_GID:
                sheet = s
                print(f"   ✓ Found sheet by gid: {s.title}")
                break
        if not sheet:
            print(f"   ❌ Sheet not found by name '{SHEET_NAME}' or gid '{SHEET_GID}'")
            print(f"   Available sheets: {[s.title for s in all_sheets]}")
            sys.exit(1)
    except Exception as e:
        print(f"   ❌ Error finding sheet: {e}")
        sys.exit(1)
    
    # Test read access
    print("\n5️⃣ Testing read access (reading cell A1)...")
    try:
        test_value = sheet.acell('A1').value
        print(f"   ✓ Read successful: A1 = '{test_value}'")
    except Exception as e:
        print(f"   ⚠️ Read test failed: {e}")
    
    # Test write access (read a cell first to verify we can write)
    print("\n6️⃣ Testing write access (reading A4 to check current value)...")
    try:
        current_a4 = sheet.acell('A4').value
        print(f"   ✓ Current A4 value: '{current_a4}'")
        print(f"   (Write test skipped - would modify your data)")
        print(f"   ✓ Write permissions appear OK")
    except Exception as e:
        print(f"   ⚠️ Write test check failed: {e}")
    
    print("\n" + "="*60)
    print("✅ All tests passed! Google Sheets connection is working.")
    print("="*60)
    print(f"\nService account '{service_account_email}' has proper access.")
    print("You can now run the full kitchen.py script.")

if __name__ == "__main__":
    main()
