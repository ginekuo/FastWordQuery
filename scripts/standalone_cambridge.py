#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Standalone Cambridge Dictionary scraper.

Dependencies:
  - requests
  - beautifulsoup4

Example:
  python scripts/standalone_cambridge.py test
  python scripts/standalone_cambridge.py test --lang en-zh-s
"""

import argparse
import json
import re
from typing import Dict, List, Optional

import requests
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


def fetch_html(url: str, timeout: int = 10) -> str:
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.text


def extract_definitions(sense_body: Tag, pos_gram: str, runon_title: Optional[str]) -> List[str]:
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
        def_info = def_info_tag.get_text().replace("›", "") if def_info_tag else ""
        definition = block.find("div", class_="def")
        translation = block.find("span", class_="trans")
        examples = block.find_all("div", class_="examp dexamp")

        parts = [
            f"[{pos_gram}]" if pos_gram else "",
            f"[{runon_title}]" if runon_title else "",
            f"[{phrase}]" if phrase else "",
            f"[{def_info.strip()}]" if def_info.strip() else "",
            definition.get_text() if definition else "",
            translation.get_text() if translation else "",
        ]
        example_text = " ".join(e.get_text() for e in examples if e)
        if example_text:
            parts.append(example_text)

        items.append(" ".join(p for p in parts if p))

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
            if sense_body:
                result["definitions"].extend(extract_definitions(sense_body, pos_gram, runon_title))

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
    args = parser.parse_args()

    url = build_url(args.word, args.lang)
    html = fetch_html(url)
    is_english = args.lang == "en"
    data = parse_cambridge(html, is_english)
    data["word"] = args.word
    data["url"] = url

    if args.pretty:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(data, ensure_ascii=False))


if __name__ == "__main__":
    main()
