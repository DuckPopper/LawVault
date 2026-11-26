"""Edit-a-PDF-page canvas: text, boxes, highlights and whiteouts you click, drag and resize on the real page.
A small custom Streamlit component (plain HTML, no build step). Returns the page's items as fractions of the page."""
import base64
import hashlib
from pathlib import Path
import streamlit.components.v1 as components

_comp = components.declare_component("pdfedit", path=str(Path(__file__).parent / "components" / "pdfedit"))


def edit(page_png: bytes, items: list, key: str, hint: str = "") -> list:
    """Shows the page with `items` on it and returns the list as the user left it. A different page image
    (a new page or file) resets the canvas to `items`."""
    token = hashlib.sha1(page_png[:4096] + str(len(page_png)).encode(), usedforsecurity=False).hexdigest()[:16]
    val = _comp(page=base64.b64encode(page_png).decode(), items=items, token=token, hint=hint,
                key=f"{key}_{token}", default={"items": items})
    got = (val or {}).get("items")
    return got if isinstance(got, list) else items
