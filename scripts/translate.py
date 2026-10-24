#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Translate article titles to Chinese, with a persistent cache.

Google's translation endpoint is unreachable from many mainland networks and
MyMemory's anonymous quota is small, so this module uses Bing's public
translator endpoint (the one behind ``cn.bing.com/translator``). It is not an
official API: the token can expire and the endpoint can rate-limit. Every
result is cached in ``.geo-reader/journal-scan/translations.json`` so a scan
only pays for titles it has not seen before, and a partial run can be resumed
by rerunning the same command.

The Chinese title is for retrieval only. The English title remains the
authoritative one in the list and in any note.
"""

import datetime
import html
import json
import re
import time
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import requests

BING_HOSTS = ("https://cn.bing.com", "https://www.bing.com")
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
)
CACHE_VERSION = 1

# Bing sometimes picks a literal but wrong geoscience term. These are narrow
# fixes: each rule fires only when the English title contains the key, so an
# unrelated use of the Chinese string is left alone.
TERM_FIXES: Tuple[Tuple[str, Tuple[Tuple[str, str], ...]], ...] = (
    ("fugacity", (("逸散性", "逸度"), ("逃逸性", "逸度"))),
    ("sub-arc", (("亚弧", "弧下"), ("次弧", "弧下"))),
    ("back-arc", (("背弧", "弧后"), ("后弧", "弧后"))),
    ("magma ocean", (("岩浆海洋", "岩浆洋"),)),
    ("stagnant slab", (("停滞板块", "停滞板片"),)),
    ("delamination", (("脱层", "拆沉"), ("分层", "拆沉"))),
    ("remagnetization", (("再磁化", "重磁化"),)),
    ("paleosol", (("古溶胶", "古土壤"),)),
    ("large igneous province", (("大型火成岩省", "大火成岩省"),)),
    ("flood basalt", (("洪水玄武岩", "溢流玄武岩"),)),
    ("ground motion", (("地面运动", "地震动"),)),
    ("mid-ocean ridge", (("大洋中脊", "洋中脊"), ("中洋脊", "洋中脊"))),
    ("de novo", (("从零", "从头"),)),
    ("enantioselective", (("手性选择性", "对映选择性"),)),
    ("spatial confinement", (("空间限制", "空间限域"),)),
    ("conductance", (("导电性", "电导"),)),
)


class TranslationError(Exception):
    """The translation service could not be reached or returned no text."""


def _clean(text: str) -> str:
    raw = html.unescape(str(text or ""))
    raw = re.sub(r"<[^>]+>", "", raw)
    return re.sub(r"\s+", " ", raw).strip()


def _post_edit(english: str, chinese: str) -> str:
    """Apply a few geoscience-term corrections to a machine translation."""
    english_lower = english.lower()
    result = _clean(chinese)
    for key, fixes in TERM_FIXES:
        if key not in english_lower:
            continue
        for wrong, right in fixes:
            result = result.replace(wrong, right)
    return result


class BingTranslator:
    """One session, one token, sequential requests with a small pause."""

    def __init__(self, timeout: float = 15.0, pace: float = 0.22):
        self.timeout = timeout
        self.pace = pace
        self._session = requests.Session()
        self._session.headers.update(
            {"User-Agent": USER_AGENT, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}
        )
        self._api = ""
        self._key = ""
        self._token = ""
        self._last_request = 0.0

    def _wait(self) -> None:
        wait = self.pace - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()

    def _refresh(self) -> None:
        last_error = ""
        for host in BING_HOSTS:
            try:
                response = self._session.get(host + "/translator", timeout=self.timeout)
                response.raise_for_status()
                page = response.text
                helper = re.search(
                    r'params_AbusePreventionHelper\s*=\s*\[(\d+),\s*"([^"]+)"', page
                )
                ident = re.search(r'IG:"([^"]+)"', page)
                iid = re.search(r'data-iid="([^"]+)"', page)
                if helper and ident and iid:
                    self._key, self._token = helper.group(1), helper.group(2)
                    self._api = (
                        host
                        + "/ttranslatev3?isVertical=1&&IG="
                        + ident.group(1)
                        + "&IID="
                        + iid.group(1)
                        + ".1"
                    )
                    return
                last_error = "页面缺少翻译令牌"
            except Exception as exc:  # network errors are retried on the next host
                last_error = str(exc)
        raise TranslationError(
            "无法连接 Bing 翻译（{}）。中文标题可稍后重跑补齐，或使用 --no-translate。".format(
                last_error or "unknown error"
            )
        )

    def translate(self, text: str) -> str:
        text = _clean(text)
        if not text:
            return ""
        if not self._api:
            self._refresh()
        for attempt in range(2):
            self._wait()
            try:
                response = self._session.post(
                    self._api,
                    data={
                        "fromLang": "en",
                        "to": "zh-Hans",
                        "text": text,
                        "token": self._token,
                        "key": self._key,
                    },
                    timeout=self.timeout,
                )
                payload = response.json()
                if isinstance(payload, list) and payload:
                    translated = (
                        payload[0].get("translations", [{}])[0].get("text", "")
                    )
                    if _clean(translated):
                        return _clean(translated)
            except Exception:
                pass
            # Tokens expire and the endpoint occasionally returns 205/empty.
            if attempt == 0:
                time.sleep(1.0)
                self._refresh()
        raise TranslationError("翻译失败：{}".format(text[:80]))


def load_cache(path: Path) -> dict:
    if not path.is_file():
        return {"version": CACHE_VERSION, "titles": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": CACHE_VERSION, "titles": {}}
    if not isinstance(payload, dict):
        return {"version": CACHE_VERSION, "titles": {}}
    titles = payload.get("titles")
    if not isinstance(titles, dict):
        titles = {}
    return {
        "version": CACHE_VERSION,
        "provider": str(payload.get("provider") or "bing"),
        "updated_at": str(payload.get("updated_at") or ""),
        "titles": {str(key): str(value) for key, value in titles.items() if value},
    }


def save_cache(path: Path, cache: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cache["version"] = CACHE_VERSION
    cache["updated_at"] = datetime.datetime.now().astimezone().isoformat(
        timespec="seconds"
    )
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temp.replace(path)


def translate_titles(
    titles: Iterable[str],
    cache_path: Path,
    translator: Optional[Callable[[str], str]] = None,
    logger: Optional[Callable[[str], None]] = None,
    save_every: int = 20,
) -> Tuple[Dict[str, str], dict]:
    """Return ``({english: chinese}, metadata)`` using the on-disk cache.

    A title whose translation fails is omitted from the mapping; callers show
    it as missing rather than inventing a translation.
    """
    cache = load_cache(cache_path)
    cached = cache["titles"]
    engine = translator or BingTranslator().translate

    wanted = []
    seen = set()
    for title in titles:
        key = _clean(title)
        if key and key not in seen:
            seen.add(key)
            wanted.append(key)

    mapping: Dict[str, str] = {}
    pending: List[str] = []
    hits = 0
    for key in wanted:
        raw = cached.get(key) or ""
        if raw:
            mapping[key] = _post_edit(key, raw)
            hits += 1
        else:
            pending.append(key)

    if pending and logger:
        logger(
            "  [中文标题] 缓存命中 {}，待翻译 {}".format(hits, len(pending))
        )

    failures = 0
    consecutive = 0
    stopped = ""
    dirty = False
    for position, key in enumerate(pending, 1):
        try:
            raw = engine(key)
        except Exception as exc:
            failures += 1
            consecutive += 1
            if not stopped:
                stopped = str(exc)
            if consecutive >= 4:
                break
            time.sleep(1.0)
            continue
        consecutive = 0
        raw = _clean(raw)
        if not raw:
            failures += 1
            continue
        cached[key] = raw
        mapping[key] = _post_edit(key, raw)
        dirty = True
        if position % save_every == 0:
            save_cache(cache_path, cache)
            if logger:
                logger(
                    "  [中文标题] 已翻译 {}/{}".format(position, len(pending))
                )

    if dirty:
        save_cache(cache_path, cache)
    if logger and pending:
        logger(
            "  [中文标题] 完成 {}，失败 {}".format(
                len(mapping) - hits, failures
            )
        )
    metadata = {
        "provider": "bing" if translator is None else "custom",
        "cached": hits,
        "translated": len(mapping) - hits,
        "missing": max(0, len(wanted) - len(mapping)),
        "error": stopped,
    }
    return mapping, metadata
