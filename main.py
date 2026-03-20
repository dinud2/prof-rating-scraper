#!/usr/bin/env python3
"""UofT Course & Professor CLI — scrape engineering course data and professor ratings."""

import argparse
import sys

from scraper import get_all_data
from exporter import export_to_excel


def main():
    parser = argparse.ArgumentParser(
        prog="uoft_course_prof_cli",
        description="Scrape UofT engineering course data and professor ratings into Excel.",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Scrape and export data")
    run_parser.add_argument(
        "--year", type=int, required=True, choices=[1, 2],
        help="Year level to scrape (1 or 2)",
    )
    run_parser.add_argument(
        "--output", type=str, default="courses.xlsx",
        help="Output Excel file path (default: courses.xlsx)",
    )

    args = parser.parse_args()

    if args.command != "run":
        parser.print_help()
        sys.exit(1)

    print(f"=== UofT Course & Professor CLI ===")
    print(f"Collecting year {args.year} engineering courses...\n")

    matched, unmatched = get_all_data(args.year)

    if not matched and not unmatched:
        print("No data found. Exiting.")
        sys.exit(1)

    export_to_excel(matched, unmatched, args.output)
    print(f"\nExported to {args.output}")
    print(f"  {len(matched)} courses with ratings")
    print(f"  {len(unmatched)} courses without ratings")


if __name__ == "__main__":
    main()
