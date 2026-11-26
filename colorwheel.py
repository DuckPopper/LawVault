"""A colour wheel for the accent colour. A tiny custom Streamlit component (plain HTML + the component postMessage
protocol, no build step). The value is the hue (0-359) the user last released the handle on, or None until they do."""
from pathlib import Path
import streamlit.components.v1 as components

_comp = components.declare_component("colorwheel", path=str(Path(__file__).parent / "components" / "colorwheel"))


def pick(hue: int, key: str, disabled: bool = False):
    return _comp(hue=int(hue), disabled=bool(disabled), key=key, default=None)
