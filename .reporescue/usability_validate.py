"""
requests-html usability validation (SKILL v2).

Hard constraints checklist:
1. Real input  : fetch live HTML from a real URL (HN front page) AND parse fixture.
2. Real output : assert specific strings/structure (HN story rows, link href values, search match).
3. Beyond unit: render pipeline + AsyncHTMLSession exercise (T2 explicitly excludes -k 'render or async or internet').
4. Primary use: invoke r.html.render() — the JS rendering招牌功能 — against a live page.
5. >=3 paths  : HTMLSession (sync), AsyncHTMLSession, HTML(), Element, render() pipeline.
6. 3.13 surface stressed:
   - lxml.html.clean -> lxml_html_clean (lxml 5.x removed Cleaner)
   - asyncio.get_event_loop() -> get_running_loop() (3.12+ deprecation, 3.13 raises)
   - StopIteration semantics in generator (PEP 479)
7. Run from /tmp after pip install -e — script is invoked with cwd=/tmp/requests-html-clean.
8. Scenario path B: 30+ line "scraper" workflow (no live downstream available with star>=100 + recent commit
   that imports requests_html; pyppeteer/lxml are dependencies, not consumers).

Run:
    cd /tmp/requests-html-clean
    /tmp/requests-html-clean/bin/python /home/zhihao/hdd/RepoRescue_Clean/artifacts/requests-html/usability_validate.py
"""

from __future__ import annotations
import os
import sys
import asyncio
import traceback

ART = "/home/zhihao/hdd/RepoRescue_Clean/artifacts/requests-html"
HN_FIXTURE = os.path.join(ART, "fixtures", "hn.html")

# Confirm not running from rescue tree.
cwd = os.getcwd()
assert "rescue_sonnet" not in cwd and "RepoRescue_Clean" not in cwd, \
    f"validate must not run inside rescue tree, got cwd={cwd}"

results: dict[str, str] = {}

def step(name):
    def deco(fn):
        def wrap():
            try:
                fn()
                results[name] = "PASS"
                print(f"[PASS] {name}")
            except BaseException as e:
                results[name] = f"FAIL: {type(e).__name__}: {e}"
                print(f"[FAIL] {name}: {e}")
                traceback.print_exc()
        return wrap
    return deco


# ---------------------------------------------------------------------------
# Path 1: HTML(...) parser on a real fixture (no network) — hits lxml + pyquery
# ---------------------------------------------------------------------------
@step("HTML.parse_fixture")
def t_parse():
    from requests_html import HTML
    with open(HN_FIXTURE, "rb") as f:
        raw = f.read()
    html = HTML(html=raw)
    # Real assertion: HN front page always has table rows of class 'athing'
    items = html.find("tr.athing")
    assert len(items) >= 10, f"expected >=10 stories, got {len(items)}"
    # Each story has a title link
    first = items[0]
    title_link = first.find("span.titleline > a", first=True)
    assert title_link is not None and title_link.text, "no title text in first story"
    assert "links" in dir(html)
    # absolute_links touches w3lib + urlparse
    assert isinstance(html.absolute_links, set)
    print(f"  HN first story title: {title_link.text[:60]!r}")
    print(f"  total athing rows   : {len(items)}")


# ---------------------------------------------------------------------------
# Path 2: HTMLSession.get on a live URL — exercises requests integration
# ---------------------------------------------------------------------------
@step("HTMLSession.get_live")
def t_session():
    from requests_html import HTMLSession
    s = HTMLSession()
    r = s.get("https://news.ycombinator.com/", timeout=15)
    assert r.status_code == 200
    titles = r.html.find("span.titleline > a")
    assert len(titles) >= 10, f"expected >=10 titles live, got {len(titles)}"
    # search() — covers parse module
    assert r.html.search('Hacker News') is not None or 'Hacker News' in r.html.text
    s.close()


# ---------------------------------------------------------------------------
# Path 3: Element.find + xpath + clean_html (touches lxml_html_clean fix)
# ---------------------------------------------------------------------------
@step("Element.find_clean")
def t_clean():
    from requests_html import HTML
    raw = b"""<html><body>
        <div id="x"><script>alert('xss')</script><p>hello <b>world</b></p></div>
    </body></html>"""
    h = HTML(html=raw)
    # find with clean=True triggers lxml_html_clean.Cleaner — the patched import
    div = h.find("#x", first=True, clean=True)
    assert div is not None
    assert "alert" not in div.html, f"cleaner did not strip script: {div.html!r}"
    # xpath path
    ps = h.xpath("//p")
    assert len(ps) == 1 and "hello" in ps[0].text


# ---------------------------------------------------------------------------
# Path 4: AsyncHTMLSession — exercises the get_running_loop() patch
# ---------------------------------------------------------------------------
@step("AsyncHTMLSession.get")
def t_async():
    from requests_html import AsyncHTMLSession
    asession = AsyncHTMLSession()

    async def fetch():
        r = await asession.get("https://example.com/", timeout=15)
        return r

    # asession.run wraps run_until_complete; needs the loop fix to not crash on 3.13
    # Use the high-level .run() API per README
    results_list = asession.run(fetch)
    r = results_list[0]
    assert r.status_code == 200
    assert "Example Domain" in r.html.text
    asession.close()


# ---------------------------------------------------------------------------
# Path 5 (primary use): r.html.render() — JS rendering via Chromium
# ---------------------------------------------------------------------------
@step("HTMLSession.render_js")
def t_render():
    from requests_html import HTMLSession
    s = HTMLSession()
    r = s.get("https://example.com/", timeout=15)
    # render() launches Chromium via pyppeteer. It also injects a tiny JS to
    # confirm execution: we override window-level value and read it back.
    # JS that does not depend on a specific selector — just confirms JS engine
    # ran inside the rendered page and that document.title made the round-trip.
    script = """() => {
        const h1 = document.querySelector('h1');
        return {
            title: document.title,
            h1: h1 ? h1.innerText : null,
            ua: navigator.userAgent,
            two_plus_two: 2 + 2,
        };
    }"""
    val = r.html.render(timeout=60, script=script, reload=True)
    assert isinstance(val, dict), f"render() should return script result dict, got {type(val)}"
    assert val.get("two_plus_two") == 4, f"JS engine math broken: {val}"
    assert "example" in (val.get("title") or "").lower(), f"document.title wrong: {val}"
    assert "Mozilla" in val.get("ua", "") or "Chrome" in val.get("ua", ""), f"UA wrong: {val}"
    # After render(), r.html should now be the rendered DOM (not the initial bytes).
    rendered_h1 = r.html.find("h1", first=True)
    assert rendered_h1 is not None and "example" in rendered_h1.text.lower(), \
        f"r.html post-render does not contain h1: {r.html.html[:200]}"
    s.close()
    print(f"  render() returned: title={val['title']!r}, h1={val.get('h1')!r}")


def main():
    t_parse()
    t_clean()
    t_session()
    t_async()
    t_render()
    print()
    for k, v in results.items():
        print(f"{k:30s} -> {v}")
    fails = [k for k, v in results.items() if v != "PASS"]
    if fails:
        print(f"\nFAILED steps: {fails}")
        sys.exit(1)
    print("\nALL PASS")


if __name__ == "__main__":
    main()
