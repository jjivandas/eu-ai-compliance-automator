# EU AI Compliance Automator

A modular tool for scraping, parsing, and automating compliance checks for the EU AI Act.

## Project Structure

```
eu-ai-compliance-automator/
├── eu_ai_compliance_scraper/   # Scraper and parser code
│   ├── main.py                # Entrypoint for scraping
│   ├── scraper/               # Playwright browser automation
│   ├── parser/                # BeautifulSoup HTML parsing
│   ├── utils/                 # File I/O, logging, helpers
│   └── config.py              # URLs, selectors, and settings
├── backend/                   # API and business logic (planned)
├── frontend/                  # Web UI (planned)
├── data/                      # Scraped HTML and parsed JSON output
├── requirements.txt           # Python dependencies
├── .env.example               # Example environment variables
├── .gitignore                 # Ignore venv, .env, node_modules, data
└── README.md                  # This file
```

## Quickstart

1. **Clone the repo and set up a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Copy and edit environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env as needed
   ```
3. **Run the scraper:**
   ```bash
   python -m eu_ai_compliance_scraper.main
   # Output will be saved in /data/
   ```
4. **Run tests:**
   ```bash
   pytest eu_ai_compliance_scraper/tests/
   ```

## How to Add New Scrapers
- Add new Playwright automation code under `eu_ai_compliance_scraper/scraper/`.
- Add new parsing logic under `eu_ai_compliance_scraper/parser/`.
- Use `eu_ai_compliance_scraper/utils/` for helpers and file I/O.
- Update `config.py` for new URLs or selectors.

## How to Extend
- Modular structure makes it easy to add new sites, forms, or parsing logic.
- Keep code readable, commented, and well-tested.

## Notes
- All data is saved in `/data/` at the repo root.
- Never commit secrets or real .env files.
- Use Playwright for browser automation, BeautifulSoup for parsing, and python-dotenv for config.