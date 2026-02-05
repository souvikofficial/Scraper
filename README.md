# 🧭 Universal Web Scraper

A Streamlit-based web scraper that supports auto-discovery, manual CSS selectors, pagination, Selenium rendering, and optional Tor routing.

## ✅ Features
- Auto-discover tables, lists, and cards without selectors
- Manual selector mode for precise extraction
- Pagination support (next button detection or custom selector)
- Optional Selenium rendering for JavaScript-heavy pages
- Optional Tor proxy for `.onion` targets
- Exports to CSV, XLSX, and JSON

## ⚙️ Requirements
- Python 3.10+
- Chrome (only required for Selenium mode)
- Tor (only required for `.onion` / Tor mode)

## 🚀 Quick Start
```powershell
cd "d:\Desktop\PROGRAMMING\Python Code\WebCrawler"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m streamlit run UI.py
```

## 📌 Usage
1. Enter the target URL.
2. Choose a mode: Auto-discover or Manual selectors.
3. If manual, provide field names and CSS selectors.
4. Configure pagination, Selenium, or Tor as needed.
5. Run the scraper and download your data.

## 🧪 Programmatic Use
```python
from scraper import scrape_site, save_data

data = scrape_site(
    "https://example.com/products",
    fields={"title": "h2.title", "price": ".price", "link": "a.card"},
    max_pages=3,
)

save_data(data, "scraped_data", formats=["csv", "json"])
```

## 📁 Output
By default, files are written to the project root:
- `scraped_data.csv`
- `scraped_data.xlsx`
- `scraped_data.json`

You can select which formats to export in the UI.

## 🧰 Troubleshooting
- `streamlit` not recognized: run `python -m streamlit run UI.py`.
- `ModuleNotFoundError: selenium`: install dependencies with `pip install -r requirements.txt`.
- Selenium errors: ensure Chrome is installed; Selenium will auto-download a compatible driver.
- Tor mode: Tor must be running locally at `127.0.0.1:9050`.

## 🔒 Legal and Ethics
Only scrape pages you are authorized to access. Respect site terms, rate limits, and `robots.txt`.

## 🗂️ Project Structure
- `UI.py` — Streamlit interface
- `scraper.py` — Scraping engine and helpers
- `requirements.txt` — Dependencies
