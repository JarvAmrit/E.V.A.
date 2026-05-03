"""
Playwright-based browser tool for E.V.A.

browse_url(url)    → {"text": ..., "screenshot": <path>, "url": url}
summarize_page(url, llm_client) → str  (LLM summary of page content)

Requires:
  pip install playwright
  playwright install chromium
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def browse_url(url: str) -> dict[str, str]:
    """Open *url* with a headless Chromium browser.

    Returns a dict with:
      - ``text``       – visible text extracted from the page
      - ``screenshot`` – absolute path to a PNG screenshot
      - ``url``        – the final URL after redirects
    """
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "playwright is required for web browsing. "
            "Install with: pip install playwright && playwright install chromium"
        ) from exc

    logger.info("Browsing URL: %s", url)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=30_000, wait_until="domcontentloaded")

        # Extract visible text
        text: str = page.evaluate(
            """() => {
                const el = document.body;
                return el ? el.innerText : '';
            }"""
        )

        # Screenshot
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        page.screenshot(path=tmp.name, full_page=False)
        screenshot_path = tmp.name

        final_url: str = page.url
        browser.close()

    # Trim text to a reasonable size for the LLM context
    trimmed = text[:8000] if len(text) > 8000 else text
    logger.info("Browsed %s → %d chars of text", final_url, len(trimmed))
    return {"text": trimmed, "screenshot": screenshot_path, "url": final_url}


def summarize_page(url: str, openai_client: Any) -> str:
    """Browse *url* and return a concise LLM summary."""
    result = browse_url(url)
    page_text = result["text"]

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Summarise the following web page content concisely in 3–5 sentences.",
            },
            {"role": "user", "content": page_text[:6000]},
        ],
        max_tokens=300,
    )
    summary: str = response.choices[0].message.content.strip()
    logger.info("Summarised %s", url)
    return summary
