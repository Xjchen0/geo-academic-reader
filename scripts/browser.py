#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chrome DevTools Protocol (CDP) browser extraction.

The browser is the primary source for figures: it keeps the user's session
cookies, survives Cloudflare challenges, and exposes publisher high-resolution
image URLs. Direct HTTP and PDF extraction are fallbacks.
"""

import asyncio
import base64
import json
import os
import platform
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

import requests

from .config import CHROME_CDP_HTTP, DEFAULT_HEADERS, GUIDE_DIR
from .figures import pick_srcset, upgrade_figure_url

CDP_PORT = 9222


class BrowserError(RuntimeError):
    pass


class BrowserChallenge(BrowserError):
    pass


def chrome_status(port: int = CDP_PORT, timeout: float = 1.5) -> Optional[dict]:
    try:
        response = requests.get(
            "http://127.0.0.1:{}/json/version".format(port), timeout=timeout
        )
        if response.ok:
            return response.json()
    except Exception:
        return None
    return None


def find_chrome() -> Optional[str]:
    system = platform.system()
    candidates = []
    if system == "Darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ]
    elif system == "Windows":
        candidates = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        ]
    else:
        for name in (
            "google-chrome",
            "google-chrome-stable",
            "chromium",
            "chromium-browser",
            "microsoft-edge",
        ):
            found = shutil.which(name)
            if found:
                candidates.append(found)
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def ensure_chrome(
    port: int = CDP_PORT,
    launch: bool = True,
    profile_dir: Optional[Path] = None,
    timeout: int = 25,
) -> dict:
    """Return CDP status, launching Chrome with a dedicated profile if needed."""
    status = chrome_status(port)
    if status:
        return status
    if not launch:
        raise BrowserError(
            "Chrome CDP 未在 9222 端口运行。请用 --browser auto 自动启动，"
            "或手动运行: {}".format(chrome_launch_command(port))
        )

    chrome = find_chrome()
    if not chrome:
        raise BrowserError(
            "未找到 Chrome/Chromium/Edge。请安装 Chrome，或使用 --browser off 走 HTTP/PDF 回退。"
        )

    profile_dir = profile_dir or (GUIDE_DIR / "chrome-profile")
    profile_dir.mkdir(parents=True, exist_ok=True)
    args = [
        chrome,
        "--remote-debugging-port={}".format(port),
        "--user-data-dir={}".format(profile_dir),
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        "--disable-features=Translate",
        "--start-maximized",
    ]
    try:
        subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as exc:
        raise BrowserError("无法启动 Chrome: {}".format(exc))

    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(0.5)
        status = chrome_status(port)
        if status:
            return status
    raise BrowserError(
        "Chrome 已启动但 9222 端口未就绪。请检查是否有安全软件拦截，"
        "或手动运行: {}".format(chrome_launch_command(port))
    )


def chrome_launch_command(port: int = CDP_PORT) -> str:
    system = platform.system()
    if system == "Darwin":
        return (
            '"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" '
            '--remote-debugging-port={} --user-data-dir="$HOME/.geo-reader/chrome-profile"'
        ).format(port)
    if system == "Windows":
        return (
            '& "$env:ProgramFiles\\Google\\Chrome\\Application\\chrome.exe" '
            '--remote-debugging-port={} --user-data-dir="$env:TEMP\\geo-reader-chrome"'
        ).format(port)
    return (
        'google-chrome --remote-debugging-port={} '
        '--user-data-dir="$HOME/.geo-reader/chrome-profile" &'
    ).format(port)


EXTRACT_JS = r"""
(() => {
  const clean = (value) => (value || '').replace(/\s+/g, ' ').trim();
  const absolute = (value) => {
    try { return new URL(value, location.href).href; } catch (e) { return value || ''; }
  };
  const meta = (name) => {
    const el = document.querySelector(`meta[name="${name}"]`);
    return el ? (el.getAttribute('content') || '') : '';
  };
  const article =
    document.querySelector('article') ||
    document.querySelector('main') ||
    document.querySelector('[role="main"]') ||
    document.body;

  const figures = [];
  const seen = new Set();
  const add = (img, figureEl) => {
    if (!img) return;
    const rawSrc =
      img.currentSrc || img.src || img.getAttribute('data-src') ||
      img.getAttribute('data-original') || img.getAttribute('data-lazy-src') || '';
    const src = absolute(rawSrc);
    if (!src || seen.has(src)) return;
    seen.add(src);
    const captionEl =
      (figureEl && figureEl.querySelector('figcaption')) ||
      img.closest('figure')?.querySelector('figcaption') ||
      null;
    let caption = clean(captionEl ? captionEl.innerText : '');
    if (!caption) caption = clean(img.getAttribute('alt') || '');
    if (!caption && figureEl) caption = clean(figureEl.innerText || '');
    const linkEl = (figureEl && figureEl.querySelector('a[href]')) || img.closest('a[href]');
    const rect = (figureEl || img).getBoundingClientRect();
    figures.push({
      src: src,
      srcset: img.getAttribute('srcset') || '',
      data_src: img.getAttribute('data-src') || '',
      caption: caption,
      alt: img.getAttribute('alt') || '',
      link: linkEl ? absolute(linkEl.href || linkEl.getAttribute('href') || '') : '',
      width: img.naturalWidth || 0,
      height: img.naturalHeight || 0,
      in_figure: !!figureEl,
      rect: { width: rect.width || 0, height: rect.height || 0 },
      class_name: img.className || ''
    });
  };

  document.querySelectorAll('figure').forEach((figureEl) => {
    figureEl.querySelectorAll('img').forEach((img) => add(img, figureEl));
  });
  article.querySelectorAll('img').forEach((img) => {
    if (!img.closest('figure')) add(img, null);
  });

  return JSON.stringify({
    title: clean(meta('citation_title')) || clean(document.querySelector('h1')?.innerText) || clean(document.title),
    text: article.innerText || '',
    figures: figures,
    url: location.href,
    lang: document.documentElement.lang || '',
    site: meta('citation_journal_title') || meta('og:site_name') || '',
    doi: meta('citation_doi') || '',
    date: meta('citation_publication_date') || '',
    authors: Array.from(document.querySelectorAll('meta[name="citation_author"]')).map((el) => el.getAttribute('content') || ''),
    description: meta('description') || meta('og:description') || ''
  });
})()
"""


FETCH_IMAGE_JS = r"""
(async () => {
  try {
    const response = await fetch(%s, {credentials: 'include', referrer: location.href});
    if (!response.ok) {
      return JSON.stringify({ok: false, status: response.status});
    }
    const blob = await response.blob();
    const dataUrl = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
    return JSON.stringify({ok: true, mime: blob.type || '', data: dataUrl});
  } catch (error) {
    return JSON.stringify({ok: false, error: String(error)});
  }
})()
"""


class BrowserSession:
    """One temporary tab with one websocket connection."""

    def __init__(self, port: int = CDP_PORT, timeout: int = 45):
        self.port = port
        self.timeout = timeout
        self.target_id = None
        self.ws_url = None

    def __enter__(self):
        base = "http://127.0.0.1:{}".format(self.port)
        response = requests.put(base + "/json/new?about:blank", timeout=5)
        if not response.ok:
            response = requests.get(base + "/json/new?about:blank", timeout=5)
        if not response.ok:
            raise BrowserError("无法创建 Chrome 标签页: HTTP {}".format(response.status_code))
        payload = response.json()
        self.target_id = payload.get("id")
        self.ws_url = payload.get("webSocketDebuggerUrl")
        if not self.ws_url:
            raise BrowserError("Chrome 未返回 webSocketDebuggerUrl")
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.target_id:
            try:
                requests.get(
                    "http://127.0.0.1:{}/json/close/{}".format(self.port, self.target_id),
                    timeout=3,
                )
            except Exception:
                pass
        return False

    def extract(
        self,
        url: str,
        wait_seconds: float = 4.0,
        challenge_timeout: int = 45,
        max_figures: int = 30,
        max_image_bytes: int = 30_000_000,
    ) -> dict:
        return asyncio.run(
            self._extract_async(url, wait_seconds, challenge_timeout, max_figures, max_image_bytes)
        )

    async def _extract_async(self, url, wait_seconds, challenge_timeout, max_figures, max_image_bytes):
        try:
            import websockets
        except ImportError:
            raise BrowserError("缺少 websockets。请运行: pip install websockets")

        state = {"id": 0}

        async with websockets.connect(
            self.ws_url, max_size=None, open_timeout=15, close_timeout=5
        ) as websocket:

            async def send(method, params=None):
                state["id"] += 1
                message_id = state["id"]
                await websocket.send(
                    json.dumps({"id": message_id, "method": method, "params": params or {}})
                )
                while True:
                    raw = await asyncio.wait_for(websocket.recv(), timeout=self.timeout)
                    message = json.loads(raw)
                    if message.get("id") != message_id:
                        continue
                    if "error" in message:
                        raise BrowserError(
                            "CDP {} 失败: {}".format(method, message["error"])
                        )
                    return message.get("result", {})

            await send("Page.enable")
            navigation = await send("Page.navigate", {"url": url})
            if navigation.get("errorText"):
                raise BrowserError("页面导航失败: {}".format(navigation["errorText"]))

            deadline = time.time() + self.timeout
            while time.time() < deadline:
                result = await send(
                    "Runtime.evaluate",
                    {"expression": "document.readyState", "returnByValue": True},
                )
                if result.get("result", {}).get("value") == "complete":
                    break
                await asyncio.sleep(0.5)

            if wait_seconds:
                await asyncio.sleep(wait_seconds)

            async def page_title():
                result = await send(
                    "Runtime.evaluate",
                    {"expression": "document.title", "returnByValue": True},
                )
                return result.get("result", {}).get("value", "") or ""

            title = await page_title()
            challenge_markers = (
                "just a moment", "attention required", "checking your browser",
                "verify you are human", "enable javascript and cookies",
            )
            if any(marker in title.lower() for marker in challenge_markers):
                print(
                    "    [browser] 检测到人机验证，请在打开的 Chrome 窗口完成验证（最多等待 {} 秒）...".format(
                        challenge_timeout
                    )
                )
                challenge_deadline = time.time() + challenge_timeout
                while time.time() < challenge_deadline:
                    await asyncio.sleep(2)
                    title = await page_title()
                    if not any(marker in title.lower() for marker in challenge_markers):
                        break
                else:
                    raise BrowserChallenge(
                        "Cloudflare/人机验证未通过。请在 Chrome 窗口手动完成验证后重试，"
                        "或使用 --browser off 走 HTTP/PDF 回退。"
                    )

            result = await send(
                "Runtime.evaluate",
                {"expression": EXTRACT_JS, "returnByValue": True, "awaitPromise": True},
            )
            if result.get("exceptionDetails"):
                raise BrowserError("页面脚本执行失败: {}".format(result["exceptionDetails"]))
            value = result.get("result", {}).get("value")
            if not value:
                raise BrowserError("页面未返回可解析内容")
            page = json.loads(value)
            page["method"] = "browser"

            candidates = []
            for figure in page.get("figures", []):
                source = figure.get("src") or ""
                srcset_best = pick_srcset(figure.get("srcset", ""))
                link = figure.get("link") or ""
                chosen = upgrade_figure_url(source)
                if srcset_best:
                    chosen = upgrade_figure_url(srcset_best)
                if link and re.search(r"\.(png|jpe?g|gif|webp)(\?|$)", link, re.I):
                    if not srcset_best or "thumb" in source.lower():
                        chosen = upgrade_figure_url(link)
                figure["source_url"] = chosen
                figure["caption"] = re.sub(r"\s+", " ", figure.get("caption") or "").strip()
                candidates.append(figure)

            # Deduplicate by final URL.
            deduped = {}
            for figure in candidates:
                key = figure.get("source_url") or ""
                if key and key not in deduped:
                    deduped[key] = figure
            candidates = list(deduped.values())[:max_figures]

            for figure in candidates:
                source_url = figure.get("source_url") or ""
                if source_url.startswith("data:"):
                    try:
                        header, encoded = source_url.split(",", 1)
                        mime = header.split(";")[0].split(":", 1)[1]
                        figure["data"] = base64.b64decode(encoded)
                        figure["mime"] = mime
                    except Exception as exc:
                        figure["fetch_error"] = str(exc)
                    continue
                if not source_url:
                    figure["fetch_error"] = "empty source"
                    continue
                expression = FETCH_IMAGE_JS % json.dumps(source_url)
                try:
                    fetched = await send(
                        "Runtime.evaluate",
                        {"expression": expression, "awaitPromise": True, "returnByValue": True},
                    )
                    payload = json.loads(fetched.get("result", {}).get("value") or "{}")
                    if not payload.get("ok"):
                        figure["fetch_error"] = payload.get("error") or "HTTP {}".format(payload.get("status"))
                        continue
                    data_url = payload.get("data") or ""
                    if len(data_url) > max_image_bytes * 4 // 3:
                        figure["fetch_error"] = "image too large"
                        continue
                    header, encoded = data_url.split(",", 1)
                    figure["data"] = base64.b64decode(encoded)
                    figure["mime"] = payload.get("mime") or ""
                except Exception as exc:
                    figure["fetch_error"] = str(exc)

            page["figures"] = candidates
            return page
