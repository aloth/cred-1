"""CRED-1: domain credibility ratings for news sources and websites.

Python access to the CRED-1 open dataset (https://github.com/aloth/cred-1).
The dataset ships inside the package, so lookups work offline.

    >>> import cred1
    >>> cred1.check("https://www.infowars.com/some/article")["category"]
    'fake'

Dataset license: CC-BY-4.0. Code license: MIT.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version as _pkg_version
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    __version__ = _pkg_version("cred1")
except PackageNotFoundError:  # source checkout
    __version__ = "0+unknown"

__all__ = [
    "check",
    "check_many",
    "search",
    "stats",
    "to_dataframe",
    "normalize_domain",
    "__version__",
]

# Compact category codes used in cred1_compact.json, same mapping as the npm package.
_CATEGORIES = {
    "f": "fake",
    "u": "unreliable",
    "m": "mixed",
    "c": "conspiracy",
    "s": "satire",
    "r": "rumor",
    "o": "other",
}

_dataset: Optional[Dict[str, Dict[str, Any]]] = None


def _data_path() -> Path:
    """The installed package carries the file; a source checkout reads data/."""
    here = Path(__file__).resolve().parent
    for candidate in (here / "cred1_compact.json", here.parent.parent / "data" / "cred1_compact.json"):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("cred1_compact.json not found; reinstall the cred1 package")


def _load() -> Dict[str, Dict[str, Any]]:
    global _dataset
    if _dataset is None:
        with _data_path().open(encoding="utf-8") as f:
            _dataset = json.load(f)
    return _dataset


def normalize_domain(value: str) -> str:
    """Lowercase, strip protocol, path, query, fragment, ``www.`` and a trailing dot."""
    d = value.strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = d.split("/")[0].split("?")[0].split("#")[0]
    d = re.sub(r"^www\.", "", d)
    return d.rstrip(".")


def _level(score: Optional[float]) -> str:
    if score is None:
        return "neutral"
    if score <= 0.2:
        return "low"
    if score <= 0.5:
        return "mixed"
    return "ok"


def _age_years(registered: Optional[str]) -> Optional[float]:
    if not registered:
        return None
    try:
        start = datetime.fromisoformat(registered).replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    days = (datetime.now(timezone.utc) - start).total_seconds() / 86400
    return round(days / 365.25, 1)


def _result(domain: str, entry: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "domain": domain,
        "score": entry["s"],
        "category": _CATEGORIES.get(entry["c"], entry["c"]),
        "level": _level(entry["s"]),
        "sources": entry["n"],
        "domain_age": _age_years(entry.get("d")),
        "tranco_rank": entry.get("r"),
    }


def check(domain: str) -> Optional[Dict[str, Any]]:
    """Look up one domain or URL. Returns ``None`` when the domain is not listed.

    The result has ``domain``, ``score`` (0.0 to 1.0, lower is less credible),
    ``category``, ``level`` (low, mixed, ok), ``sources``, ``domain_age`` (years)
    and ``tranco_rank``.
    """
    name = normalize_domain(domain)
    entry = _load().get(name)
    return _result(name, entry) if entry else None


def check_many(domains: Iterable[str]) -> Dict[str, Optional[Dict[str, Any]]]:
    """Look up several domains or URLs; keys are the inputs as given."""
    return {d: check(d) for d in domains}


def search(pattern: str) -> List[Dict[str, Any]]:
    """Domains matching a regular expression (or a literal substring if the
    pattern is not a valid regex), least credible first."""
    try:
        rx = re.compile(pattern, re.I)
    except re.error:
        rx = re.compile(re.escape(pattern), re.I)
    hits = [_result(d, e) for d, e in _load().items() if rx.search(d)]
    return sorted(hits, key=lambda r: r["score"])


def stats() -> Dict[str, Any]:
    """Total domain count, count per category (largest first) and package version."""
    counts: Dict[str, int] = {}
    for entry in _load().values():
        cat = _CATEGORIES.get(entry["c"], entry["c"])
        counts[cat] = counts.get(cat, 0) + 1
    return {
        "total_domains": len(_load()),
        "categories": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
        "version": __version__,
    }


def to_dataframe():
    """The whole dataset as a pandas DataFrame, one row per domain.

    Needs pandas: ``pip install "cred1[pandas]"``.
    """
    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover - message only
        raise ImportError('to_dataframe() needs pandas: pip install "cred1[pandas]"') from exc
    rows = [_result(d, e) for d, e in _load().items()]
    return pd.DataFrame(rows).sort_values("score", kind="stable").reset_index(drop=True)
