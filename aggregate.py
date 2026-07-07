"""
aggregate.py — Transform bookings extract into director dashboard JSON.

Reads data/bookings_extract.tsv, computes KPIs, event-series profitability,
season stats, room-type analytics, and teacher rankings. Outputs anonymized
JSON for the static dashboard.
"""

import json
import os
from collections import defaultdict
from datetime import datetime
import csv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(SCRIPT_DIR, "data", "bookings_extract.tsv")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "dashboard", "public", "data")


def fiscal_season(date_str):
    """Sept-Aug fiscal year. Returns start year (e.g. 2023 for Sept 2023 - Aug 2024)."""
    if not date_str:
        return None
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return d.year if d.month >= 9 else d.year - 1
    except (ValueError, TypeError):
        return None


def event_series(event_name):
    """Extract series code from event name (text after last ' - ')."""
    if not event_name:
        return "Unknown"
    s = event_name.strip()
    if " - " in s:
        return s.rsplit(" - ", 1)[-1].strip()
    return s


def director_bucket(series_code, event_name):
    """Classify into IDMT / Bénévole / Repas hors / Séjour personnel / Retreats."""
    if series_code == "IDMT" or "IDMT" in (event_name or ""):
        return "IDMT"
    if series_code == "Bénévole" or event_name == "Bénévole":
        return "Bénévole"
    if "Repas hors" in (event_name or ""):
        return "Repas hors activités"
    if series_code == "Séjour personnel":
        return "Séjour personnel"
    return "Retraites & événements"


def load_extract():
    rows = []
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            for key in ["revenue_attendance", "revenue_lodging", "revenue_meals",
                        "revenue_misc", "revenue_total", "payment_total", "balance"]:
                try:
                    row[key] = float(row.get(key) or 0)
                except (ValueError, TypeError):
                    row[key] = 0.0
            for key in ["nights", "meal_days", "participant_days"]:
                try:
                    row[key] = int(row.get(key) or 0)
                except (ValueError, TypeError):
                    row[key] = 0
            rows.append(row)
    return rows


def aggregate(rows):
    kpis = {
        "totalRows": len(rows),
        "totalRevenue": 0,
        "totalPayments": 0,
        "openBalance": 0,
        "confirmedCount": 0,
        "canceledCount": 0,
        "onlineCount": 0,
        "onsiteCount": 0,
    }

    by_series = defaultdict(lambda: {
        "rows": 0, "revenue_total": 0, "revenue_attendance": 0,
        "revenue_lodging": 0, "revenue_meals": 0, "revenue_misc": 0,
        "payment_total": 0, "balance": 0, "nights": 0,
        "confirmed": 0, "teachers": set()
    })
    by_bucket = defaultdict(lambda: {"rows": 0, "revenue_total": 0, "balance": 0})
    by_season = defaultdict(lambda: {
        "all": 0, "with_lodging": 0, "meals_only": 0,
        "revenue_total": 0, "balance": 0
    })
    by_room_type = defaultdict(lambda: {
        "bookings": 0, "revenue": 0, "nights": 0
    })
    by_teacher = defaultdict(lambda: {"events": set(), "rows": 0, "revenue": 0})
    by_status = defaultdict(int)
    by_month = defaultdict(lambda: {"rows": 0, "revenue": 0})

    for row in rows:
        rev = row["revenue_total"]
        pay = row["payment_total"]
        bal = row["balance"]
        status = row.get("status", "")
        att_type = row.get("attendance_type", "")

        kpis["totalRevenue"] += rev
        kpis["totalPayments"] += pay
        if bal > 0:
            kpis["openBalance"] += bal
        if status == "Confirmed":
            kpis["confirmedCount"] += 1
        elif status == "Canceled":
            kpis["canceledCount"] += 1
        if att_type == "online":
            kpis["onlineCount"] += 1
        elif att_type == "on-site":
            kpis["onsiteCount"] += 1

        by_status[status] += 1

        series = event_series(row.get("event_name"))
        bucket = director_bucket(series, row.get("event_name"))

        s = by_series[series]
        s["rows"] += 1
        s["revenue_total"] += rev
        s["revenue_attendance"] += row["revenue_attendance"]
        s["revenue_lodging"] += row["revenue_lodging"]
        s["revenue_meals"] += row["revenue_meals"]
        s["revenue_misc"] += row["revenue_misc"]
        s["payment_total"] += pay
        s["balance"] += bal
        s["nights"] += row["nights"]
        if status == "Confirmed":
            s["confirmed"] += 1
        teachers_str = row.get("teachers", "").strip()
        if teachers_str:
            s["teachers"].add(teachers_str)

        by_bucket[bucket]["rows"] += 1
        by_bucket[bucket]["revenue_total"] += rev
        by_bucket[bucket]["balance"] += bal

        fy = fiscal_season(row.get("from_date"))
        if fy:
            by_season[fy]["all"] += 1
            by_season[fy]["revenue_total"] += rev
            by_season[fy]["balance"] += bal
            if row["revenue_lodging"] > 0:
                by_season[fy]["with_lodging"] += 1
            elif row["revenue_meals"] > 0:
                by_season[fy]["meals_only"] += 1

        rt_code = row.get("room_type_code", "").strip()
        rt_name = row.get("room_type_name", "").strip()
        if rt_code and rt_code not in ("EXTERN", "ONLINE", "ONLINE."):
            by_room_type[rt_name or rt_code]["bookings"] += 1
            by_room_type[rt_name or rt_code]["revenue"] += row["revenue_lodging"]
            by_room_type[rt_name or rt_code]["nights"] += row["nights"]

        if teachers_str:
            for t in teachers_str.split("; "):
                t = t.strip()
                if t:
                    by_teacher[t]["rows"] += 1
                    by_teacher[t]["revenue"] += rev
                    by_teacher[t]["events"].add(series)

        from_date = row.get("from_date", "")
        if from_date and len(from_date) >= 7:
            by_month[from_date[:7]]["rows"] += 1
            by_month[from_date[:7]]["revenue"] += rev

    # Build output
    series_list = []
    for name, data in sorted(by_series.items(), key=lambda x: -x[1]["revenue_total"]):
        series_list.append({
            "series": name,
            "bucket": director_bucket(name, name),
            "rows": data["rows"],
            "confirmed": data["confirmed"],
            "revenue_total": round(data["revenue_total"], 2),
            "revenue_attendance": round(data["revenue_attendance"], 2),
            "revenue_lodging": round(data["revenue_lodging"], 2),
            "revenue_meals": round(data["revenue_meals"], 2),
            "revenue_misc": round(data["revenue_misc"], 2),
            "payment_total": round(data["payment_total"], 2),
            "balance": round(data["balance"], 2),
            "nights": data["nights"],
            "teachers": "; ".join(sorted(data["teachers"])) if data["teachers"] else "",
        })

    season_list = []
    for year in sorted(by_season.keys()):
        d = by_season[year]
        season_list.append({
            "season": f"{year}-{year+1}",
            "all": d["all"],
            "with_lodging": d["with_lodging"],
            "meals_only": d["meals_only"],
            "revenue_total": round(d["revenue_total"], 2),
            "balance": round(d["balance"], 2),
        })

    room_list = []
    for name, data in sorted(by_room_type.items(), key=lambda x: -x[1]["revenue"]):
        room_list.append({
            "room_type": name,
            "bookings": data["bookings"],
            "revenue": round(data["revenue"], 2),
            "nights": data["nights"],
            "rev_per_night": round(data["revenue"] / data["nights"], 2) if data["nights"] > 0 else 0,
        })

    teacher_list = []
    for name, data in sorted(by_teacher.items(), key=lambda x: -x[1]["revenue"]):
        teacher_list.append({
            "teacher": name,
            "rows": data["rows"],
            "revenue": round(data["revenue"], 2),
            "events": len(data["events"]),
        })

    month_list = []
    for ym in sorted(by_month.keys()):
        month_list.append({
            "month": ym,
            "rows": by_month[ym]["rows"],
            "revenue": round(by_month[ym]["revenue"], 2),
        })

    output = {
        "updatedAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataSource": "SeminarDesk backup 2026-07-07 (Sept 2023+)",
        "kpis": {k: round(v, 2) if isinstance(v, float) else v for k, v in kpis.items()},
        "byStatus": dict(by_status),
        "byBucket": {k: {kk: round(vv, 2) if isinstance(vv, float) else vv for kk, vv in v.items()} for k, v in by_bucket.items()},
        "byEventSeries": series_list,
        "bySeason": season_list,
        "byRoomType": room_list,
        "byTeacher": teacher_list[:20],
        "byMonth": month_list,
    }

    return output


def main():
    print(f"Loading {INPUT_PATH}...")
    rows = load_extract()
    print(f"Loaded {len(rows)} rows")

    print("Aggregating...")
    output = aggregate(rows)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    summary_path = os.path.join(OUTPUT_DIR, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Written {summary_path} ({os.path.getsize(summary_path) / 1024:.1f} KB)")

    print("\n=== KPIs ===")
    for k, v in output["kpis"].items():
        print(f"  {k}: {v}")
    print(f"\n  Event series: {len(output['byEventSeries'])}")
    print(f"  Seasons: {len(output['bySeason'])}")
    print(f"  Room types: {len(output['byRoomType'])}")
    print(f"  Teachers: {len(output['byTeacher'])}")


if __name__ == "__main__":
    main()
