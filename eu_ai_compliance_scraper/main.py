import os
import sys
from eu_ai_compliance_scraper.scraper.form_navigator import scrape_compliance_checker
from eu_ai_compliance_scraper.parser.form_parser import parse_form_html
from eu_ai_compliance_scraper.utils.file_ops import save_html, save_json
from eu_ai_compliance_scraper import config


def main():
    record_mode = '--record' in sys.argv
    if record_mode:
        print("\n[RECORD MODE] Walk through the form in the browser. At each question, select your answer(s) as prompted. When the form ends, the run will be saved.\n")
    # Step 1: Scrape the compliance checker form (recorded or automated)
    html_data = scrape_compliance_checker(config.COMPLIANCE_CHECKER_URL, record_mode=record_mode)
    save_html(html_data, os.path.join(config.DATA_DIR, 'compliance_checker.html'))
    if not record_mode:
        # Step 2: Parse the HTML to extract form structure
        form_json = parse_form_html(html_data)
        save_json(form_json, os.path.join(config.DATA_DIR, 'compliance_checker.json'))
        print(f"Scraping and parsing complete. Output saved to {config.DATA_DIR}")
    else:
        print(f"Recording complete. Output saved to {config.DATA_DIR}")


if __name__ == "__main__":
    main() 