/**
 * Google Apps Script to trigger Kitchen Report automation
 * 
 * This script can be set to run on a schedule using Google Apps Script's
 * built-in time-driven triggers. It will call a Cloud Function that runs
 * the actual Playwright script.
 * 
 * SETUP:
 * 1. Deploy the Cloud Function (see DEPLOYMENT.md)
 * 2. Get the Cloud Function URL
 * 3. Set the CLOUD_FUNCTION_URL below
 * 4. Set up a time-driven trigger in Apps Script:
 *    - Edit → Current project's triggers
 *    - Add trigger → Choose function: triggerKitchenReport
 *    - Event source: Time-driven
 *    - Type: Day timer
 *    - Time of day: 2am (or your preferred time)
 */

const CLOUD_FUNCTION_URL = 'YOUR_CLOUD_FUNCTION_URL_HERE'; // Replace with your Cloud Function URL

/**
 * Main function to trigger the kitchen report automation
 * This will be called by the time-driven trigger
 */
function triggerKitchenReport() {
  try {
    Logger.log('Triggering kitchen report automation...');
    
    // Call the Cloud Function
    const response = UrlFetchApp.fetch(CLOUD_FUNCTION_URL, {
      method: 'GET',
      muteHttpExceptions: true
    });
    
    const statusCode = response.getResponseCode();
    const responseText = response.getContentText();
    
    if (statusCode === 200) {
      Logger.log('✓ Kitchen report automation triggered successfully');
      Logger.log('Response: ' + responseText);
      
      // Optional: Send email notification
      // sendEmailNotification('Kitchen Report', 'Report automation completed successfully');
    } else {
      Logger.log('⚠️ Error triggering automation. Status: ' + statusCode);
      Logger.log('Response: ' + responseText);
      
      // Optional: Send error notification
      // sendEmailNotification('Kitchen Report Error', 'Status: ' + statusCode + '\n' + responseText);
    }
    
    return {
      success: statusCode === 200,
      statusCode: statusCode,
      message: responseText
    };
    
  } catch (error) {
    Logger.log('❌ Error: ' + error.toString());
    // sendEmailNotification('Kitchen Report Error', error.toString());
    throw error;
  }
}

/**
 * Optional: Send email notification
 * Uncomment and customize if you want email notifications
 */
function sendEmailNotification(subject, body) {
  const email = Session.getActiveUser().getEmail();
  MailApp.sendEmail({
    to: email,
    subject: subject,
    body: body
  });
}

/**
 * Test function - run this manually to test the trigger
 */
function testTrigger() {
  triggerKitchenReport();
}






