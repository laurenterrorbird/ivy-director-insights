/**
 * Copy data from SeminarDesk Google Sheet "Planning_Names" to Planning Google Sheet "SD_Benevoles"
 * 
 * Source: Planning_Names sheet, columns A3:E (all rows from row 3)
 * Destination: SD_Benevoles sheet, columns A3:E (starting at row 3)
 * 
 * Only copies if the source data has changed (detected via hash comparison)
 */

/**
 * Calculate a hash/checksum of the data to detect changes
 */
function calculateDataHash(data) {
  const dataString = JSON.stringify(data);
  const hash = Utilities.computeDigest(
    Utilities.DigestAlgorithm.MD5,
    dataString,
    Utilities.Charset.UTF_8
  );
  return hash.map(byte => ('0' + (byte & 0xFF).toString(16)).slice(-2)).join('');
}

function copyPlanningNamesToBenevoles() {
  // ⚙️ CONFIGURATION - Update these with your spreadsheet IDs
  const SOURCE_SPREADSHEET_ID = 'YOUR_SEMINARDESK_SPREADSHEET_ID_HERE';
  const DESTINATION_SPREADSHEET_ID = 'YOUR_PLANNING_SPREADSHEET_ID_HERE';
  
  const SOURCE_SHEET_NAME = 'Planning_Names';
  const DESTINATION_SHEET_NAME = 'SD_Benevoles';
  
  try {
    // Open source spreadsheet
    const sourceSS = SpreadsheetApp.openById(SOURCE_SPREADSHEET_ID);
    const sourceSheet = sourceSS.getSheetByName(SOURCE_SHEET_NAME);
    
    if (!sourceSheet) {
      throw new Error(`Source sheet "${SOURCE_SHEET_NAME}" not found in SeminarDesk spreadsheet`);
    }
    
    // Get data from source (A3:E, all rows from row 3 onwards)
    const lastRow = sourceSheet.getLastRow();
    if (lastRow < 3) {
      Logger.log('No data to copy (source sheet has less than 3 rows)');
      return;
    }
    
    const sourceData = sourceSheet.getRange(3, 1, lastRow - 2, 5).getValues(); // A3:E, starting from row 3
    
    if (sourceData.length === 0) {
      Logger.log('No data to copy');
      return;
    }
    
    // Calculate hash of current source data
    const currentHash = calculateDataHash(sourceData);
    
    // Open destination spreadsheet
    const destSS = SpreadsheetApp.openById(DESTINATION_SPREADSHEET_ID);
    let destSheet = destSS.getSheetByName(DESTINATION_SHEET_NAME);
    
    if (!destSheet) {
      // Create sheet if it doesn't exist
      destSheet = destSS.insertSheet(DESTINATION_SHEET_NAME);
      Logger.log(`Created destination sheet "${DESTINATION_SHEET_NAME}"`);
    }
    
    // Check stored hash (stored in cell Z1)
    const storedHashCell = destSheet.getRange(1, 26); // Column Z, row 1
    const storedHash = storedHashCell.getValue();
    
    // Compare hashes - only copy if data has changed
    if (storedHash === currentHash) {
      Logger.log('⏭️  No changes detected - skipping copy (data unchanged)');
      return;
    }
    
    Logger.log(`📝 Changes detected - copying data (old hash: ${storedHash || 'none'}, new hash: ${currentHash})`);
    
    // Clear existing data in destination range (A3:E) if needed, or just overwrite
    const destLastRow = destSheet.getLastRow();
    if (destLastRow >= 3) {
      // Clear existing data from row 3 onwards in columns A:E
      destSheet.getRange(3, 1, destLastRow - 2, 5).clearContent();
    }
    
    // Write data to destination starting at A3
    destSheet.getRange(3, 1, sourceData.length, 5).setValues(sourceData);
    
    // Store the new hash in Z1 for next comparison
    storedHashCell.setValue(currentHash);
    
    Logger.log(`✅ Successfully copied ${sourceData.length} rows from "${SOURCE_SHEET_NAME}" to "${DESTINATION_SHEET_NAME}"`);
    
  } catch (error) {
    Logger.log(`❌ Error: ${error.message}`);
    throw error;
  }
}

/**
 * Test function to verify spreadsheet access
 */
function testSpreadsheetAccess() {
  const SOURCE_SPREADSHEET_ID = 'YOUR_SEMINARDESK_SPREADSHEET_ID_HERE';
  const DESTINATION_SPREADSHEET_ID = 'YOUR_PLANNING_SPREADSHEET_ID_HERE';
  
  try {
    const sourceSS = SpreadsheetApp.openById(SOURCE_SPREADSHEET_ID);
    Logger.log(`✅ Source spreadsheet accessible: ${sourceSS.getName()}`);
    
    const destSS = SpreadsheetApp.openById(DESTINATION_SPREADSHEET_ID);
    Logger.log(`✅ Destination spreadsheet accessible: ${destSS.getName()}`);
    
  } catch (error) {
    Logger.log(`❌ Error accessing spreadsheets: ${error.message}`);
  }
}
