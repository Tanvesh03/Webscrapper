# Booking.com Web Scraper — MCP Edition

A production-ready Booking.com hotel data scraper with **MCP (Model Context Protocol)** integration,
designed for use with **Claude Code** and **VS Code**.

## Features

- Scrapes hotel **name, price, rating, reviews, stars, location, distance, breakfast**
- **MCP-compatible** tool interface (`search_hotels`, `get_hotel_info`)
- CLI and Python API support
- Polite scraping with configurable delays & user-agent rotation
- CAPTCHA detection with Selenium fallback guidance
- Exports to **CSV** and **JSON**

## Project Structure

```
Webscrapper/
├── scraper.py          # Main scraper + MCP interface
├── requirements.txt    # Python dependencies
├── .mcp.json           # MCP server configuration for Claude Code
└── README.md
```

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run from CLI

```bash
# Basic search
python scraper.py --city Dubai --checkin 2026-06-01 --checkout 2026-06-05

# More options
python scraper.py --city "New York" --adults 2 --rooms 1 --pages 3 --output ny_hotels.csv

# Also export JSON
python scraper.py --city Paris --json
```

### 3. Use as Python library

```python
from scraper import BookingMCPScraper

scraper = BookingMCPScraper()
df = scraper.scrape(
    city     = "Dubai",
    checkin  = "2026-06-01",
    checkout = "2026-06-05",
    adults   = 2,
    rooms    = 1,
    max_pages = 2,
)

print(df.head())
scraper.save_csv(df)
```

### 4. Use MCP tool interface (Claude Code)

```python
from scraper import BookingMCPScraper

scraper = BookingMCPScraper()
result  = scraper.call_tool("search_hotels", {
    "destination": "Dubai",
    "check_in":    "2026-06-01",
    "check_out":   "2026-06-05",
    "adults":      2,
    "pages":       2,
})

print(f"Found {result['count']} hotels")
```

## MCP Integration with VS Code + Claude Code

1. Install Claude Code extension in VS Code
2. The `.mcp.json` in this repo auto-configures the MCP server
3. Claude Code can call `search_hotels` and `get_hotel_info` tools directly

Example prompt for Claude Code:
```
Search for hotels in Dubai from June 1–5 2026 for 2 adults using the booking-scraper MCP tool
```

## CLI Reference

| Argument | Default | Description |
|---|---|---|
| `--city` | required | Destination city |
| `--checkin` | 30 days from now | Check-in date (YYYY-MM-DD) |
| `--checkout` | 32 days from now | Check-out date (YYYY-MM-DD) |
| `--adults` | 2 | Number of adults |
| `--rooms` | 1 | Number of rooms |
| `--pages` | 2 | Pages to scrape (25 hotels/page) |
| `--output` | auto-generated | CSV output file path |
| `--json` | false | Also export JSON |
| `--delay` | 3.0 | Delay between requests (seconds) |

## Notes

- Booking.com may block automated requests. If you get empty results, try again later or use a VPN.
- A Selenium fallback is available — see the comments in `scraper.py`.
- Always respect Booking.com's Terms of Service and robots.txt.

## License

MIT
