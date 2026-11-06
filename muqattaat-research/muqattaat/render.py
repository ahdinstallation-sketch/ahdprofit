"""Arabic-aware rendering helpers for matplotlib and reportlab."""
import re

import arabic_reshaper
from bidi.algorithm import get_display

from . import RAW

FONT_REGULAR = RAW / "fonts/Amiri-Regular.ttf"
FONT_BOLD = RAW / "fonts/Amiri-Bold.ttf"
_AR_RUN = re.compile(r"[؀-ۿ][؀-ۿ\s‌]*[؀-ۿ]|[؀-ۿ]")


def ar(text: str) -> str:
    """Shape and visually order every Arabic run inside an otherwise LTR string."""
    if not isinstance(text, str):
        return text
    return _AR_RUN.sub(lambda m: get_display(arabic_reshaper.reshape(m.group())), text)


def mpl(text: str) -> str:
    """matplotlib >= 3.11 shapes and reorders Arabic itself (libraqm), so text is passed raw;
    a left-to-right mark keeps mixed Latin/Arabic labels in LTR paragraph order, and the
    neutral arrow is replaced by a Latin word so it cannot merge two Arabic runs."""
    if not isinstance(text, str):
        return text
    return "‎" + text.replace("→", "to")


def setup_matplotlib():
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import font_manager, rcParams
    font_manager.fontManager.addfont(str(FONT_REGULAR))
    font_manager.fontManager.addfont(str(FONT_BOLD))
    rcParams["font.family"] = ["Amiri", "DejaVu Sans"]
    rcParams["axes.unicode_minus"] = False
