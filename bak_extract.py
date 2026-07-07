"""
bak_extract.py — Extract director-dashboard data from IVY SeminarDesk SQL backup.

Connects to local Docker SQL Server (restored .bak), queries Sept 2023+ bookings
with event series, room types, teachers, and financial fields. Outputs CSV for
aggregate.py to consume.

Requirements: pip install pyodbc pandas
"""

import os
import pandas as pd
import pyodbc

CONN_STR = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=localhost,1433;"
    "DATABASE=IvySD;"
    "UID=sa;"
    "PWD=IvyDash2026!;"
    "TrustServerCertificate=yes;"
)

CUTOFF_DATE = "2023-09-01"

EXTRACT_QUERY = """
SELECT
    bg.BuchungsGastID,
    bg.Von AS [from_date],
    bg.Bis AS [to_date],
    bg.SeminarName AS event_name,
    bg.SeminarTerminName AS event_instance,
    bg.SeminarID AS event_id,
    s.Kurzbezeichnung AS event_short,
    bg.LogisKategorie AS room_type_code,
    zt.Bezeichnung AS room_type_name,
    bg.AnzahlNächte AS nights,
    bg.AnzahlEssenstage AS meal_days,
    bg.AnzahlTeilnahme AS participant_days,
    bg.UmsatzSeminar AS revenue_attendance,
    bg.UmsatzLogis AS revenue_lodging,
    bg.UmsatzFB AS revenue_meals,
    bg.UmsatzSonstiges AS revenue_misc,
    (bg.UmsatzSeminar + bg.UmsatzLogis + bg.UmsatzFB + bg.UmsatzSonstiges) AS revenue_total,
    bg.ZahlungGesamt AS payment_total,
    (bg.UmsatzSeminar + bg.UmsatzLogis + bg.UmsatzFB + bg.UmsatzSonstiges - bg.ZahlungGesamt) AS balance,
    bg.Buchungsstatus AS status_code,
    CASE bg.Buchungsstatus
        WHEN 1 THEN 'Pending'
        WHEN 2 THEN 'Confirmed'
        WHEN 3 THEN 'Waitlist'
        WHEN 5 THEN 'Canceled'
        WHEN 6 THEN 'No-show'
        WHEN 7 THEN 'Waitlist-canceled'
        WHEN 8 THEN 'Deleted'
        ELSE 'Other'
    END AS status,
    CASE bg.AttendanceType
        WHEN 0 THEN 'on-site'
        WHEN 1 THEN 'online'
        WHEN 2 THEN 'guest-choice'
        ELSE 'unknown'
    END AS attendance_type,
    b.Buchungsquelle AS booking_source,
    b.OnlinePaymentStatus AS online_payment_status,
    b.BuchungsID AS booking_id,
    b.ConfirmationDate AS confirmation_date,
    teacher_agg.teachers AS teachers
FROM Buchungsgast bg
JOIN Buchung b ON bg.BuchungsID = b.BuchungsID
LEFT JOIN Seminar s ON bg.SeminarID = s.SeminarID
LEFT JOIN LU_Zimmertyp zt ON bg.LogisKategorie = zt.Code
LEFT JOIN (
    SELECT sl.SeminarID,
           STRING_AGG(ISNULL(p.Vorname,'') + ' ' + ISNULL(p.Nachname,''), '; ')
             WITHIN GROUP (ORDER BY sl.[Order]) AS teachers
    FROM Seminarleiter sl
    JOIN Person p ON sl.PersonID = p.PersonID
    GROUP BY sl.SeminarID
) teacher_agg ON bg.SeminarID = teacher_agg.SeminarID
WHERE bg.Von >= '{cutoff}'
ORDER BY bg.Von, bg.BuchungsGastID
""".format(cutoff=CUTOFF_DATE)


def extract():
    print(f"Connecting to SQL Server...")
    conn = pyodbc.connect(CONN_STR)
    print(f"Extracting bookings from {CUTOFF_DATE}...")
    df = pd.read_sql(EXTRACT_QUERY, conn)
    conn.close()

    print(f"Rows extracted: {len(df)}")
    print(f"Revenue total: €{df['revenue_total'].sum():,.0f}")
    print(f"Payment total: €{df['payment_total'].sum():,.0f}")
    print(f"Open balance: €{df['balance'].sum():,.0f}")

    out_path = os.path.join(os.path.dirname(__file__), "data", "bookings_extract.csv")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Written to {out_path}")
    return df


if __name__ == "__main__":
    extract()
