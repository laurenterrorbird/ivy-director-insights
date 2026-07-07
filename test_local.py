#!/usr/bin/env python3
"""
Local test wrapper for kitchen.py
Run this instead of kitchen.py directly for easier local testing.

Usage:
    python3 test_local.py
    
Or set credentials via environment variables:
    export SEMINARDESK_USERNAME='your@email.com'
    export SEMINARDESK_PASSWORD='your-password'
    python3 test_local.py
"""

import os
import sys

# Import the main script
from kitchen import download_report

def main():
    """Run kitchen.py locally with user-friendly setup"""
    
    # Check for credentials
    username = os.getenv("SEMINARDESK_USERNAME") or os.getenv("KITCHEN_USERNAME")
    password = os.getenv("SEMINARDESK_PASSWORD") or os.getenv("KITCHEN_PASSWORD")
    
    if not username or not password:
        print("⚠️  SeminarDesk credentials not set.")
        print("\nSet them via environment variables:")
        print("  export SEMINARDESK_USERNAME='your@email.com'")
        print("  export SEMINARDESK_PASSWORD='your-password'")
        print("\nOr edit this file to set them directly (less secure).")
        sys.exit(1)
    
    # Check for Google credentials
    has_google_creds = (
        os.path.exists("credentials.json") or 
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    )
    
    if not has_google_creds:
        print("⚠️  Google credentials not found.")
        print("   Google Sheets upload will be skipped.")
        print("   To enable: put credentials.json in this folder or set GOOGLE_APPLICATION_CREDENTIALS")
        print()
    
    # Set defaults for local testing
    # Non-headless so you can see the browser
    headless = os.getenv("HEADLESS", "false").lower() == "true"
    # Use browser paste for local testing (no API credentials needed)
    use_browser_paste = os.getenv("USE_BROWSER_PASTE", "true").lower() == "true"
    
    print("🚀 Running kitchen.py locally...")
    print(f"   HEADLESS={headless}")
    print(f"   USE_BROWSER_PASTE={use_browser_paste}")
    print()
    
    # Run the main function
    try:
        download_report(
            format_types=["CSV", "PDF"],
            upload_to_sheets=has_google_creds,  # Only upload if credentials available
            use_browser_paste=use_browser_paste
        )
        print("\n✅ Done!")
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
