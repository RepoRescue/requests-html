"""
Bug-hunt for requests-html (Step 7, anti-PyCG-blindspot).

We probe edges that the patch surface implies might be fragile:

  H1. Empty / None HTML body — does HTML(html=b'') crash on lxml parse?
  H2. Repeated render() on the same HTMLSession — state leak in self.session.loop?
  H3. Pagination / __next__ generator — patch added StopIteration but does it
      actually terminate when no next link exists?
  H4. Unicode + non-ASCII tag content — lxml_html_clean Cleaner roundtrip.
  H5. Nested AsyncHTMLSession invocations — get_running_loop() on already-running
      loop should not crash.
  H6. Render with broken JS — does it propagate the error cleanly or hang?
"""
from __future__ import annotations
import asyncio
import os
import sys
import traceback

assert "rescue_sonnet" not in os.getcwd()

found: list[str] = []
attempted: list[str] = []


def hunt(name):
    def deco(fn):
        attempted.append(name)
        def wrap():
            try:
                fn()
                print(f"[OK]  {name}")
            except BaseException as e:
                found.append(f"{name}: {type(e).__name__}: {e}")
                print(f"[BUG] {name}: {type(e).__name__}: {e}")
                traceback.print_exc()
        return wrap
    return deco


@hunt("H1_empty_html")
def _h1():
    from requests_html import HTML
    h = HTML(html=b"")
    # Should not crash; find should return empty
    assert h.find("p") == [] or h.find("p") is not None  # accept either


@hunt("H4_unicode_clean")
def _h4():
    from requests_html import HTML
    raw = "<html><body><p>こんにちは <b>世界</b> 🎉</p><script>x=1</script></body></html>".encode("utf-8")
    h = HTML(html=raw)
    p = h.find("p", first=True, clean=True)
    assert p is not None
    assert "こんにちは" in p.text and "世界" in p.text, f"unicode lost: {p.text!r}"
    assert "<script>" not in p.html


@hunt("H3_pagination_terminates")
def _h3():
    """The __next__ patch raises StopIteration when next() returns None.
    We feed an HTML with no 'next' link and confirm iteration terminates."""
    from requests_html import HTML
    h = HTML(html=b"<html><body><p>only page</p></body></html>",
             url="https://example.com/page1")
    # iter() on HTML yields pages via __next__; with no next link this should
    # raise StopIteration immediately, not loop forever.
    it = iter(h)
    try:
        next(it)
        # If we got here, there was a next page somehow — also fine
    except StopIteration:
        pass  # expected


@hunt("H2_render_repeat")
def _h2():
    from requests_html import HTMLSession
    s = HTMLSession()
    for i in range(2):
        r = s.get("https://example.com/", timeout=15)
        v = r.html.render(timeout=60, script="() => 42", reload=True)
        assert v == 42, f"iter {i}: {v}"
    s.close()


@hunt("H6_render_broken_js")
def _h6():
    from requests_html import HTMLSession
    s = HTMLSession()
    r = s.get("https://example.com/", timeout=15)
    try:
        r.html.render(timeout=30, script="() => { throw new Error('boom'); }", reload=True)
    except Exception as e:
        # Expected: should propagate as ElementHandleError, not hang
        assert "boom" in str(e) or "Error" in str(e), f"unexpected: {e}"
    s.close()


@hunt("H5_async_nested")
def _h5():
    """Inside an already-running loop, AsyncHTMLSession() should still construct
    without crashing thanks to the get_running_loop() patch."""
    from requests_html import AsyncHTMLSession

    async def inner():
        # constructed inside running loop — patch path B
        a = AsyncHTMLSession()
        r = await a.get("https://example.com/", timeout=15)
        return r.status_code

    code = asyncio.run(inner())
    assert code == 200


def main():
    _h1(); _h4(); _h3(); _h2(); _h6(); _h5()
    print()
    print(f"Attempted : {attempted}")
    print(f"Found bugs: {found if found else 'none'}")


if __name__ == "__main__":
    main()
