/***** CONFIG *****/
const RAW_SHEET_NAME      = 'SD';        // raw SeminarDesk webhook data
const FLAT_SHEET_NAME     = 'Flattened'; // one row per guest
const LOG_SHEET_NAME      = 'Log';
const TZ                  = 'Europe/Paris';

/***** WEBHOOK ENTRYPOINT *****/
function doPost(e) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(RAW_SHEET_NAME);
  if (!sheet) return ContentService.createTextOutput('Missing sheet SD');
  
  // Parse incoming data - preserve columns A, B, C if they exist in the payload
  const raw = e.postData ? e.postData.contents : '';
  const ts = new Date();
  
  // Try to parse as JSON first (if webhook sends JSON)
  try {
    const json = JSON.parse(raw);
    // If JSON, extract the payload string and metadata
    const webhookId = json.id || '';
    const version = json.version || '';
    const extendedPayload = json.extendedPayload || '';
    const payloadStr = json.payload || raw;
    
    sheet.appendRow([
      webhookId,
      version,
      JSON.stringify(extendedPayload),
      payloadStr
    ]);
  } catch (e) {
    // If not JSON, just append raw to column D (preserving A, B, C structure)
    // Column A: webhook ID (if available)
    // Column B: version (if available)  
    // Column C: extended payload metadata (if available)
    // Column D: actual payload string
    sheet.appendRow([
      Utilities.getUuid(), // Generate ID if not provided
      '1',
      '{}',
      raw
    ]);
  }
  
  return ContentService.createTextOutput('OK');
}

/***** UTILITIES *****/
function logRun_(type, msg, details) {
  const ss = SpreadsheetApp.getActive();
  let log = ss.getSheetByName(LOG_SHEET_NAME) || ss.insertSheet(LOG_SHEET_NAME);
  if (log.getLastRow() === 0) {
    log.appendRow(['Timestamp', 'Type', 'Message', 'Details']);
  }
  log.appendRow([
    Utilities.formatDate(new Date(), TZ, 'MM/dd/yyyy HH:mm:ss'),
    type, msg, details || ''
  ]);
}

function extractAll_(str, regex) {
  const out = [];
  let m;
  while ((m = regex.exec(str)) !== null) {
    out.push(m.slice(1));
  }
  return out;
}

function extractOne_(str, regex) {
  const m = str.match(regex);
  return m ? m[1] : '';
}

function isoToDate_(iso) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    return Utilities.formatDate(d, TZ, 'dd/MM/yyyy');
  } catch (e) {
    return '';
  }
}

function isoToDateValue_(iso) {
  // Returns date value (number) for filtering/comparison
  if (!iso) return '';
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    return d;
  } catch (e) {
    return '';
  }
}

function parseNumber_(v) {
  const n = parseFloat(v);
  return isNaN(n) ? 0 : n;
}

// Extract all additionalFieldValues into a joined string "Name: value | Name2: value2"
function extractAdditionalFields_(sectionStr) {
  if (!sectionStr) return '';
  const matches = extractAll_(sectionStr, /field=\{id=\d+,\s*name=([^}]+)\},\s*value=(.*?)(?=,\s*source=)/g);
  if (!matches || matches.length === 0) return '';
  return matches.map(m => `${m[0].trim()}: ${m[1].trim()}`).join(' | ');
}

/***** PARSING *****/
function parsePayloadToGuestRows_(payloadStr) {
  if (!payloadStr || typeof payloadStr !== 'string') return [];

  // Booking-level
  const bookingId    = extractOne_(payloadStr, /payload=\{id=(\d+),/);
  if (!bookingId) return [];

  const bookerName   = extractOne_(payloadStr, /booker=\{id=\d+, name=([^}]+)\}/);
  const bookingStatus= extractOne_(payloadStr, /payload=\{id=\d+,[^}]*?status=([A-Z_]+),/);
  // Capture remarks - they can contain commas, so capture up to the next known field name
  // externalRemarks is followed by internalRemarks
  const externalRem  = extractOne_(payloadStr, /externalRemarks=(.*?)(?=,\s*internalRemarks=)/);
  // internalRemarks is followed by paymentMethod or other fields
  const internalRem  = extractOne_(payloadStr, /internalRemarks=(.*?)(?=,\s*paymentMethod=)/) ||
                       extractOne_(payloadStr, /internalRemarks=(.*?)(?=,\s*specialRequestsPriceList=)/) ||
                       extractOne_(payloadStr, /internalRemarks=(.*?)(?=,\s*labels=)/) ||
                       extractOne_(payloadStr, /internalRemarks=(.*?)(?=,\s*marker=)/) ||
                       extractOne_(payloadStr, /internalRemarks=(.*?)(?=,\s*referenceNumbers=)/) ||
                       extractOne_(payloadStr, /internalRemarks=(.*?)(?=,\s*voucherCode=)/) ||
                       extractOne_(payloadStr, /internalRemarks=(.*?)(?=,\s*guests=)/);
  const openBalance  = parseNumber_(extractOne_(payloadStr, /openBalance=([-\d.]+)/));
  const onlinePayStat= extractOne_(payloadStr, /onlinePaymentStatus=([A-Z_]+|null)/);
  const changedAt    = extractOne_(payloadStr, /changedAt=([0-9:\-T.]+Z)/);
  const confirmationDate = extractOne_(payloadStr, /confirmationDate=([0-9:\-T.]+Z)/);
  const bookingAdditional = extractAdditionalFields_(extractOne_(payloadStr, /additionalFieldValues=([\s\S]*?)(?:\}, confirmationDate=|$)/));

  // Sum payments.amount
  let paid = 0;
  const paymentMatches = extractAll_(payloadStr, /payments=\{[^}]*amount=([-\d.]+)/g);
  paymentMatches.forEach(m => {
    paid += parseNumber_(m[0]);
  });

  // Guests blocks - extract all guest entries
  const guestsSection = extractOne_(payloadStr, /guests=([\s\S]*?), numberOfInvoices=/);
  if (!guestsSection) return [];

  // Split guests by finding each guest block
  const guestBlocks = [];
  // Pattern: {id=XXXX, guest={profile=...}...} followed by either },{id= or }, numberOfInvoices
  const guestPattern = /{id=(\d+),\s*guest=\{profile=\{id=\d+,\s*name=[\s\S]*?(?=},\s*{id=\d+,\s*guest=|},\s*numberOfInvoices=)/g;
  let gm;
  let lastIndex = 0;
  
  while ((gm = guestPattern.exec(guestsSection)) !== null) {
    // Extract from start of match to end of this guest block
    const startIdx = gm.index;
    const matchStr = gm[0];
    
    // Find the end of this guest block (before next guest or numberOfInvoices)
    let endIdx = guestsSection.indexOf('}, {id=', startIdx + matchStr.length);
    if (endIdx === -1) {
      endIdx = guestsSection.indexOf('}, numberOfInvoices=', startIdx + matchStr.length);
    }
    if (endIdx === -1) {
      endIdx = guestsSection.length;
    }
    
    guestBlocks.push(guestsSection.substring(startIdx, endIdx + 2)); // +2 for '},'
  }
  
  // Fallback: if no matches, treat entire section as one guest
  if (guestBlocks.length === 0) {
    guestBlocks.push(guestsSection);
  }

  const rows = [];

  guestBlocks.forEach(block => {
    const guestId      = extractOne_(block, /id=(\d+), guest=\{profile=/);
    const guestName    = extractOne_(block, /name=([^,}]+), age=/);
    const age          = extractOne_(block, /age=(\d+)/);
    const gender       = extractOne_(block, /gender=([A-Z]+)/);
    const status       = extractOne_(block, /status=([A-Z_]+), guestType=/);
    const priceLevel   = extractOne_(block, /priceLevel=\{id=\d+, name=([^}]+)\}/);
    const attendance   = extractOne_(block, /attendanceType=([A-Z_]+)/);
    const eventId      = extractOne_(block, /event=\{id=(\d+), name=/);
    const eventName    = extractOne_(block, /event=\{id=\d+, name=([^}]+)\}/);
    const eventDateLbl = extractOne_(block, /eventDate=\{id=\d+, name=([^}]+)\}/);

    // Items - extract all item blocks
    const itemPattern = /{id=(\d+),\s*type=\{type=([A-Z_]+)[^}]*\},\s*status=([A-Z_]+),\s*begin=([0-9:\-T.]+Z),\s*end=([0-9:\-T.]+Z),\s*text=([^,}]+),\s*priceList=\{id=\d+,\s*name=([^}]+)\},\s*priceListItemId=([\d]+|null)?,\s*calculatedPrice=([-\d.]+),\s*actualPrice=([-\d.]+)/g;
    const itemMatches = extractAll_(block, itemPattern);

    let accBegin='', accEnd='';
    let lodgingText='', lodgingPrice=0;
    let mealsText='', mealsPrice=0;
    let eventFee=0;
    let miscTotal=0;
    let totalCalc=0, totalAct=0;

    itemMatches.forEach(m => {
      const logicalType = m[1]; // type field
      const begin = m[3], end = m[4];
      const text = m[5], actual = parseNumber_(m[10]), calc = parseNumber_(m[9]);
      const price = calc || actual;
      totalAct += actual; 
      totalCalc += calc;

      if (logicalType === 'ACCOMMODATION') {
        lodgingText = text;
        lodgingPrice += price;
        accBegin = begin; 
        accEnd = end;
      } else if (logicalType === 'MEALS') {
        mealsText = text;
        mealsPrice += price;
      } else if (logicalType === 'EVENT') {
        eventFee += price;
      } else {
        miscTotal += price;
      }
    });

    // Nights from accommodation range if present
    let nights = '';
    if (accBegin && accEnd) {
      const b = new Date(accBegin); 
      const e = new Date(accEnd);
      const diffDays = Math.max(0, Math.round((e - b) / (1000*60*60*24)));
      nights = diffDays;
    }

    // Use accommodation dates if available, otherwise first item dates
    const arrivalUTC = accBegin || (itemMatches[0] ? itemMatches[0][3] : '');
    const departureUTC = accEnd || (itemMatches[0] ? itemMatches[0][4] : '');
    
    const startDate = isoToDate_(arrivalUTC);
    const endDate   = isoToDate_(departureUTC);
    
    // Date values for filtering (stored as actual date objects)
    const arrivalDateValue = isoToDateValue_(arrivalUTC);
    const departureDateValue = isoToDateValue_(departureUTC);

    // Extract custom field values from additionalFieldValues
    // Field id=30: Heure d'arrivée
    // Field id=31: Heure de départ
    // Capture value up to ", source=" to handle values that may contain commas
    const heureArrivee = extractOne_(block, /field=\{id=30,\s*name=Heure d'arrivée\},\s*value=(.*?)(?=,\s*source=)/);
    const heureDepart = extractOne_(block, /field=\{id=31,\s*name=Heure de départ\s*\},\s*value=(.*?)(?=,\s*source=)/);
    const guestAdditional = extractAdditionalFields_(extractOne_(block, /additionalFieldValues=([\s\S]*?)(?:\}, numberOfInvoices=|$)/));

    const remaining = Math.max(openBalance, totalAct - paid, 0);

    rows.push({
      key: `${bookingId}:${guestId}:${eventDateLbl}`, // Use BookingID + GuestID + EventDateLabel as unique key
      bookingId,
      guestId,
      guestName,
      age,
      gender,
      eventId,
      eventName,
      eventDateLbl,
      status: status || bookingStatus || '',
      bookingStatus,
      attendance,
      priceLevel,
      arrivalUTC,
      departureUTC,
      arrivalDate: startDate,
      departureDate: endDate,
      arrivalDateValue,
      departureDateValue,
      nights,
      lodgingText,
      lodgingPrice,
      mealsText,
      mealsPrice,
      eventFee,
      miscTotal,
      totalCalculated: totalCalc,
      totalActual: totalAct,
      paid,
      remaining,
      openBalance,
      bookerName,
      changedAt,
      confirmationDate,
      externalRem,
      internalRem,
      onlinePaymentStatus: onlinePayStat === 'null' ? '' : onlinePayStat,
      bookingAdditional,
      guestAdditional,
      heureArrivee: heureArrivee || '',
      heureDepart: heureDepart || ''
    });
  });

  return rows;
}

/***** MAIN FLATTEN - OPTIMIZED TO PROCESS ONLY NEW ROWS *****/
function updateFlattened() {
  const ss = SpreadsheetApp.getActive();
  const raw = ss.getSheetByName(RAW_SHEET_NAME);
  if (!raw) throw new Error('Sheet SD not found');
  let flat = ss.getSheetByName(FLAT_SHEET_NAME);
  if (!flat) flat = ss.insertSheet(FLAT_SHEET_NAME);

  // Ensure SD sheet has "Processed" column (column E)
  const rawHeader = raw.getRange(1, 1, 1, 5).getValues()[0];
  if (!rawHeader[4] || rawHeader[4] !== 'Processed') {
    raw.getRange(1, 5).setValue('Processed');
  }

  const rawValues = raw.getDataRange().getValues();
  if (rawValues.length < 2) {
    logRun_('INFO', 'No raw rows to process', '');
    return;
  }

  // Header - added date value columns for filtering
  const header = [
    'Key','BookingId','GuestId','GuestName','Age','Gender',
    'EventId','EventName','EventDateLabel','Status','BookingStatus','AttendanceType','PriceLevel',
    'ArrivalUTC','DepartureUTC','ArrivalDate','DepartureDate',
    'ArrivalDateValue','DepartureDateValue','Nights',
    'LodgingText','LodgingPrice','MealsText','MealsPrice','EventFee','MiscTotal',
    'TotalCalculated','TotalActual','Paid','Remaining','OpenBalance',
    'BookerName','ChangedAt','ConfirmationDate','ExternalRemarks','InternalRemarks',
    'OnlinePaymentStatus','BookingAdditional','GuestAdditional','HeureArrivee','HeureDepart'
  ];
  if (flat.getLastRow() === 0) {
    flat.getRange(1,1,1,header.length).setValues([header]);
    // Format date value columns as dates
    flat.getRange(1,17,1,2).setNumberFormat('dd/MM/yyyy');
  }

  // Build map of existing keys in Flattened sheet with their changedAt timestamps and source row numbers
  const keyCol = 1;
  const changedAtCol = 32; // Column AF (0-based index 31, but we need 1-based)
  const existing = flat.getDataRange().getValues();
  const keyToRow = {};
  const keyToMetadata = {}; // Track {changedAtTime, sourceRowNum} for each key
  for (let i=1; i<existing.length; i++) {
    const k = existing[i][keyCol-1];
    if (k) {
      keyToRow[k] = i+1;
      // Store changedAt timestamp and source row number for comparison
      const changedAtStr = existing[i][changedAtCol-1] || '';
      let changedAtTime = 0;
      if (changedAtStr) {
        try {
          const changedAtDate = new Date(changedAtStr);
          if (!isNaN(changedAtDate.getTime())) {
            changedAtTime = changedAtDate.getTime();
          }
        } catch (e) {
          // If parsing fails, treat as 0 (oldest)
        }
      }
      // Store metadata: timestamp and a placeholder source row (we'll use a high number for existing rows)
      // This ensures new rows from raw data will have higher source row numbers
      keyToMetadata[k] = {
        changedAtTime: changedAtTime,
        sourceRowNum: 999999 // High number so new rows from raw data will be considered newer
      };
    }
  }

  let nextRow = flat.getLastRow() + 1;
  let processed = 0, fails = 0, skipped = 0;
  const rowsToMarkProcessed = [];

  // Only process rows where column E (index 4) is empty or not "PROCESSED"
  for (let r=1; r<rawValues.length; r++) {
    const processedFlag = rawValues[r][4]; // Column E (0-based index 4)
    
    // Skip if already processed
    if (processedFlag === 'PROCESSED') {
      skipped++;
      continue;
    }

    const payloadStr = rawValues[r][3]; // col D (0-based index 3)
    const rawRowNumber = r + 1; // 1-based row number in raw sheet (for tiebreaker)
    const rows = parsePayloadToGuestRows_(payloadStr);
    if (!rows || rows.length === 0) { 
      fails++;
      rowsToMarkProcessed.push(r + 1); // Mark as processed even if parse failed
      continue; 
    }

    rows.forEach(obj => {
      // Parse changedAt timestamp for comparison
      let newChangedAtTime = 0;
      if (obj.changedAt) {
        try {
          const changedAtDate = new Date(obj.changedAt);
          if (!isNaN(changedAtDate.getTime())) {
            newChangedAtTime = changedAtDate.getTime();
          }
        } catch (e) {
          // If parsing fails, treat as 0 (oldest)
        }
      }
      
      // Check if this key already exists and if new version is more recent
      const existingMetadata = keyToMetadata[obj.key];
      if (keyToRow[obj.key] && existingMetadata) {
        const existingChangedAtTime = existingMetadata.changedAtTime || 0;
        
        // Compare timestamps
        if (newChangedAtTime < existingChangedAtTime) {
          // Existing row has newer timestamp, skip this one
          skipped++;
          return;
        }
        // If timestamps are equal or new is newer, we'll update
        // (When equal, prefer the new row since we're processing raw rows in order - later rows are newer)
      }
      
      const rowArr = [
        obj.key,
        obj.bookingId,
        obj.guestId,
        obj.guestName,
        obj.age,
        obj.gender,
        obj.eventId,
        obj.eventName,
        obj.eventDateLbl,
        obj.status,
        obj.bookingStatus,
        obj.attendance,
        obj.priceLevel,
        obj.arrivalUTC,
        obj.departureUTC,
        obj.arrivalDate,
        obj.departureDate,
        obj.arrivalDateValue,
        obj.departureDateValue,
        obj.nights,
        obj.lodgingText,
        obj.lodgingPrice,
        obj.mealsText,
        obj.mealsPrice,
        obj.eventFee,
        obj.miscTotal,
        obj.totalCalculated,
        obj.totalActual,
        obj.paid,
        obj.remaining,
        obj.openBalance,
        obj.bookerName,
        obj.changedAt,
        obj.confirmationDate,
        obj.externalRemarks,
        obj.internalRemarks,
        obj.onlinePaymentStatus,
        obj.bookingAdditional,
        obj.guestAdditional,
        obj.heureArrivee,
        obj.heureDepart
      ];
      if (keyToRow[obj.key]) {
        // Update existing row (newer version)
        flat.getRange(keyToRow[obj.key], 1, 1, rowArr.length).setValues([rowArr]);
        keyToMetadata[obj.key] = {
          changedAtTime: newChangedAtTime,
          sourceRowNum: rawRowNumber
        };
      } else {
        // New row
        flat.getRange(nextRow, 1, 1, rowArr.length).setValues([rowArr]);
        keyToRow[obj.key] = nextRow;
        keyToMetadata[obj.key] = {
          changedAtTime: newChangedAtTime,
          sourceRowNum: rawRowNumber
        };
        nextRow++;
      }
      processed++;
    });

    // Mark this raw row as processed
    rowsToMarkProcessed.push(r + 1);
  }

  // Batch update processed flags
  if (rowsToMarkProcessed.length > 0) {
    const processedFlags = rowsToMarkProcessed.map(() => ['PROCESSED']);
    raw.getRange(rowsToMarkProcessed[0], 5, rowsToMarkProcessed.length, 1)
       .setValues(processedFlags);
  }

  // Format date value columns for new rows
  if (nextRow > 2) {
    const lastFormattedRow = existing.length > 1 ? existing.length : 1;
    if (nextRow > lastFormattedRow + 1) {
      flat.getRange(lastFormattedRow + 1, 17, nextRow - lastFormattedRow - 1, 2)
          .setNumberFormat('dd/MM/yyyy');
    }
  }

  flat.getRange('AP1').setValue(
    'Last Updated: ' + Utilities.formatDate(new Date(), TZ, 'MM/dd/yyyy HH:mm')
  );

  logRun_('INFO', 'updateFlattened finished', 
    `Processed: ${processed}, Parse fails: ${fails}, Skipped (already processed): ${skipped}, Flattened rows: ${flat.getLastRow()-1}`);
}

/***** OPTIONAL: Full reprocess (use if you need to rebuild everything) *****/
function updateFlattenedFull() {
  // Clear processed flags and Flattened sheet, then reprocess everything
  const ss = SpreadsheetApp.getActive();
  const raw = ss.getSheetByName(RAW_SHEET_NAME);
  const flat = ss.getSheetByName(FLAT_SHEET_NAME);
  
  // Clear processed flags
  if (raw && raw.getLastRow() > 1) {
    raw.getRange(2, 5, raw.getLastRow() - 1, 1).clearContent();
  }
  
  // Clear Flattened sheet but keep header
  if (flat && flat.getLastRow() > 1) {
    flat.getRange(2, 1, flat.getLastRow() - 1, flat.getLastColumn()).clearContent();
  }
  
  updateFlattened();
}

/***** HELPER: Create Volunteers View *****/
function createVolunteersView() {
  const ss = SpreadsheetApp.getActive();
  let volSheet = ss.getSheetByName('Volunteers');
  if (!volSheet) {
    volSheet = ss.insertSheet('Volunteers');
  }
  
  // Clear existing content
  volSheet.clear();
  
  // Use FILTER instead of QUERY for better date handling
  const formula = `=FILTER(Flattened!A:AO, 
    LOWER(Flattened!H)="bénévole", 
    Flattened!R>=TODAY())`;
  
  volSheet.getRange('A1').setFormula(formula);
  
  // Copy header
  const flatSheet = ss.getSheetByName(FLAT_SHEET_NAME);
  if (flatSheet) {
    const header = flatSheet.getRange(1, 1, 1, 41).getValues()[0];
    volSheet.getRange(1, 1, 1, header.length).setValues([header]);
  }
}

