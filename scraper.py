"""Scraping and data-gathering logic for UofT course/professor CLI."""

import re
import time

from bs4 import BeautifulSoup

from utils import (
    safe_request,
    is_year_course,
    normalize_prof_name,
    base_code,
    TIMETABLE_FALL_URL,
    CALENDAR_SEARCH_URL,
    RMP_GRAPHQL_URL,
    RMP_AUTH_TOKEN,
    RMP_SCHOOL_ID,
    ALL_PREFIXES,
)

# Module-level cache for professor ratings
_rating_cache = {}

# Hardcoded fallback data for when scraping fails
FALLBACK_COURSES = {
    1: [
        # Fall
        {"code": "APS100H1F", "title": "Orientation to Engineering", "professor": "TBA", "year": 1},
        {"code": "APS110H1F", "title": "Engineering Chemistry and Materials Science", "professor": "TBA", "year": 1},
        {"code": "APS111H1F", "title": "Engineering Strategies & Practice I", "professor": "TBA", "year": 1},
        {"code": "CIV100H1F", "title": "Mechanics", "professor": "TBA", "year": 1},
        {"code": "MAT186H1F", "title": "Calculus I", "professor": "TBA", "year": 1},
        {"code": "MAT188H1F", "title": "Linear Algebra", "professor": "TBA", "year": 1},
        # Winter
        {"code": "APS105H1S", "title": "Computer Fundamentals", "professor": "TBA", "year": 1},
        {"code": "APS112H1S", "title": "Engineering Strategies & Practice II", "professor": "TBA", "year": 1},
        {"code": "ECE191H1S", "title": "Introduction to Electrical and Computer Engineering", "professor": "TBA", "year": 1},
        {"code": "ECE110H1S", "title": "Electrical Fundamentals", "professor": "TBA", "year": 1},
        {"code": "MAT187H1S", "title": "Calculus II", "professor": "TBA", "year": 1},
        {"code": "MIE100H1S", "title": "Dynamics", "professor": "TBA", "year": 1},
    ],
    2: [
        # Fall
        {"code": "ECE201H1F", "title": "Electrical and Computer Engineering Seminar", "professor": "TBA", "year": 2},
        {"code": "ECE231H1F", "title": "Introductory Electronics", "professor": "TBA", "year": 2},
        {"code": "ECE241H1F", "title": "Digital Systems", "professor": "TBA", "year": 2},
        {"code": "ECE244H1F", "title": "Programming Fundamentals", "professor": "TBA", "year": 2},
        {"code": "MAT290H1F", "title": "Advanced Engineering Mathematics", "professor": "TBA", "year": 2},
        {"code": "MAT291H1F", "title": "Introduction to Mathematical Physics", "professor": "TBA", "year": 2},
        # Winter
        {"code": "ECE212H1S", "title": "Circuit Analysis", "professor": "TBA", "year": 2},
        {"code": "ECE216H1S", "title": "Signals and Systems", "professor": "TBA", "year": 2},
        {"code": "ECE221H1S", "title": "Electric and Magnetic Fields", "professor": "TBA", "year": 2},
        {"code": "ECE243H1S", "title": "Computer Organization", "professor": "TBA", "year": 2},
        {"code": "ECE297H1S", "title": "Software Design and Communication", "professor": "TBA", "year": 2},
    ],
}


def scrape_timetable(year: int) -> list[dict]:
    """Scrape the UofT engineering timetable for courses in the given year."""
    try:
        resp = safe_request(TIMETABLE_FALL_URL)
        if resp is None:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        tables = soup.find_all("table")

        courses = []
        seen = set()

        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 8:
                    continue

                code = cells[0].get_text(strip=True).upper()
                section = cells[1].get_text(strip=True).upper()
                professor = cells[7].get_text(strip=True)

                if "LEC" not in section:
                    continue

                if not is_year_course(code, year):
                    continue

                key = (code, professor)
                if key in seen:
                    continue
                seen.add(key)

                courses.append({
                    "code": code,
                    "title": "",
                    "professor": professor,
                    "year": year,
                })

        return courses

    except Exception as e:
        print(f"  Warning: Failed to scrape timetable: {e}")
        return []


def scrape_course_titles() -> dict[str, str]:
    """Scrape the UofT engineering calendar for course titles."""
    titles = {}

    for prefix in ALL_PREFIXES:
        try:
            url = f"{CALENDAR_SEARCH_URL}?search_api_views_fulltext={prefix}"
            resp = safe_request(url)
            if resp is None:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # Look for course listings in headings and links
            for element in soup.find_all(["h3", "h4", "a", "span"]):
                text = element.get_text(strip=True)
                # Match patterns like "APS105H1 - Computer Fundamentals" or
                # "APS105H1: Computer Fundamentals"
                match = re.match(
                    r'([A-Z]{2,3}\d{3}[HY]\d)\s*[-:]\s*(.+)', text
                )
                if match:
                    code = match.group(1)
                    title = match.group(2).strip()
                    titles[code] = title

        except Exception as e:
            print(f"  Warning: Failed to scrape titles for {prefix}: {e}")
            continue

    return titles


def get_professor_rating(first_name: str, last_name: str) -> dict | None:
    """Look up a professor's rating on RateMyProfessors."""
    cache_key = f"{first_name} {last_name}".lower()

    if cache_key in _rating_cache:
        return _rating_cache[cache_key]

    query = """
query TeacherSearchQuery($text: String!, $schoolID: ID!) {
    newSearch {
        teachers(query: {text: $text, schoolID: $schoolID}, first: 1) {
            edges {
                node {
                    firstName
                    lastName
                    avgRating
                    avgDifficulty
                    numRatings
                }
            }
        }
    }
}
"""

    variables = {
        "text": f"{first_name} {last_name}",
        "schoolID": RMP_SCHOOL_ID,
    }

    try:
        resp = safe_request(
            RMP_GRAPHQL_URL,
            method="POST",
            headers={"Authorization": f"Basic {RMP_AUTH_TOKEN}"},
            json_data={"query": query, "variables": variables},
        )

        if resp is None:
            _rating_cache[cache_key] = None
            return None

        data = resp.json()
        edges = data["data"]["newSearch"]["teachers"]["edges"]

        if not edges:
            _rating_cache[cache_key] = None
            return None

        node = edges[0]["node"]

        # Validate last name to avoid false positives
        if node["lastName"].lower() != last_name.lower():
            _rating_cache[cache_key] = None
            return None

        result = {
            "rating": float(node["avgRating"]),
            "difficulty": float(node["avgDifficulty"]),
            "num_ratings": int(node["numRatings"]),
        }

        _rating_cache[cache_key] = result
        return result

    except Exception as e:
        print(f"  Warning: RMP lookup failed for {first_name} {last_name}: {e}")
        _rating_cache[cache_key] = None
        return None

    finally:
        time.sleep(0.5)


def get_all_data(year: int) -> tuple[list[dict], list[dict]]:
    """Gather all course and professor data for the given year.

    Returns (matched, unmatched) where matched courses have ratings
    and unmatched courses do not.
    """
    # Step 1: Get course list
    print(f"Scraping timetable for year {year} courses...")
    courses = scrape_timetable(year)

    if not courses:
        print("  Timetable scrape returned no results, using fallback data.")
        courses = FALLBACK_COURSES.get(year, [])

    # Step 2: Get course titles and merge them in
    print("Scraping course titles from calendar...")
    titles = scrape_course_titles()

    for course in courses:
        bc = base_code(course["code"])
        if bc in titles and not course["title"]:
            course["title"] = titles[bc]

    # Step 3: Look up professor ratings
    print("Looking up professor ratings on RateMyProfessors...")
    matched = []
    unmatched = []

    for course in courses:
        prof_pairs = normalize_prof_name(course["professor"])

        if not prof_pairs:
            # No valid professor name
            unmatched.append({
                "code": course["code"],
                "title": course["title"],
                "year": course["year"],
                "professor": course["professor"],
                "rating": None,
                "difficulty": None,
                "num_ratings": None,
            })
            continue

        # Use the first professor listed
        first_name, last_name = prof_pairs[0]
        print(f"  Looking up professor: {first_name} {last_name}...")

        rating_data = get_professor_rating(first_name, last_name)

        entry = {
            "code": course["code"],
            "title": course["title"],
            "year": course["year"],
            "professor": f"{first_name} {last_name}",
            "rating": rating_data["rating"] if rating_data else None,
            "difficulty": rating_data["difficulty"] if rating_data else None,
            "num_ratings": rating_data["num_ratings"] if rating_data else None,
        }

        if rating_data:
            matched.append(entry)
        else:
            unmatched.append(entry)

    print(f"Done: {len(matched)} matched, {len(unmatched)} unmatched.")
    return matched, unmatched
