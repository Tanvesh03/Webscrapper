"""
Booking.com Web Scraper - MCP Edition
=======================================
Designed for Claude Code + VS Code with MCP server integration.

Install:  pip install -r requirements.txt

CLI:      python scraper.py --city Dubai --checkin 2026-06-01 --checkout 2026-06-05
Python:   from scraper import BookingMCPScraper
          df = BookingMCPScraper().scrape("Dubai","2026-06-01","2026-06-05")
"""

import argparse, json, os, re, sys, time, random
from datetime import datetime, timedelta
from typing import Optional

import requests
from bs4 import BeautifulSoup
import pandas as pd


class BookingMCPScraper:
    """
    Booking.com hotel data scraper with MCP-compatible tool interface.

    Fields scraped: name, location, price, rating, reviews,
                    stars, distance, breakfast, url
    """

    BASE_URL = "https://www.booking.com/searchresults.html"
    CURRENCY = "USD"

    HEADERS = [
        {
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/124.0.0.0 Safari/537.36"),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Referer": "https://www.booking.com/",
            "Connection": "keep-alive",
        },
        {
            "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"),
            "Accept-Language": "en-GB,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        },
    ]

    def __init__(self, delay: float = 3.0):
        self.session = requests.Session()
        self.delay_range = (delay, delay + 2)
        self._data: list[dict] = []

    # ── MCP Tool Interface ─────────────────────────────────────────────
    def call_tool(self, tool_name: str, params: dict) -> dict:
        """MCP dispatcher — call search_hotels or get_hotel_info."""
        if tool_name == "search_hotels":
            return self._tool_search(params)
        if tool_name == "get_hotel_info":
            return self._tool_detail(params)
        raise ValueError(f"Unknown MCP tool: {tool_name}")

    def _tool_search(self, p: dict) -> dict:
        df = self.scrape(
            city      = p.get("destination", p.get("city", "")),
            checkin   = p.get("check_in",  p.get("checkin", "")),
            checkout  = p.get("check_out", p.get("checkout", "")),
            adults    = int(p.get("adults", 2)),
            rooms     = int(p.get("rooms", 1)),
            max_pages = int(p.get("pages", 2)),
        )
        return {"tool": "search_hotels", "count": len(df),
                "result": df.to_dict(orient="records")}

    def _tool_detail(self, p: dict) -> dict:
        html = self._fetch(p.get("url", ""))
        if not html:
            return {"tool": "get_hotel_info", "error": "fetch_failed"}
        soup  = BeautifulSoup(html, "lxml")
        title = soup.find("h2", class_=re.compile(r"pp-header__title|hotel_name"))
        desc  = soup.find("div", attrs={"data-testid": "property-description"})
        return {
            "tool": "get_hotel_info",
            "name": title.get_text(strip=True) if title else "N/A",
            "description": desc.get_text(" ", strip=True)[:500] if desc else "N/A",
        }

    # ── HTTP helpers ───────────────────────────────────────────────────
    def _headers(self): return random.choice(self.HEADERS)

    def _build_url(self, city, checkin, checkout, adults, rooms, offset) -> str:
        params = {
            "ss": city, "checkin": checkin, "checkout": checkout,
            "group_adults": adults, "no_rooms": rooms, "offset": offset,
            "lang": "en-us", "selected_currency": self.CURRENCY, "order": "popularity",
        }
        return self.BASE_URL + "?" + "&".join(f"{k}={v}" for k, v in params.items())

    def _fetch(self, url: str) -> Optional[str]:
        for attempt in range(3):
            try:
                r = self.session.get(url, headers=self._headers(), timeout=20)
                print(f"    HTTP {r.status_code}")
                if r.status_code == 200: return r.text
                if r.status_code == 429:
                    w = 30 + random.randint(0, 20)
                    print(f"    Rate-limited — waiting {w}s …"); time.sleep(w)
                elif r.status_code in (403, 503):
                    print(f"    Blocked ({r.status_code})."); return None
            except Exception as e:
                print(f"    Attempt {attempt+1}/3: {e}")
            time.sleep(random.uniform(*self.delay_range))
        return None

    # ── Parser ─────────────────────────────────────────────────────────
    def _parse(self, html: str) -> list[dict]:
        soup  = BeautifulSoup(html, "lxml")
        cards = soup.find_all("div", attrs={"data-testid": "property-card"})
        if not cards:
            cards = soup.find_all("div", class_=re.compile(r"sr_property_block"))
        print(f"    {len(cards)} cards found")
        out = []
        for card in cards:
            h = {}
            f = card.find  # shorthand

            el = (f("div", attrs={"data-testid": "title"}) or
                  f("span", class_=re.compile(r"sr-hotel__name|hotel_name")))
            h["name"] = el.get_text(strip=True) if el else "N/A"

            el = (f("span", attrs={"data-testid": "address"}) or
                  f("span", class_=re.compile(r"address")))
            h["location"] = el.get_text(strip=True) if el else "N/A"

            el = (f("span", attrs={"data-testid": "price-and-discounted-price"}) or
                  f("span", class_=re.compile(r"bui-price-display")))
            if el:
                raw = el.get_text(strip=True)
                m = re.search(r"[$€£]?\s?[\d,]+", raw)
                h["price"] = m.group(0).strip() if m else raw
            else: h["price"] = "N/A"

            el = (f("div", attrs={"data-testid": "review-score"}) or
                  f("span", class_=re.compile(r"review-score-badge")))
            if el:
                txt  = el.get_text(" ", strip=True)
                nums = re.findall(r"\d+\.?\d*", txt)
                h["rating"] = nums[0] if nums else "N/A"
                m = re.search(r"([\d,]+)\s*review", txt, re.I)
                h["reviews"] = m.group(1) if m else "N/A"
            else: h["rating"] = h["reviews"] = "N/A"

            el = f("div", attrs={"data-testid": "rating-stars"})
            h["stars"] = len(el.find_all("span", attrs={"aria-hidden":"true"})) if el else "N/A"

            el = f("span", attrs={"data-testid": "distance"})
            h["distance"] = el.get_text(strip=True) if el else "N/A"

            el = f("span", class_=re.compile(r"breakfast", re.I))
            h["breakfast"] = el.get_text(strip=True) if el else "N/A"

            el = (f("a", attrs={"data-testid": "title-link"}) or
                  f("a", class_=re.compile(r"hotel_name_link")))
            if el and el.get("href"):
                href = el["href"]
                h["url"] = href if href.startswith("http") else "https://www.booking.com" + href
            else: h["url"] = "N/A"

            if h["name"] != "N/A": out.append(h)
        return out

    # ── Public scrape() ────────────────────────────────────────────────
    def scrape(self, city, checkin=None, checkout=None,
               adults=2, rooms=1, max_pages=2) -> pd.DataFrame:
        """Scrape Booking.com and return a pandas DataFrame."""
        if not checkin:  checkin  = (datetime.today()+timedelta(days=30)).strftime("%Y-%m-%d")
        if not checkout: checkout = (datetime.today()+timedelta(days=32)).strftime("%Y-%m-%d")
        self._data = []
        print(f"\nScraping: {city} | {checkin} → {checkout} | {adults} adults, {rooms} room(s)")
        for page in range(max_pages):
            offset = page * 25
            url    = self._build_url(city, checkin, checkout, adults, rooms, offset)
            print(f"  Page {page+1}/{max_pages}  offset={offset}")
            html = self._fetch(url)
            if not html: print("  Fetch failed."); break
            if "captcha" in html.lower() or len(html) < 5000:
                print("  CAPTCHA detected — use Selenium fallback."); break
            hotels = self._parse(html)
            if not hotels: print("  No results."); break
            self._data.extend(hotels)
            print(f"  Total: {len(self._data)}")
            if page < max_pages - 1:
                d = random.uniform(*self.delay_range)
                print(f"  Sleeping {d:.1f}s …"); time.sleep(d)
        print(f"  Done: {len(self._data)} hotels.")
        return pd.DataFrame(self._data) if self._data else pd.DataFrame()

    def save_csv(self, df, path=None) -> str:
        if not path: path = f"booking_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(path, index=False)
        print(f"  Saved {len(df)} rows → {path}"); return path


# ── CLI ───────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(description="Booking.com MCP Scraper")
    p.add_argument("--city",     required=True)
    p.add_argument("--checkin",  default=None)
    p.add_argument("--checkout", default=None)
    p.add_argument("--adults",   type=int,   default=2)
    p.add_argument("--rooms",    type=int,   default=1)
    p.add_argument("--pages",    type=int,   default=2)
    p.add_argument("--output",   default=None)
    p.add_argument("--json",     action="store_true")
    p.add_argument("--delay",    type=float, default=3.0)
    args = p.parse_args()
    scraper = BookingMCPScraper(delay=args.delay)
    df = scraper.scrape(args.city, args.checkin, args.checkout,
                        args.adults, args.rooms, args.pages)
    if df.empty: print("No data scraped."); sys.exit(1)
    out = scraper.save_csv(df, args.output)
    if args.json:
        jp = out.replace(".csv", ".json")
        df.to_json(jp, orient="records", indent=2)
        print(f"  JSON → {jp}")
    print(f"Summary: {len(df)} hotels | cols: {list(df.columns)}")

if __name__ == "__main__": main()
