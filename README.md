# requests-html (RepoRescue fork) 🛟

HTML scraping for humans, with optional JavaScript rendering via headless Chromium —
the only library that combines the `requests` ergonomics with `pyppeteer` JS execution.

This is an **unofficial fork** maintained under the [RepoRescue](https://github.com/RepoRescue) program.
The original project (`psf/requests-html`) has been unmaintained since 2020 and no longer
imports on Python 3.12+. This fork is **modernized for Python 3.13** and the current
`lxml` / `asyncio` releases — the public API is unchanged.

---

## Install

```bash
pip install git+https://github.com/RepoRescue/requests-html.git
```

Requires Python 3.13. The first call to `.render()` will download a Chromium build
(~150 MB) into `~/.local/share/pyppeteer/`.

## Quick start

Synchronous scraping with a CSS selector:

```python
from requests_html import HTMLSession

session = HTMLSession()
r = session.get("https://news.ycombinator.com/")
for row in r.html.find("tr.athing")[:5]:
    title = row.find("span.titleline > a", first=True)
    print(title.text, "->", title.attrs["href"])
```

JavaScript-rendered DOM (the headline feature) — Chromium is launched in the
background, the page is rendered, and your script runs in the live page context:

```python
from requests_html import HTMLSession

session = HTMLSession()
r = session.get("https://example.com/")

result = r.html.render(
    timeout=60,
    reload=True,
    script="() => ({ title: document.title, h1: document.querySelector('h1').innerText })",
)
print(result)  # {'title': 'Example Domain', 'h1': 'Example Domain'}

# After render(), r.html reflects the post-JS DOM
print(r.html.find("h1", first=True).text)
```

Async fan-out across multiple URLs:

```python
from requests_html import AsyncHTMLSession

asession = AsyncHTMLSession()

async def fetch(url):
    r = await asession.get(url, timeout=15)
    return r.status_code, len(r.html.links)

results = asession.run(
    lambda: fetch("https://example.com/"),
    lambda: fetch("https://example.org/"),
)
print(results)
```

## What this rescue actually changes

The patch is small and surgical — only what was needed to run on Python 3.13 + current
deps. The public API is untouched.

- **`lxml.html.clean` → `lxml_html_clean`.** `lxml` 5.x split the HTML cleaner into a
  separate package. `from lxml.html.clean import Cleaner` now reads
  `from lxml_html_clean import Cleaner`, and `lxml-html-clean` is an explicit dependency.
- **`asyncio.get_event_loop()` → `get_running_loop()` with fallback.** Python 3.12
  deprecated, and 3.13 raises, when `get_event_loop()` is called with no running loop.
  `AsyncHTMLSession.__init__` now does `try: get_running_loop(); except RuntimeError:
  new_event_loop()`, which works both inside and outside an existing loop.
- **PEP 479 in the pagination generator.** The `__next__` implementation that walked
  "next page" links used to leak a bare `StopIteration`, which since 3.7 turns into a
  `RuntimeError` inside generators. It now raises `StopIteration` explicitly when no
  next link is found.

That's the whole rescue surface. No behavioral changes, no new features.

## Caveats

- **Empty body crashes the constructor.** `HTML(html=b"")` raises
  `lxml.etree.ParserError: Document is empty` from inside `pyquery` / `lxml`.
  This is **pre-existing upstream behavior**, not introduced by the rescue, and was
  not patched (fixing it would change the public contract). Guard your inputs.
- **Chromium is a heavyweight dep.** `pyppeteer` downloads a ~150 MB Chromium build
  on first `.render()`. In sandboxed environments, set `PYPPETEER_HOME` or pre-cache.
- **`render()` is single-threaded per session.** The `pyppeteer` event loop is held
  on the session; do not share an `HTMLSession` across threads.
- The fork tracks the upstream API verbatim — if upstream had a bug in 2020 and
  it isn't a Python 3.13 incompatibility, this fork still has it.

## Validation evidence

Every claim above is reproduced end-to-end (live HN scrape, real Chromium launch, JS
round-trip, async fan-out, PEP 479 generator, unicode cleaner) by the validator at
[`.reporescue/REPORT.md`](.reporescue/REPORT.md). Status: **USABLE** under the
RepoRescue v2 protocol — five distinct subsystems exercised on Python 3.13, all green.

## Original project

- Upstream: <https://github.com/psf/requests-html>
- Original author: Kenneth Reitz (and contributors)
- License: MIT (preserved — see [LICENSE](LICENSE))

If upstream resumes maintenance, prefer it over this fork.

## Disclaimer

This is an unofficial fork. It is not endorsed by Kenneth Reitz, the Python Software
Foundation, or the original `requests-html` maintainers. The RepoRescue program
publishes minimal-diff Python 3.13 modernizations of abandoned libraries for users who
need them to keep working; bug reports about the rescue patch belong here, bug reports
about the underlying library belong upstream.
