#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Standalone Cambridge Dictionary scraper.

Dependencies:
  - beautifulsoup4

Example:
  python scripts/standalone_cambridge.py test
  python scripts/standalone_cambridge.py test --lang en-zh-s
"""

import argparse
import gzip
import importlib.util
import json
import re
from typing import Dict, List, Optional
from urllib import request

if importlib.util.find_spec("bs4") is None:
    raise SystemExit("Missing dependency: beautifulsoup4. Install with `pip install beautifulsoup4`.")

from bs4 import BeautifulSoup, Tag

CAMBRIDGE_BASE = "https://dictionary.cambridge.org/"
LANG_URLS = {
    "en": "https://dictionary.cambridge.org/dictionary/english/",
    "en-zh-s": "https://dictionary.cambridge.org/us/dictionary/english-chinese-simplified/",
    "en-zh-t": "https://dictionary.cambridge.org/us/dictionary/english-chinese-traditional/",
}
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 6.1; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/70.0.3538.67 Safari/537.36"
    )
}


def normalize_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    return text

DEFAULT_CSS = """
body {
  font-family: "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  margin: 32px;
  color: #0f172a;
  background: #f1f5f9;
}
.card {
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.12);
  padding: 28px 32px;
  max-width: 980px;
  margin: 0 auto;
  border: 1px solid #e2e8f0;
}
.header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
}
.word {
  font-size: 36px;
  font-weight: 750;
  color: #0b1220;
  letter-spacing: 0.3px;
}
.meta {
  font-size: 13px;
  color: #64748b;
}
.meta a {
  color: #2563eb;
  text-decoration: none;
}
.meta a:hover {
  text-decoration: underline;
}
.pron {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 12px;
  font-size: 15px;
}
.pron span {
  background: #e0f2fe;
  padding: 6px 12px;
  border-radius: 999px;
  color: #0f172a;
  border: 1px solid #bae6fd;
}
.section {
  margin-top: 24px;
}
.section-title {
  font-size: 18px;
  font-weight: 650;
  margin-bottom: 12px;
  color: #1e3a8a;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.definitions {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 12px;
}
.definition {
  background: #f8fafc;
  border-radius: 12px;
  padding: 14px 16px;
  line-height: 1.6;
  border: 1px solid #e2e8f0;
  display: grid;
  gap: 6px;
}
.definition-header {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.tag {
  background: #ede9fe;
  color: #5b21b6;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid #ddd6fe;
}
.definition-text {
  font-size: 15px;
  color: #0f172a;
  white-space: pre-line;
}
.definition-index {
  font-weight: 700;
  color: #1d4ed8;
  font-size: 13px;
  margin-right: 6px;
}
.media {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}
.media img {
  max-width: 240px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #fff;
}
.grid {
  display: grid;
  gap: 12px;
}
.footer {
  margin-top: 16px;
  font-size: 12px;
  color: #94a3b8;
}
"""


def render_html(data: Dict[str, object], css_path: Optional[str]) -> str:
    pronunciations = data.get("pronunciation", {})
    defs = data.get("definitions", [])
    image_url = data.get("image")
    thumb_url = data.get("thumb")
    word = data.get("word", "")
    url = data.get("url", "")

    css_tag = (
        f'<link rel="stylesheet" href="{css_path}">' if css_path else "<style>" + DEFAULT_CSS + "</style>"
    )

    def format_definition(index: int, definition: str) -> str:
        tag_match = re.match(r"^((?:\\[[^\\]]+\\]\\s*)+)(.*)$", definition)
        tags_html = ""
        main_text = definition.strip()
        if tag_match:
            tags = re.findall(r"\\[([^\\]]+)\\]", tag_match.group(1))
            tags_html = "".join(f"<span class=\"tag\">{tag}</span>" for tag in tags)
            main_text = tag_match.group(2).strip()
        header_html = (
            f"<div class=\"definition-header\">"
            f"<span class=\"definition-index\">{index:02d}</span>{tags_html}</div>"
            if tags_html
            else f"<div class=\"definition-header\"><span class=\"definition-index\">{index:02d}</span></div>"
        )
        return (
            "<li class=\"definition\">"
            f"{header_html}"
            f"<div class=\"definition-text\">{main_text or 'No definition text.'}</div>"
            "</li>"
        )

    if defs:
        def_list = "\n".join(format_definition(i + 1, definition) for i, definition in enumerate(defs))
    else:
        def_list = "<li class=\"definition\"><div class=\"definition-text\">No definitions found.</div></li>"

    media_parts = []
    if thumb_url:
        media_parts.append(f'<img src="{thumb_url}" alt="Thumbnail">')
    if image_url and image_url != thumb_url:
        media_parts.append(f'<img src="{image_url}" alt="Image">')
    media_html = "\n".join(media_parts) if media_parts else "<div class=\"meta\">No images available.</div>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Cambridge: {word}</title>
  {css_tag}
</head>
<body>
  <div class="card">
    <div class="header">
      <div class="word">{word}</div>
      <div class="meta"><a href="{url}">{url}</a></div>
    </div>
    <div class="pron">
      <span>AmE: {pronunciations.get("AmE", "")}</span>
      <span>BrE: {pronunciations.get("BrE", "")}</span>
    </div>
    <div class="section">
      <div class="section-title">📘 Definitions</div>
      <ul class="definitions">
        {def_list}
      </ul>
    </div>
    <div class="section">
      <div class="section-title">🖼️ Images</div>
      <div class="media">
        {media_html}
      </div>
    </div>
    <div class="footer">Generated by standalone_cambridge.py</div>
  </div>
</body>
</html>
"""


def fetch_html(url: str, timeout: int = 10) -> str:
    req = request.Request(url, headers=DEFAULT_HEADERS)
    with request.urlopen(req, timeout=timeout) as response:
        data = response.read()
        if response.headers.get("Content-Encoding") == "gzip":
            data = gzip.decompress(data)
        return data.decode("utf-8", errors="ignore")


def extract_definitions(
    sense_body: Tag,
    pos_gram: str,
    runon_title: Optional[str],
    guideword: Optional[str],
    guideword_provider=None,
) -> List[str]:
    items: List[str] = []

    def extract_sense(block: Tag, phrase: Optional[str] = None) -> None:
        if not isinstance(block, Tag):
            return

        block_type = block.get("class", [""])[0]
        if block_type == "def-block":
            pass
        elif block_type == "phrase-block":
            phrase_header = block.find("span", class_="phrase-head")
            phrase_body = block.find("div", class_="phrase-body pad-indent")
            if phrase_body:
                for phrase_block in phrase_body:
                    extract_sense(phrase_block, phrase_header.get_text() if phrase_header else None)
            return
        elif block_type == "runon-body":
            pass
        else:
            return

        def_info_tag = block.find("span", class_="def-info")
        def_info = (
            normalize_text(def_info_tag.get_text(" ", strip=True).replace("›", ""))
            if def_info_tag
            else ""
        )
        label_tags = []
        for label in block.find_all("span", class_="lab"):
            if label.get_text(strip=True):
                label_tags.append(label.get_text(strip=True))
        if not label_tags:
            parent_block = block.find_parent("div", class_="pr")
            if parent_block:
                for label in parent_block.find_all("span", class_="lab"):
                    if label.get_text(strip=True):
                        label_tags.append(label.get_text(strip=True))
        definition = block.find("div", class_="def")
        translation = block.find("span", class_="trans")
        examples = block.find_all("div", class_="examp dexamp")

        guideword_for_block = guideword
        parent_dsense = block.find_parent("div", class_=lambda c: c and "dsense" in c)
        if parent_dsense:
            guideword_tag = parent_dsense.find("span", class_="guideword")
            if guideword_tag:
                guideword_for_block = normalize_text(guideword_tag.get_text(" ", strip=True))
        if not guideword_for_block and guideword_provider:
            guideword_for_block = guideword_provider()

        tags = [
            pos_gram,
            runon_title,
            phrase,
            guideword_for_block,
            def_info.strip(),
            *label_tags,
        ]
        tag_text = " ".join(f"[{tag}]" for tag in tags if tag)
        main_text_parts = []
        if definition and definition.get_text(" ", strip=True):
            main_text_parts.append(normalize_text(definition.get_text(" ", strip=True)))
        if translation and translation.get_text(" ", strip=True):
            main_text_parts.append(normalize_text(translation.get_text(" ", strip=True)))

        example_lines = [
            f"- {normalize_text(e.get_text(' ', strip=True))}"
            for e in examples
            if e and e.get_text(" ", strip=True)
        ]
        text_blocks = [" ".join(main_text_parts).strip()] if main_text_parts else []
        text_blocks.extend(example_lines)

        definition_text = "\n".join(text_blocks).strip()
        full_text = " ".join(part for part in [tag_text, definition_text] if part)
        items.append(full_text)

    for block in sense_body:
        extract_sense(block)

    return items


def parse_cambridge(html: str, is_english: bool) -> Dict[str, object]:
    soup = BeautifulSoup(html, "html.parser")
    result: Dict[str, object] = {
        "pronunciation": {"AmE": "", "BrE": "", "AmEmp3": "", "BrEmp3": ""},
        "image": "",
        "thumb": "",
        "definitions": [],
    }

    page_class = "page" if is_english else "di-body"
    element = soup.find("div", class_=page_class)
    if not element:
        return result

    elements = element.find_all("div", class_="entry-body__el")
    guidewords = [
        normalize_text(tag.get_text(" ", strip=True))
        for tag in element.find_all("span", class_="guideword")
        if tag.get_text(strip=True)
    ]
    guideword_index = 0

    def next_guideword():
        nonlocal guideword_index
        if guideword_index < len(guidewords):
            value = guidewords[guideword_index]
            guideword_index += 1
            return value
        return None
    header_found = False
    for entry in elements:
        if not entry:
            continue
        if not header_found:
            header = entry.find("div", class_="pos-header")
            if header:
                tags = header.find_all("span", class_="dpron-i")
                for tag in tags:
                    region = tag.find("span", class_="region")
                    reg = region.get_text() if region else ""
                    pronunciation_key = "AmE" if reg == "us" else "BrE"
                    pron = tag.find("span", class_="pron")
                    result["pronunciation"][pronunciation_key] = pron.get_text() if pron else ""
                    source = tag.find("source", type="audio/mpeg")
                    if source and source.get("src"):
                        result["pronunciation"][pronunciation_key + "mp3"] = (
                            CAMBRIDGE_BASE + source.get("src")
                        )
                header_found = True

        senses = entry.find_all("div", class_="pos-body")
        span_posgram = entry.find("div", class_="posgram")
        pos_gram = span_posgram.get_text() if span_posgram else ""

        for sense in senses:
            runon_title = None
            if sense.get("class", [""])[0] == "runon":
                runon_pos = sense.find("span", class_="pos")
                runon_gram = sense.find("span", class_="gram")
                if runon_pos is not None:
                    pos_gram = runon_pos.get_text() + (runon_gram.get_text() if runon_gram else "")
                runon_header = sense.find("h3", class_="runon-title")
                runon_title = runon_header.get_text() if runon_header else None

            sense_body = sense.find("div", class_=re.compile("sense-body|runon-body pad-indent"))
            guideword = None
            guideword_tags = sense.find_all("span", class_="guideword")
            if len(guideword_tags) == 1:
                guideword = normalize_text(guideword_tags[0].get_text(" ", strip=True))
            if sense_body:
                result["definitions"].extend(
                    extract_definitions(
                        sense_body,
                        pos_gram,
                        runon_title,
                        guideword,
                        guideword_provider=next_guideword,
                    )
                )

            image = sense.find("img", class_="lightboxLink")
            if image:
                if image.get("data-image"):
                    result["image"] = CAMBRIDGE_BASE + image.get("data-image")
                if image.get("src"):
                    result["thumb"] = CAMBRIDGE_BASE + image.get("src")

    return result


def build_url(word: str, lang: str) -> str:
    base = LANG_URLS.get(lang)
    if not base:
        raise ValueError(f"Unsupported language key: {lang}")
    return f"{base}{word}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Standalone Cambridge Dictionary scraper")
    parser.add_argument("word", help="Word to query")
    parser.add_argument(
        "--lang",
        default="en",
        choices=sorted(LANG_URLS.keys()),
        help="Dictionary language (default: en)",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument("--html-out", help="Write a styled HTML file to this path")
    parser.add_argument("--css-out", help="Write CSS to this path (used by HTML output)")
    args = parser.parse_args()

    url = build_url(args.word, args.lang)
    html = fetch_html(url)
    is_english = args.lang == "en"
    data = parse_cambridge(html, is_english)
    data["word"] = args.word
    data["url"] = url

    if args.html_out:
        css_path = None
        if args.css_out:
            with open(args.css_out, "w", encoding="utf-8") as css_file:
                css_file.write(DEFAULT_CSS.strip() + "\n")
            css_path = args.css_out
        html_content = render_html(data, css_path)
        with open(args.html_out, "w", encoding="utf-8") as html_file:
            html_file.write(html_content)

    if args.pretty:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(data, ensure_ascii=False))


if __name__ == "__main__":
    main()
