from __future__ import annotations
import asyncio
import httpx
from bs4 import BeautifulSoup  # requires dependency
from typing import List, Dict

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36"

BASE_URL = "https://www.indeed.com/jobs"


async def fetch_page(client: httpx.AsyncClient, query: str, location: str | None, start: int) -> str:
    params = {"q": query, "start": start}
    if location:
        params["l"] = location
    r = await client.get(BASE_URL, params=params, timeout=20)
    r.raise_for_status()
    return r.text


def parse_jobs(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    jobs: List[Dict] = []
    for card in soup.select("div.job_seen_beacon"):
        title_el = card.select_one("h2 span")
        company_el = card.select_one("span.companyName")
        loc_el = card.select_one("div.companyLocation")
        link_el = card.select_one("h2 a")
        jd_el = card.select_one("div.job-snippet")
        if not title_el or not link_el:
            continue
        url = link_el.get("href")
        if url and url.startswith("/rc/"):
            url = f"https://www.indeed.com{url}"
        jobs.append({
            "title": title_el.get_text(strip=True),
            "company": company_el.get_text(strip=True) if company_el else None,
            "location": loc_el.get_text(" ", strip=True) if loc_el else None,
            "url": url,
            "description": jd_el.get_text(" ", strip=True) if jd_el else None,
        })
    return jobs


async def scrape_indeed(query: str, location: str | None = None, pages: int = 1) -> List[Dict]:
    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        tasks = [fetch_page(client, query, location, p * 10) for p in range(pages)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    jobs: List[Dict] = []
    for res in results:
        if isinstance(res, Exception):
            continue
        jobs.extend(parse_jobs(res))
    # de-duplicate by (title, company, location)
    seen = set()
    deduped = []
    for j in jobs:
        key = (j.get("title"), j.get("company"), j.get("location"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(j)
    return deduped

__all__ = ["scrape_indeed"]
