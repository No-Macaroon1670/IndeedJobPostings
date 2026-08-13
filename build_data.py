"""Build data.json for the Indeed Job Postings explorer.

Pulls the two national US files from Indeed Hiring Lab's public tracker repo and
flattens them into one compact JSON payload the web page can load in one request.

    python build_data.py

Source: https://github.com/hiring-lab/job_postings_tracker
Only sectors still present in the live file are included, so discontinued
series drop out automatically on the next run.
"""

import csv
import io
import json
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

RAW = "https://raw.githubusercontent.com/hiring-lab/job_postings_tracker/master/US"
AGGREGATE_URL = f"{RAW}/aggregate_job_postings_US.csv"
SECTOR_URL = f"{RAW}/job_postings_by_sector_US.csv"
OUT = Path(__file__).parent / "data.json"

# Indeed's 41 occupational sectors, bucketed for the picker's quick-select groups.
GROUPS = {
    "Tech & data": [
        "Software Development",
        "IT Infrastructure, Operations & Support",
        "IT Systems & Solutions",
        "Data & Analytics",
        "Scientific Research & Development",
    ],
    "Healthcare": [
        "Nursing",
        "Physicians & Surgeons",
        "Medical Technician",
        "Medical Information",
        "Pharmacy",
        "Personal Care & Home Health",
    ],
    "Business & professional": [
        "Accounting",
        "Banking & Finance",
        "Legal",
        "Human Resources",
        "Management",
        "Project Management",
        "Marketing",
        "Sales",
        "Administrative Assistance",
        "Media & Communications",
    ],
    "Engineering & construction": [
        "Architecture",
        "Civil Engineering",
        "Electrical Engineering",
        "Industrial Engineering",
        "Mechanical Engineering",
    ],
    "Goods & logistics": [
        "Production & Manufacturing",
        "Loading & Stocking",
        "Logistic Support",
        "Installation & Maintenance",
    ],
    "Consumer services": [
        "Retail",
        "Food Preparation & Service",
        "Hospitality & Tourism",
        "Customer Service",
        "Cleaning & Sanitation",
        "Security & Public Safety",
        "Arts & Entertainment",
    ],
    "Education & social": [
        "Education & Instruction",
        "Community & Social Service",
        "Social Science",
        "Childcare",
    ],
}

SHORT_NAMES = {
    "IT Infrastructure, Operations & Support": "IT Infrastructure & Ops",
    "Scientific Research & Development": "Scientific R&D",
    "Personal Care & Home Health": "Personal & Home Care",
    "Production & Manufacturing": "Manufacturing",
    "Food Preparation & Service": "Food Prep & Service",
    "Administrative Assistance": "Admin Assistance",
    "Community & Social Service": "Community & Social Svc",
    "Education & Instruction": "Education",
    "Security & Public Safety": "Security & Public Safety",
}

VARIABLE_KEY = {"total postings": "total", "new postings": "new"}


def fetch(url, attempts=3):
    """Download with a couple of retries — this runs unattended on a schedule."""
    print(f"  downloading {url.rsplit('/', 1)[-1]} ...")
    req = urllib.request.Request(url, headers={"User-Agent": "indeed-postings-explorer"})
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return resp.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError) as err:
            if attempt == attempts:
                raise
            wait = attempt * 10
            print(f"    attempt {attempt} failed ({err}); retrying in {wait}s")
            time.sleep(wait)


def slugify(name):
    out = []
    for ch in name.lower():
        out.append(ch if ch.isalnum() else "-")
    return "-".join(filter(None, "".join(out).split("-")))


def num(text):
    text = text.strip()
    if not text:
        return None
    return round(float(text), 2)


def main():
    print("Fetching Indeed Hiring Lab data...")
    agg_rows = list(csv.DictReader(io.StringIO(fetch(AGGREGATE_URL))))
    sector_rows = list(csv.DictReader(io.StringIO(fetch(SECTOR_URL))))

    # date -> variable -> value, for the national aggregate (seasonally adjusted column)
    national = defaultdict(dict)
    for row in agg_rows:
        key = VARIABLE_KEY.get(row["variable"])
        if key:
            national[row["date"]][key] = num(row["indeed_job_postings_index_SA"])

    # sector -> date -> variable -> value
    sectors = defaultdict(lambda: defaultdict(dict))
    for row in sector_rows:
        key = VARIABLE_KEY.get(row["variable"])
        if key:
            sectors[row["display_name"]][row["date"]][key] = num(row["indeed_job_postings_index"])

    dates = sorted(national)
    print(f"  {len(dates)} daily observations, {dates[0]} -> {dates[-1]}")

    group_of = {name: group for group, names in GROUPS.items() for name in names}
    unknown = sorted(set(sectors) - set(group_of))
    if unknown:
        print(f"  NOTE: sectors missing from GROUPS (filed under 'Other'): {unknown}")
    missing = sorted(set(group_of) - set(sectors))
    if missing:
        print(f"  NOTE: grouped sectors absent from the live file (discontinued?): {missing}")

    def pack(by_date):
        return {
            "total": [by_date.get(d, {}).get("total") for d in dates],
            "new": [by_date.get(d, {}).get("new") for d in dates],
        }

    series = [
        {
            "id": "national",
            "name": "National (all sectors)",
            "group": "Overall",
            "short": "National",
            **pack(national),
        }
    ]
    for name in sorted(sectors):
        series.append(
            {
                "id": slugify(name),
                "name": name,
                "group": group_of.get(name, "Other"),
                "short": SHORT_NAMES.get(name, name),
                **pack(sectors[name]),
            }
        )

    payload = {
        "generated": date.today().isoformat(),
        "baseline": "2020-02-01",
        "source": "Indeed Hiring Lab — Job Postings Index",
        "sourceUrl": "https://github.com/hiring-lab/job_postings_tracker",
        "groups": ["Overall"] + list(GROUPS),
        "dates": dates,
        "series": series,
    }

    # `generated` changes on every run, so compare everything else — otherwise the
    # scheduled rebuild would commit an identical file every day.
    if OUT.exists():
        try:
            old = json.loads(OUT.read_text(encoding="utf-8"))
            if {k: v for k, v in old.items() if k != "generated"} == \
               {k: v for k, v in payload.items() if k != "generated"}:
                print(f"No change since {old.get('generated', 'the last build')} - leaving {OUT.name} alone")
                return
        except (ValueError, OSError) as err:
            print(f"  (could not read existing {OUT.name}: {err}; rewriting)")

    OUT.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    size_mb = OUT.stat().st_size / 1024 / 1024
    print(f"Wrote {OUT} ({len(series)} series, {size_mb:.1f} MB, through {dates[-1]})")


if __name__ == "__main__":
    main()   # the workflow detects a change with `git diff`, not the exit code
