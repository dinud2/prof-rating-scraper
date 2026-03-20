# UofT Course & Professor CLI

Scrapes University of Toronto first- and second-year engineering course data and professor ratings from RateMyProfessors, then exports to a formatted Excel file.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Scrape year 1 courses
python main.py run --year 1 --output year1.xlsx

# Scrape year 2 courses
python main.py run --year 2 --output year2.xlsx
```

## Output

The Excel file contains:
- **Courses** sheet: courses with professor ratings (Course Code, Course Title, Year, Professor Name, Professor Rating, Difficulty, Review Count)
- **Unmatched** sheet: courses where professor ratings were not found

## How it works

1. Scrapes course codes and professors from the UofT engineering timetable
2. Scrapes course titles from the engineering calendar
3. Looks up each professor on RateMyProfessors
4. Exports everything to a formatted Excel file

If live scraping fails, fallback data is used so the tool always produces output.
# prof-rating-scraper
