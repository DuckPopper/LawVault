"""Click-to-place, drag and resize a signature on a page preview. A tiny custom Streamlit component
(plain HTML + the component postMessage protocol, no build step). Returns {x, y, w} as fractions of the page."""
import base64
import hashlib
from pathlib import Path
import streamlit.components.v1 as components

_comp = components.declare_component("sigplace", path=str(Path(__file__).parent / "components" / "sigplace"))


def place(page_png: bytes, sig_png: bytes, key: str, x: float = 0.75, y: float = 0.88, w: float = 0.22, hint: str = ""):
    """Shows the page with the signature on it. The value is the last position the user left it at (the initial
    one until they touch it). A new page or signature resets the position to x, y, w."""
    token = hashlib.sha1(page_png[:4096] + sig_png, usedforsecurity=False).hexdigest()[:16]
    val = _comp(page=base64.b64encode(page_png).decode(), sig=base64.b64encode(sig_png).decode(), token=token,
                x=x, y=y, w=w, hint=hint, key=f"{key}_{token}", default={"x": x, "y": y, "w": w})
    return val or {"x": x, "y": y, "w": w}
