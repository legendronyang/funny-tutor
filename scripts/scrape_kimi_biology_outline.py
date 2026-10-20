#!/usr/bin/env python3
"""Capture a JavaScript-rendered biology outline site as Markdown.

Install and run:
  python -m pip install playwright
  python -m playwright install chromium
  python scripts/scrape_kimi_biology_outline.py

When the site does not load in headless mode, use --headed to inspect it.
This captures browser-rendered text; it does not recover data hidden behind
authentication, failed network requests, or inaccessible application APIs.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

DEFAULT_URL = "https://nuxaap6e7b46i.ok.kimi.link/"
DEFAULT_OUTPUT = "docs/gaokao-biology-kimi-site-capture.md"


def clean_lines(text: str) -> list[str]:
    """Normalize whitespace and remove only obvious standalone UI controls."""
    result: list[str] = []
    previous_blank = False
    skip_exact = {
        "☰",
        "🔍",
        "◀",
        "▶",
        "✕",
        "全部展开",
        "全部收起",
        "搜索导航...",
        "搜索页面内容...",
    }
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw.strip()
        if line in skip_exact:
            continue
        if not line:
            if result and not previous_blank:
                result.append("")
            previous_blank = True
            continue
        result.append(line)
        previous_blank = False
    while result and not result[-1]:
        result.pop()
    return result


def convert_to_markdown(lines: list[str]) -> str:
    """Promote numbered outline rows to headings while preserving their labels."""
    converted: list[str] = []
    numbered_heading = re.compile(r"^(\d+(?:\.\d+){0,3})[.、]?\s+(.+)$")
    for line in lines:
        match = numbered_heading.match(line)
        if match:
            depth = min(match.group(1).count(".") + 2, 6)
            converted.append("#" * depth + " " + line)
        elif line in {"目录导航", "高考生物考纲详解"}:
            converted.append("## " + line)
        else:
            converted.append(line)
    return "\n".join(converted).strip() + "\n"


def click_expand_all(page) -> str:
    """Try common button and text locators, without toggling each nested row."""
    candidates = [
        page.get_by_role("button", name=re.compile("全部展开")),
        page.get_by_text("全部展开", exact=True),
    ]
    for locator in candidates:
        try:
            count = locator.count()
            for index in range(min(count, 5)):
                item = locator.nth(index)
                if item.is_visible():
                    item.click(timeout=4000)
                    page.wait_for_timeout(1200)
                    return "已点击“全部展开”；仍需检查输出是否覆盖所有节点。"
        except PlaywrightTimeoutError:
            continue
        except Exception:
            continue
    return "未能确认“全部展开”控件可用；已尝试保存可见文本。"


def scroll_for_lazy_content(page, max_rounds: int = 16) -> str:
    """Scroll progressively so pages that load sections on demand get a chance to render."""
    stable_rounds = 0
    previous_height = -1
    try:
        for _ in range(max_rounds):
            height = page.evaluate(
                "() => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)"
            )
            page.evaluate("() => window.scrollBy(0, Math.max(window.innerHeight, 700))")
            page.wait_for_timeout(350)
            new_height = page.evaluate(
                "() => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)"
            )
            if new_height == previous_height == height:
                stable_rounds += 1
            else:
                stable_rounds = 0
            previous_height = new_height
            if stable_rounds >= 3:
                break
        page.evaluate("() => window.scrollTo(0, 0)")
        page.wait_for_timeout(250)
        return f"已执行懒加载滚动检查（最多 {max_rounds} 轮）。"
    except Exception as exc:
        return f"滚动检查未完成：{type(exc).__name__}: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help="Target page URL")
    parser.add_argument(
        "--output", default=DEFAULT_OUTPUT, help=f"Markdown path (default: {DEFAULT_OUTPUT})"
    )
    parser.add_argument("--timeout-ms", type=int, default=60000, help="Navigation timeout")
    parser.add_argument("--headed", action="store_true", help="Show Chromium UI for debugging")
    args = parser.parse_args()

    page_title = ""
    page_url = args.url
    page_text = ""
    capture_notes: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headed)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.set_default_timeout(10000)
        try:
            response = page.goto(
                args.url,
                wait_until="domcontentloaded",
                timeout=args.timeout_ms,
            )
            status = response.status if response else "no response object"
            capture_notes.append(f"HTTP status: {status}")
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except PlaywrightTimeoutError:
                capture_notes.append("networkidle 未达成（SPA 或长连接可能导致），继续抓取 DOM。")
            page.wait_for_timeout(1500)

            page_title = page.title().strip()
            page_url = page.url
            capture_notes.append(click_expand_all(page))
            capture_notes.append(scroll_for_lazy_content(page))
            page_text = page.locator("body").inner_text(timeout=15000)
        except Exception as exc:  # noqa: BLE001 - report browser failures to the caller
            print(f"抓取失败：{type(exc).__name__}: {exc}", file=sys.stderr)
            try:
                screenshot = Path("/tmp/kimi-biology-capture-error.png")
                page.screenshot(path=str(screenshot), full_page=True)
                print(f"诊断截图：{screenshot}", file=sys.stderr)
            except Exception:
                pass
            return 2
        finally:
            browser.close()

    lines = clean_lines(page_text)
    body = convert_to_markdown(lines)
    captured_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    header = (
        "# 高考生物考纲详解：浏览器渲染文本捕获\n\n"
        f"- 来源 URL：{page_url}\n"
        f"- 页面标题：{page_title or '（无法读取）'}\n"
        f"- 捕获时间：{captured_at}\n"
        + "".join(f"- 抓取记录：{note}\n" for note in capture_notes)
        + "- 抓取方式：Playwright Chromium 读取渲染后的页面文本；不是逐字节 HTML 镜像。\n\n"
        + "> 完整性检查：确认所有目录节点均已展开；核对最末模块与子模块编号；检查是否存在分页、"
        + "虚拟列表、登录限制或加载失败。如果输出不完整，可运行 --headed 观察页面并调整脚本。\n\n"
        + "---\n\n"
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(header + body, encoding="utf-8")
    print(f"已保存：{output.resolve()}")
    print(f"文本行数：{len(lines)}")
    print(f"页面标题：{page_title or '（无法读取）'}")
    for note in capture_notes:
        print(f"- {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
