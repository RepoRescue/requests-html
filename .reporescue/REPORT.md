# requests-html — Usability Validation (SKILL v2 rerun)

**Selected rescue**: sonnet (srconly: PASS — also kimi/gpt-codex/glm/minimax all PASS, sonnet picked per priority sonnet > gpt-codex > kimi > glm > minimax, srconly-PASS confirmed source-only patch sufficient)
**Scenario type**: B (end-user library API + path B 30-line scraper; no live downstream meeting star >= 100 + 2-year activity)
**Real-world use**: HTML scraping with optional JavaScript rendering via headless Chromium — the only PSF library that combines `requests` ergonomics with `pyppeteer` JS execution.

## Step 0: Import sanity
`<rescue>/venv-t2/bin/python -c "import requests_html"` → **OK**

## Step 4: Install + core feature (clean venv, outside rescue tree)
- `python3.13 -m venv /tmp/requests-html-clean` → OK
- `pip install -e /home/zhihao/hdd/RepoRescue_Clean/repos/rescue_sonnet/requests-html` → **OK** (resolved 23 deps including pyppeteer 2.0, lxml 6.1, lxml-html-clean 0.4.4)
- Switched cwd to `/tmp/requests-html-clean`. Validate script `assert "rescue_sonnet" not in os.getcwd()` enforces this.
- Core feature exercised: `r.html.render()` launches Chromium (cached at `~/.local/share/pyppeteer/local-chromium/1181205`), navigates to example.com, runs JS `() => ({title, h1, two_plus_two: 2+2})`, returns dict to Python.
- Result: **PASS** (all 5 paths green).

## Hard constraint 6: Py3.13 surface stressed (with concrete evidence)

| Surface | Evidence |
|---|---|
| `lxml.html.clean` removed in lxml 5.x | src.patch: `-from lxml.html.clean import Cleaner` → `+from lxml_html_clean import Cleaner`. Validate path 3 invokes `cleaner.clean_html` via `find(..., clean=True)`. |
| `asyncio.get_event_loop()` no running loop in 3.12+, raises in 3.13 | `requests_html.py:823-833` patch: `try: get_running_loop() except RuntimeError: new_event_loop()`. Paths 4 + 5 + bug-hunt H5 exercise it. |
| PEP 479 StopIteration in `__next__` | patch line 489-491 raises explicit StopIteration. Bug-hunt H3 confirms. |

**Conclusion: NOT a TRIVIAL_RESCUE — rescue did real 3.13 work.**

## Beyond unit tests (constraint 3)

- T2 wrapper `validation/requests-html/t2_sonnet.sh`: `pytest … -k "not (render or browser or async or internet)"` — drops every render/async/internet test.
- `tests/test_requests_html.py` has 6 `@pytest.mark.render` tests + several `async def test_async_*` — **all skipped by the T2 filter**.
- v1 of this validation also missed `.render()` (used local static http.server). v2 corrected this.

## Step 5: Three+ distinct paths

| # | Path | Module touched |
|---|---|---|
| 1 | `HTML.parse_fixture` | `requests_html.HTML`, pyquery, lxml.html |
| 2 | `Element.find_clean` | Element, `lxml_html_clean.Cleaner`, xpath |
| 3 | `HTMLSession.get_live` | HTMLSession, requests, parse.search |
| 4 | `AsyncHTMLSession.get` | AsyncHTMLSession, asyncio.run_until_complete |
| 5 | `HTMLSession.render_js` | HTML.render, pyppeteer.launch, Chromium JS engine |

5 distinct subsystems; 5 PASS.

## Step 6: Downstream / Scenario

- **Path A**: skipped — searched for ≥100 star + 2-year activity downstream. pyppeteer is upstream; newspaper3k uses lxml directly; PyPI reverse-deps (~12) are archived <50-star scrapers. No qualifying downstream.
- **Path B**: `scenario_validate.py` (95 lines) — HN scraper. Parses 5 stories, runs `.render()` with JS round-trip on example.com, fetches top URLs concurrently via `AsyncHTMLSession`, persists JSON to /tmp/hn_top.json. **PASS**.

## Step 7: Bug-hunt

| Probe | Result |
|---|---|
| H1_empty_html (`HTML(html=b"")`) | **BUG**: `lxml.etree.ParserError: Document is empty` propagates unguarded. **Pre-existing upstream behavior, not regression**. |
| H2_render_repeat | OK |
| H3_pagination_terminates | OK (PEP 479 patch works) |
| H4_unicode_clean (JP + emoji + script) | OK |
| H5_async_nested (AsyncHTMLSession inside running loop) | OK |
| H6_render_broken_js | OK (ElementHandleError, no hang) |

Found bug is at constructor in upstream pyquery/lxml layer, not the rescue patch. Per SKILL "找到 bug 不否决 USABLE".

## Hard constraint matrix

| # | Constraint | Status |
|---|---|---|
| 1 | Real input | PASS (HN live URL, example.com live URL, real fixture) |
| 2 | Real output assertion | PASS (rank int, two_plus_two==4 from Chromium, len(stories)==5, JSON reload) |
| 3 | Beyond unit tests | PASS (T2 filter drops every patched-path test) |
| 4 | Primary use mode | PASS (`.render()` launches Chromium and round-trips JS — v1 had skipped this) |
| 5 | Three distinct paths | PASS (5 subsystems) |
| 6 | Stress 3.13 surface | PASS (lxml.html.clean + get_event_loop + PEP 479 with grep evidence) |
| 7 | Installed + core feature | PASS (clean venv pip install -e, cwd switched out) |
| 8 | Downstream OR scenario | PASS via path B |

## Verdict

**STATUS: USABLE**

Reason: All 8 hard constraints pass, the招牌 `.render()` JS pipeline runs end-to-end on Python 3.13 (Chromium launched, JS evaluated, DOM round-tripped), all three patched 3.13 surfaces are concretely stressed, and bug-hunt only surfaces a pre-existing upstream constructor edge case. v1's假 USABLE (which never touched `.render()` and ran inside the rescue tree) is corrected.

STATUS: USABLE
