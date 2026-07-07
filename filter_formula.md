# Filter Formula for Display Sheet (French Google Sheets)

## Basic Formula (All Date Ranges)

Place this in cell A1 of your "Display" sheet:

```
=FILTRE(Source!A:Z; 
  Source!B:B <> "omit"; 
  Source!C:C <> "omit";
  (Source!E:E >= DATE(2023;9;1)) * (Source!E:E <= DATE(2024;8;31)) + 
  (Source!E:E >= DATE(2024;9;1)) * (Source!E:E <= DATE(2025;8;31)) + 
  (Source!E:E >= DATE(2025;9;1)) * (Source!E:E <= DATE(2026;8;31))
)
```

## With Date Range Selector

If you want to select which date range to show, put the range number (1, 2, or 3) in cell Z1 of the Display sheet, then use:

```
=FILTRE(Source!A:Z; 
  Source!B:B <> "omit"; 
  Source!C:C <> "omit";
  SI(Z1=1; (Source!E:E >= DATE(2023;9;1)) * (Source!E:E <= DATE(2024;8;31));
  SI(Z1=2; (Source!E:E >= DATE(2024;9;1)) * (Source!E:E <= DATE(2025;8;31));
  SI(Z1=3; (Source!E:E >= DATE(2025;9;1)) * (Source!E:E <= DATE(2026;8;31));
  (Source!E:E >= DATE(2023;9;1)) * (Source!E:E <= DATE(2026;8;31)))))
)
```

## Alternative: Using Named Ranges

If you prefer, you can use a dropdown in Z1 with values 1, 2, 3, or "All", then:

```
=FILTRE(Source!A:Z; 
  Source!B:B <> "omit"; 
  Source!C:C <> "omit";
  SI(Z1="All"; 
    ((Source!E:E >= DATE(2023;9;1)) * (Source!E:E <= DATE(2024;8;31)) + 
     (Source!E:E >= DATE(2024;9;1)) * (Source!E:E <= DATE(2025;8;31)) + 
     (Source!E:E >= DATE(2025;9;1)) * (Source!E:E <= DATE(2026;8;31)));
  SI(Z1=1; (Source!E:E >= DATE(2023;9;1)) * (Source!E:E <= DATE(2024;8;31));
  SI(Z1=2; (Source!E:E >= DATE(2024;9;1)) * (Source!E:E <= DATE(2025;8;31));
  SI(Z1=3; (Source!E:E >= DATE(2025;9;1)) * (Source!E:E <= DATE(2026;8;31)); FAUX)))))
)
```

**Note:** 
- Replace "Source" with the actual name of your source sheet
- French Google Sheets use semicolons (;) instead of commas (,) as argument separators
- Function names: FILTRE (instead of FILTER), SI (instead of IF), DATE (same)
