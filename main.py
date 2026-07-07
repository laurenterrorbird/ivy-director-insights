"""
Google Cloud Function entry point for Kitchen Report automation
This is the main function that Cloud Functions will call
"""

import os
import json

def main(request):
    """
    Cloud Function entry point (HTTP trigger)
    
    Args:
        request: Flask request object (for Cloud Functions HTTP trigger)
    
    Returns:
        Tuple of (response dict, status code)
    """
    # Optional: Check for secret token
    secret_token = os.environ.get('SECRET_TOKEN')
    if secret_token:
        request_token = None
        if hasattr(request, 'args'):
            request_token = request.args.get('token')
        elif hasattr(request, 'get_json'):
            data = request.get_json(silent=True) or {}
            request_token = data.get('token')
        
        if not request_token:
            request_token = request.headers.get('X-Token') if hasattr(request, 'headers') else None
        
        if request_token != secret_token:
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Unauthorized'})
            }, 401
    
    try:
        # Import here to avoid issues if kitchen.py has import errors
        from kitchen import download_report
        
        # Set environment variables for headless operation
        os.environ['HEADLESS'] = 'true'
        os.environ['USE_BROWSER_PASTE'] = 'false'
        
        # Run the report download
        download_report(format_types=["CSV", "PDF"])
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'message': 'Kitchen report automation completed successfully'
            })
        }, 200
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        error_trace = traceback.format_exc()
        print(f"Error: {error_msg}")
        print(error_trace)
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': error_msg,
                'trace': error_trace
            })
        }, 500

