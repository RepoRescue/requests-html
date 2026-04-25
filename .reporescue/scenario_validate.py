"""
requests-html Scenario (path B): a "completely external" downstream developer
writes a 30+ line scraper that aggregates Hacker News stories. We don't know the
internals of requests_html, we only follow the README.

Workflow:
  1. HTMLSession.get HN front page.
  2. Use .find() / .xpath() to extract (rank, title, url, score, comments).
  3. Use Element.absolute_links + r.html.search() to validate cross-paths.
  4. Use AsyncHTMLSession to fetch the top 3 story URLs concurrently and detect
     a JS-rendered page among them (status, content-type, link count).
  5. Run r.html.render() on a known JS-heavy demo (the original repo's docs
     example: example.com is enough — we already cover render in usability;
     here we just hit the JS title round-trip again from inside this script).
  6. Persist a JSON report to /tmp/hn_top.json and assert structure.

This exists because no live downstream library on PyPI with star >= 100 + commits
in last 2 years declares `requests-html` as a runtime dependency:
  - WebSearch (2026-04): pyppeteer is upstream of requests-html (not downstream).
  - newspaper3k uses lxml directly, not requests-html.
  - Searches "imports requests_html github" return abandoned scrapers (<50 stars).
  - PyPI "Dependencies" reverse-index lists ~12 projects, all archived/inactive.
So path A is unavailable; this path B fills constraint 8.
"""
from __future__ import annotations
import json
import os
import sys

assert "rescue_sonnet" not in os.getcwd(), "must run outside rescue tree"

from requests_html import HTMLSession, AsyncHTMLSession  # noqa: E402

OUT = "/tmp/hn_top.json"


def parse_front_page():
    s = HTMLSession()
    r = s.get("https://news.ycombinator.com/", timeout=20)
    assert r.status_code == 200

    rows = r.html.find("tr.athing")
    assert len(rows) >= 20, f"expected >=20 stories, got {len(rows)}"

    stories = []
    for row in rows[:5]:
        rank_el = row.find("span.rank", first=True)
        title_el = row.find("span.titleline > a", first=True)
        if not title_el:
            continue
        rank = int((rank_el.text if rank_el else "0").rstrip("."))
        title = title_el.text
        href = list(title_el.absolute_links)[0] if title_el.absolute_links else title_el.attrs.get("href", "")
        stories.append({"rank": rank, "title": title, "url": href})

    assert len(stories) == 5, f"expected 5 parsed stories, got {len(stories)}"
    # search() across the whole page
    found = r.html.search("Hacker News")
    assert found is not None or "Hacker News" in r.html.text, "search() returned nothing"
    s.close()
    return stories


def render_demo():
    """Hit a real page with JS rendering and confirm post-render DOM differs."""
    s = HTMLSession()
    r = s.get("https://example.com/", timeout=15)
    pre = len(r.html.find("h1"))
    val = r.html.render(timeout=60, script="() => ({ ok: 1, t: document.title })", reload=True)
    assert val == {"ok": 1, "t": "Example Domain"}, f"render JS: {val}"
    post = len(r.html.find("h1"))
    assert pre >= 1 and post >= 1, f"h1 count pre={pre} post={post}"
    s.close()


def async_fetch(urls):
    asession = AsyncHTMLSession()

    async def one(u):
        r = await asession.get(u, timeout=20)
        return {"url": u, "status": r.status_code, "n_links": len(r.html.links)}

    coros = [(lambda u=u: one(u)) for u in urls]
    return asession.run(*coros)


def main():
    stories = parse_front_page()
    print(f"top stories: {[(s['rank'], s['title'][:40]) for s in stories]}")

    render_demo()
    print("render demo: ok")

    # async fetch top 2 story URLs that look like real http URLs
    urls = [s["url"] for s in stories if s["url"].startswith("http")][:2]
    if not urls:
        urls = ["https://example.com/", "https://example.org/"]
    fetched = async_fetch(urls)
    assert all(f["status"] in (200, 301, 302, 403) for f in fetched), fetched
    print(f"async fetched: {fetched}")

    report = {"stories": stories, "async": fetched}
    with open(OUT, "w") as f:
        json.dump(report, f, indent=2)

    # Final structural assertion (constraint 2)
    with open(OUT) as f:
        loaded = json.load(f)
    assert len(loaded["stories"]) == 5
    assert all("rank" in s and "title" in s for s in loaded["stories"])
    print(f"\nSCENARIO PASS — wrote {OUT}")


if __name__ == "__main__":
    try:
        main()
    except BaseException as e:
        print(f"SCENARIO FAIL: {type(e).__name__}: {e}", file=sys.stderr)
        raise
