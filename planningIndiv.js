// This script updates each person's individual "planning"
function generateChronologicalTaskList() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sourceSheet = ss.getSheetByName("PLANNING");
  const vipassanaSheet = ss.getSheetByName("VIPASSANA");
  const targetSheet = ss.getSheetByName("Plannings Individuels") || ss.insertSheet("Plannings Individuels");
  targetSheet.clear();

  // Force time zone to Paris
  const TIMEZONE = "Europe/Paris";
  const WEEKDAYS_FR = ['dim', 'lun', 'mar', 'mer', 'jeu', 'ven', 'sam'];

  // Date range for VIPASSANA tasks: Dec 27 - Jan 6
  const VIPASSANA_START = new Date('2025-12-27');
  const VIPASSANA_END = new Date('2026-01-06');

  // 🚫 Rows to skip when processing tasks
  // You can specify rows to skip by:
  // - Row number in the sheet (e.g., 10, 15, 20) - note: row 1 is header, data starts at row 6
  // - Text from Column A (e.g., "Task Name", "Some Text")
  // Mix and match as needed!
  const ROWS_TO_SKIP = [
    // Examples (uncomment and modify as needed):
    // 10,                    // Skip row 10 in the sheet
    // 15,                    // Skip row 15 in the sheet
      "RECEPTION",           // Skip row where Column A contains "RECEPTION"
    // "Some Text",           // Skip row where Column A contains "Some Text"
  ];

  // 📅 Date cutoff for displaying tasks
  // Options:
  // - null or undefined: Show all future dates (no cutoff)
  // - Number (e.g., 4): Show only the next N weeks from today
  // - Date string in dd/mm/yyyy format (e.g., "15/03/2026"): Show only dates through this date
  const DATE_CUTOFF = null; // Example: 4 for next 4 weeks, or "15/03/2026" for through March 15, 2026

  const dataRange = sourceSheet.getDataRange().getValues();
  const rawDates = dataRange[1].slice(3); // Row 2, columns D → ZZ
  const taskData = dataRange.slice(5);    // From Row 6 onward

  // Load VIPASSANA sheet data if it exists
  let vipassanaData = null;
  if (vipassanaSheet) {
    vipassanaData = vipassanaSheet.getDataRange().getValues();
  }

  // Helper function to process task name with A&B combination logic
  const processTaskName = (colA, colB, refTask) => {
    colA = (colA || "").toString();
    colB = (colB || "").toString();
    refTask = (refTask || "").toString().trim();

    const hasAide = colA.toUpperCase().includes("AIDE") || colB.toUpperCase().includes("AIDE");
    const hasLineBreak = colA.includes('\n') || colB.includes('\n');

    if (hasAide) {
      const target = colB || colA;
      if (target.includes('\n')) {
        const parts = target.split('\n').map(p => p.trim()).filter(Boolean);
        const secondLine = parts[1] || "";
        return `AIDE ${secondLine} ${refTask}`.trim();
      } else {
        return `AIDE ${refTask}`.trim();
      }
    } else if (hasLineBreak) {
      const target = colB || colA;
      const parts = target.split('\n').map(p => p.trim()).filter(Boolean);
      return parts.join(' ');
    } else {
      return colB || colA;
    }
  };

  // Helper function to get task name from PLANNING sheet
  const getPlanningTaskName = (rowIndex) => {
    const row = taskData[rowIndex];
    const above = rowIndex > 0 ? taskData[rowIndex - 1] : ["", ""];
    const colA = row[0];
    const colB = row[1];
    const refTask = (above[1] || above[0] || "").toString().trim();
    return processTaskName(colA, colB, refTask);
  };

  // Helper function to get task name from VIPASSANA sheet
  const getVipassanaTaskName = (rowIndex) => {
    if (!vipassanaData || vipassanaData.length <= rowIndex + 5) {
      return "";
    }
    const row = vipassanaData[rowIndex + 5];
    const above = rowIndex > 0 && vipassanaData.length > rowIndex + 4 ? vipassanaData[rowIndex + 4] : ["", ""];
    const colA = row[0];
    const colB = row[1];
    const refTask = (above[1] || above[0] || "").toString().trim();
    return processTaskName(colA, colB, refTask);
  };

  // Helper function to get task name based on row and date
  const getTaskName = (rowIndex, date) => {
    // Check if date falls within VIPASSANA range
    const useVipassana = date instanceof Date && 
                         date >= VIPASSANA_START && 
                         date <= VIPASSANA_END;

    if (useVipassana) {
      const vipassanaTask = getVipassanaTaskName(rowIndex);
      if (vipassanaTask) {
        return vipassanaTask;
      }
    }

    // Use PLANNING task name (either because VIPASSANA not in range, or VIPASSANA is empty)
    return getPlanningTaskName(rowIndex);
  };

  // Keep tasks array for backward compatibility (but we'll override per date)
  const tasks = taskData.map((row, i) => {
    const above = i > 0 ? taskData[i - 1] : ["", ""];
    const colA = (row[0] || "").toString();
    const colB = (row[1] || "").toString();
    const refTask = (above[1] || above[0] || "").toString().trim();

    const hasAide = colA.toUpperCase().includes("AIDE") || colB.toUpperCase().includes("AIDE");
    const hasLineBreak = colA.includes('\n') || colB.includes('\n');

    if (hasAide) {
      const target = colB || colA;
      if (target.includes('\n')) {
        const parts = target.split('\n').map(p => p.trim()).filter(Boolean);
        const secondLine = parts[1] || "";
        return `AIDE ${secondLine} ${refTask}`.trim();
      } else {
        return `AIDE ${refTask}`.trim();
      }
    } else if (hasLineBreak) {
      const target = colB || colA;
      const parts = target.split('\n').map(p => p.trim()).filter(Boolean);
      return parts.join(' ');
    } else {
      return colB || colA;
    }
  });

  const assignments = taskData.map(row => row.slice(3));
  const taskMap = new Map();             // key -> array of "date - task"
  const displayNameByKey = new Map();    // key -> DISPLAY NAME (ALL CAPS)

  const formatDate = dateValue => {
    if (!(dateValue instanceof Date)) return ""; // safer: never return garbage text
    const day = Utilities.formatDate(dateValue, TIMEZONE, "dd");
    const month = Utilities.formatDate(dateValue, TIMEZONE, "MM");
    const weekdayIdx = Number(Utilities.formatDate(dateValue, TIMEZONE, "u")) % 7;
    const weekday = WEEKDAYS_FR[weekdayIdx];
    return `${weekday} ${day}/${month}`;
  };

  // uniqueness key: accent- and case-insensitive, collapsed spaces
  const normalizeKey = name =>
    name
      .trim()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")      // strip accents
      .toLocaleLowerCase("fr")              // case-insensitive
      .replace(/\s+/g, " ");                // collapse internal whitespace

  // display for column A: ALL CAPS (accents preserved), collapsed spaces
  const displayCaps = name =>
    name
      .trim()
      .replace(/\s+/g, " ")
      .toLocaleUpperCase("fr");

  const splitNamesPreservingParens = str => {
    const result = [];
    let current = "";
    let inParens = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str[i];
      if (char === "(") inParens++;
      if (char === ")") inParens--;
      if (inParens === 0 && /[,\n/&+]/.test(char)) {
        if (current.trim()) result.push(current.trim());
        current = "";
      } else {
        current += char;
      }
    }
    if (current.trim()) result.push(current.trim());
    return result;
  };

  for (let r = 0; r < assignments.length; r++) {
    const colA = (dataRange[r + 5][0] || "").toString().trim();
    const colB = (dataRange[r + 5][1] || "").toString().trim();
    if (!colA && !colB) continue;

    // Check if this row should be skipped
    const sheetRowNumber = r + 6; // taskData starts at row 6, r is 0-based
    let shouldSkipCustom = false;
    
    if (ROWS_TO_SKIP.length > 0) {
      for (const skipItem of ROWS_TO_SKIP) {
        if (typeof skipItem === 'number') {
          // Row number match
          if (skipItem === sheetRowNumber) {
            shouldSkipCustom = true;
            break;
          }
        } else if (typeof skipItem === 'string') {
          // Column A text match (case-insensitive)
          const colAText = (taskData[r][0] || "").toString().trim();
          if (colAText.toUpperCase().includes(skipItem.toUpperCase().trim())) {
            shouldSkipCustom = true;
            break;
          }
        }
      }
    }

    const skipRow = (!taskData[r][0] && !taskData[r][1]) ||
                    (taskData[r][0] || "").toUpperCase().includes("SUR PLACE") ||
                    (taskData[r][1] || "").toUpperCase().includes("SUR PLACE") ||
                    (taskData[r][0] || "").toUpperCase().includes("INFO") ||
                    (taskData[r][1] || "").toUpperCase().includes("INFO") ||
                    shouldSkipCustom;
    if (skipRow) continue;

    for (let c = 0; c < assignments[r].length; c++) {
      const cellValue = (assignments[r][c] || "").toString().trim();
      if (!cellValue) continue;

      const entries = splitNamesPreservingParens(cellValue);
      entries.forEach(nameRaw => {
        const nameParts = nameRaw.trim().match(/^([^\(]+)(\s*\(.*\))?$/);
        if (!nameParts) return;

        const rawName = nameParts[1].trim();
        const key = normalizeKey(rawName);
        if (!key || ["x", "-", "ferme"].includes(key)) return;

        const suffix = nameParts[2] ? nameParts[2].trim() : "";
        const d = rawDates[c];

        if (!(d instanceof Date)) {
          Logger.log(`Skipping: no valid date for column ${c + 4} (row ${r + 6}), name "${rawName}", task "${tasks[r]}"`);
          return; // skip this entry; prevents bad "date - task" lines
        }

        // Filter: only include dates from today onward (in Paris timezone)
        const todayStr = Utilities.formatDate(new Date(), TIMEZONE, "yyyy-MM-dd");
        const dateStr = Utilities.formatDate(d, TIMEZONE, "yyyy-MM-dd");
        if (dateStr < todayStr) {
          return; // skip past dates
        }

        // Filter: apply date cutoff if configured
        if (DATE_CUTOFF !== null && DATE_CUTOFF !== undefined) {
          let cutoffDate = null;
          
          if (typeof DATE_CUTOFF === 'number') {
            // Number of weeks from today
            cutoffDate = new Date();
            cutoffDate.setDate(cutoffDate.getDate() + (DATE_CUTOFF * 7));
            cutoffDate.setHours(23, 59, 59, 999); // End of the cutoff day
          } else if (typeof DATE_CUTOFF === 'string') {
            // Date string - primary format: dd/mm/yyyy
            const dateStr = DATE_CUTOFF.trim();
            if (dateStr.match(/^\d{1,2}\/\d{1,2}\/\d{4}$/)) {
              // Format: "15/03/2026" (dd/mm/yyyy)
              const parts = dateStr.split('/');
              cutoffDate = new Date(parseInt(parts[2]), parseInt(parts[1]) - 1, parseInt(parts[0]));
            } else if (dateStr.match(/^\d{1,2}\/\d{1,2}\/\d{2}$/)) {
              // Format: "15/03/26" (dd/mm/yy)
              const parts = dateStr.split('/');
              const year = parseInt(parts[2]) + 2000;
              cutoffDate = new Date(year, parseInt(parts[1]) - 1, parseInt(parts[0]));
            } else if (dateStr.match(/^\d{4}-\d{2}-\d{2}$/)) {
              // Format: "2026-03-15" (yyyy-mm-dd) - fallback support
              const parts = dateStr.split('-');
              cutoffDate = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
            }
            
            if (cutoffDate) {
              cutoffDate.setHours(23, 59, 59, 999); // End of the cutoff day
            }
          }
          
          // Skip dates beyond the cutoff
          if (cutoffDate && d.getTime() > cutoffDate.getTime()) {
            return; // skip dates beyond cutoff
          }
        }

        if (!displayNameByKey.has(key)) displayNameByKey.set(key, displayCaps(rawName));

        // Get task name based on date (VIPASSANA for Dec 27 - Jan 6, otherwise PLANNING)
        const taskName = getTaskName(r, d);
        const formattedDate = formatDate(d);
        const fullTask = `${formattedDate} - ${taskName}${suffix ? ' ' + suffix : ''}`.replace(/\s+/g, ' ').trim();
        // Store both the formatted string and the original Date object for sorting
        const entry = { date: d, formattedDate: formattedDate, task: fullTask };
        (taskMap.has(key) ? taskMap.get(key) : taskMap.set(key, []).get(key)).push(entry);
      });
    }
  }

  const sortedOutput = [["PERSONNE", "TÂCHES"]];
  const sortedKeys = [...taskMap.keys()].sort((a, b) => a.localeCompare(b, 'fr'));

  sortedKeys.forEach(key => {
    const entries = taskMap.get(key);
    const display = displayNameByKey.get(key) || displayCaps(key);

    const dateTaskMap = new Map();

    entries.forEach(entry => {
      // entry is now an object with { date, formattedDate, task }
      if (!entry.date || !(entry.date instanceof Date)) {
        Logger.log(`Malformed entry (no valid date): "${entry.task}" for "${display}"`);
        return; // skip malformed
      }

      const formattedDate = entry.formattedDate;
      // Extract task part: entry.task is "formattedDate - taskName", so get everything after " - "
      const dashIndex = entry.task.indexOf(" - ");
      const task = dashIndex >= 0 ? entry.task.slice(dashIndex + 3) : entry.task;

      if (!dateTaskMap.has(formattedDate)) {
        dateTaskMap.set(formattedDate, { date: entry.date, tasks: [task] });
      } else {
        dateTaskMap.get(formattedDate).tasks.push(task);
      }
    });

    // Sort by the original Date objects (which include full year information)
    const sortedDates = Array.from(dateTaskMap.keys()).sort((a, b) => {
      const dateA = dateTaskMap.get(a).date;
      const dateB = dateTaskMap.get(b).date;
      return dateA.getTime() - dateB.getTime();
    });

    const lines = sortedDates.map(formattedDate => {
      const { tasks } = dateTaskMap.get(formattedDate);
      return `${formattedDate} - ${tasks.join("; ")}`;
    });
    sortedOutput.push([display, lines.join("\n")]);
  });

  targetSheet.getRange(1, 1, sortedOutput.length, 2).setValues(sortedOutput);

  // === FORMATTING ===
  targetSheet.setFrozenRows(1);
  const header = targetSheet.getRange("1:1");
  header.setFontWeight("bold").setHorizontalAlignment("center");

  const colA = targetSheet.getRange(2, 1, Math.max(0, targetSheet.getLastRow() - 1), 1);
  colA.setFontWeight("bold").setHorizontalAlignment("center").setVerticalAlignment("middle");
}