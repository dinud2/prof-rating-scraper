"""Constants and helper functions for UofT course scraper."""

import re
import time
import requests

# URLs
TIMETABLE_FALL_URL = "https://portal.engineering.utoronto.ca/sites/timetable/fall.html"
TIMETABLE_WINTER_URL = "https://portal.engineering.utoronto.ca/sites/timetable/winter.html"
CALENDAR_SEARCH_URL = "https://engineering.calendar.utoronto.ca/search-courses"

# RateMyProfessors
RMP_GRAPHQL_URL = "https://www.ratemyprofessors.com/graphql"
RMP_AUTH_TOKEN = "dGVzdDp0ZXN0"
RMP_SCHOOL_ID = "U2Nob29sLTE0ODQ="  # UofT St. George

# Course prefix ranges by year
YEAR1_PREFIXES = {
    "APS": (100, 199),
    "MAT": (186, 188),
    "CIV": (100, 109),
    "ECE": (110, 191),
    "MIE": (100, 109),
}

YEAR2_PREFIXES = {
    "ECE": (200, 299),
    "MAT": (290, 291),
}

# All relevant prefixes (union of year 1 and 2)
ALL_PREFIXES = sorted(set(list(YEAR1_PREFIXES.keys()) + list(YEAR2_PREFIXES.keys())))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}


def safe_request(url, method="GET", retries=3, headers=None, json_data=None, timeout=15):
    """Make an HTTP request with retries and exponential backoff."""
    hdrs = {**HEADERS, **(headers or {})}
    for attempt in range(retries):
        try:
            if method == "POST":
                resp = requests.post(url, headers=hdrs, json=json_data, timeout=timeout)
            else:
                resp = requests.get(url, headers=hdrs, timeout=timeout)
            resp.raise_for_status()
            return resp
        except (requests.RequestException, Exception) as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"  Warning: Request to {url} failed after {retries} attempts: {e}")
                return None


def is_year_course(course_code, year):
    """Check if a course code belongs to the specified year (1 or 2)."""
    match = re.match(r'^([A-Z]{2,3})(\d{3})', course_code.upper())
    if not match:
        return False
    prefix, number = match.group(1), int(match.group(2))
    prefixes = YEAR1_PREFIXES if year == 1 else YEAR2_PREFIXES
    if prefix in prefixes:
        low, high = prefixes[prefix]
        return low <= number <= high
    return False


def normalize_prof_name(raw_name):
    """Convert 'Last, First' to [('First', 'Last'), ...]. Handles TBA and multiple profs."""
    if not raw_name or raw_name.strip().upper() in ("TBA", "TBD", "STAFF", ""):
        return []
    results = []
    # Split on common separators for multiple professors
    for name in re.split(r'\s*/\s*|\s+and\s+', raw_name):
        name = name.strip()
        if not name or name.upper() in ("TBA", "TBD", "STAFF"):
            continue
        if "," in name:
            parts = name.split(",", 1)
            last = parts[0].strip()
            first = parts[1].strip()
        else:
            parts = name.split()
            if len(parts) >= 2:
                first = parts[0]
                last = parts[-1]
            else:
                first = name
                last = ""
        if first and last:
            results.append((first, last))
    return results


def base_code(course_code):
    """Strip term suffix to get base code. APS112H1F -> APS112H1"""
    match = re.match(r'^([A-Z]{2,3}\d{3}[HY]\d)', course_code.upper())
    return match.group(1) if match else course_code.upper()
