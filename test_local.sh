#!/bin/bash
# Local test script for kitchen.py
# This runs kitchen.py locally without needing GitHub Actions

# Set your credentials here (or export them in your shell)
# You can also create a .env file and source it, or just export them before running

# Check if credentials are set
if [ -z "$SEMINARDESK_USERNAME" ] || [ -z "$SEMINARDESK_PASSWORD" ]; then
    echo "⚠️  Credentials not set in environment."
    echo ""
    echo "Set them before running:"
    echo "  export SEMINARDESK_USERNAME='your@email.com'"
    echo "  export SEMINARDESK_PASSWORD='your-password'"
    echo ""
    echo "Or edit this script to set them directly (less secure)."
    exit 1
fi

# Check if Google credentials exist
if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ ! -f "credentials.json" ]; then
    echo "⚠️  Google credentials not found."
    echo "   Either:"
    echo "   - Put credentials.json in this folder, or"
    echo "   - Set GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json"
    echo ""
    echo "   (Google Sheets upload will be skipped if not available)"
    echo ""
fi

# Run in non-headless mode so you can see what's happening
# Set HEADLESS=true if you want headless mode
export HEADLESS="${HEADLESS:-false}"
export USE_BROWSER_PASTE="${USE_BROWSER_PASTE:-true}"

echo "🚀 Running kitchen.py locally..."
echo "   HEADLESS=$HEADLESS"
echo "   USE_BROWSER_PASTE=$USE_BROWSER_PASTE"
echo ""

python3 kitchen.py
