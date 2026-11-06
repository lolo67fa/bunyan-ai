"""Input language detection (Arabic vs English) without external libraries."""

from __future__ import annotations

import re

_ARABIC = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")
_LATIN = re.compile(r"[A-Za-z]")


def detect_language(text: str) -> str:
    """Return ``"ar"`` when Arabic letters dominate the text, else ``"en"``.

    Mixed input such as "تطبيق لإدارة المهام with due dates" counts as Arabic
    when at least 40% of its letters are Arabic, because Arabic speakers often
    keep technical terms in English.
    """
    arabic = len(_ARABIC.findall(text))
    latin = len(_LATIN.findall(text))
    if arabic == 0:
        return "en"
    return "ar" if arabic / (arabic + latin) >= 0.4 else "en"
