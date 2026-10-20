#!/usr/bin/env python3
"""Capture a JavaScript-rendered Kimi biology outline page as Markdown.

Usage:
  python -m pip install playwright
  python -m playwright install chromium
  python scripts/scrape_kimi_biology_outline.py

The script intentionally saves rendered page text rather than claiming to
reconstruct hidden application data. Review the output for navigation
duplicates, truncation notices, missing sections, or failed expansion.
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
    """Trim boilerplate and collapse excessive blank lines without deleting content."""
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
    """Promote obvious numbered module headings while preserving other lines."""
    converted: list[str] = []
    numbered_heading = re.compile(r"^(\d+(?:\.\d+){0,3})[.、]?\s+(.+)$")
    for line in lines:
        match = numbered_heading.match(line)
        if match:
            depth = match.group(1).count(".") + 2
            depth = min(depth, 6)
            converted.append("#" * depth + " " + line)
        elif line in {"目录导航", "高考生物考纲详解"}:
            converted.append("## " + line)
        else:
            converted.append(line)
    return "\n".join(converted).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help="Target page URL")
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Markdown output path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=60000,
        help="Navigation timeout in milliseconds",
    )
    args = parser.parse_args()

    page_title = ""
    page_url = args.url
    page_text = ""
    expansion_note = "未确认是否成功展开全部节点。"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        try:
            page.goto(
                args.url,
                wait_until="domcontentloaded",
                timeout=args.timeout_ms,
            )
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except PlaywrightTimeoutError:
                # Some single-page applications keep network connections open.
                pass
            page.wait_for_timeout(1500)

            page_title = page.title().strip()
            page_url = page.url

            # The page currently displays a "全部展开" control in its index.
            expand = page.get_by_role("button", name=re.compile("全部展开"))
            try:
                if expand.count() > 0:
                    expand.first.click(timeout=5000)
                    page.wait_for_timeout(1200)
                    expansion_note = "已点击“全部展开”控件；请检查输出确认所有内容确实展开。"
                else:
                    expansion_note = "未发现“全部展开”按钮；已保存当前浏览器可见文本。"
            except PlaywrightTimeoutError:
                expansion_note = "发现展开控件但点击超时；已保存当前浏览器可见文本。"

            page_text = page.locator("body").inner_text(timeout=10000)
        except Exception as exc:  # noqa: BLE001 - record the browser failure for diagnosis
            print(f"抓取失败：{type(exc).__name__}: {exc}", file=sys.stderr)
            browser.close()
            return 2
        finally:
            browser.close()

    lines = clean_lines(page_text)
    body = convert_to_markdown(lines)
    captured_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    header = (
        "# 高考生物考纲详解：浏览器渲染文本捕获\n\n"
        f"- Source URL: {page_url}\n"
        f"- Page title: {page_title or '(title unavailable)'}\n"
        f"- Captured at: {captured_at}\n"
        f"- Expansion: {expansion_note}\n"
        "- Capture mode: Playwright Chromium; this is rendered text, not a byte-for-byte HTML archive.\n\n"
        "> Review this artifact before treating it as complete. If the page uses lazy loading, "
        "pagination, virtualized lists, or nested accordions, expand/scroll through all sections "
        "and compare the resulting headings with the site's navigation.\n\n"
        "---\n\n"
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(header + body, encoding="utf-8")
    print(f"已保存：{output.resolve()}")
    print(f"文本行数：{len(lines)}")
    print(f"标题：{page_title or '(title unavailable)'}")
    print(f"展开状态：{expansion_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
