# Standalone Cambridge Scraper (Termux / Python)

This repository's Cambridge dictionary logic was originally designed for the Anki
addon environment. If you want to run it on a normal Python device (including Termux),
use the standalone script below.

## Requirements

```bash
pip install requests beautifulsoup4
```

## Usage

```bash
python scripts/standalone_cambridge.py test --pretty
```

### Language Options

- `en`: English-English
- `en-zh-s`: English → Simplified Chinese
- `en-zh-t`: English → Traditional Chinese

Example:

```bash
python scripts/standalone_cambridge.py test --lang en-zh-s --pretty
```

## Output

The script prints JSON with:

- `pronunciation.AmE` / `pronunciation.BrE`
- `pronunciation.AmEmp3` / `pronunciation.BrEmp3` (audio URLs)
- `definitions` (plain text list)
- `image` / `thumb` (image URLs if present)

Note: The output is text-focused (no Anki HTML/media tags). It is intended for CLI use
and simple integrations.
