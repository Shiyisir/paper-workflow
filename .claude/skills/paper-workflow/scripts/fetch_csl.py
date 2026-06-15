#!/usr/bin/env python3
"""Download official CSL citation style files from citationstyles.org.

Usage:
    python scripts/fetch_csl.py gb-t-7714
    python scripts/fetch_csl.py apa
    python scripts/fetch_csl.py chicago
    python scripts/fetch_csl.py --all
"""

import argparse
import sys
from pathlib import Path
from urllib.request import urlretrieve

CSL_BASE = "https://raw.githubusercontent.com/citation-style-language/styles/master"
CSL_DIR = Path(__file__).resolve().parent.parent / "templates" / "csl"

STYLES = {
    "gb-t-7714": {
        "url": f"{CSL_BASE}/gb-t-7714-2015-numeric.csl",
        "file": "gb-t-7714.csl",
    },
    "apa": {
        "url": f"{CSL_BASE}/apa.csl",
        "file": "apa.csl",
    },
    "chicago": {
        "url": f"{CSL_BASE}/chicago-author-date.csl",
        "file": "chicago.csl",
    },
}


def fetch_style(key: str) -> bool:
    info = STYLES[key]
    dest = CSL_DIR / info["file"]
    try:
        print(f"Downloading {info['url']} ...")
        urlretrieve(info["url"], dest)
        print(f"  [OK] saved to {dest}")
        return True
    except Exception as e:
        print(f"  [FAIL] failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Download CSL citation style files")
    parser.add_argument("style", nargs="?", choices=list(STYLES.keys()),
                        help="Style to download")
    parser.add_argument("--all", action="store_true",
                        help="Download all available styles")
    args = parser.parse_args()

    CSL_DIR.mkdir(parents=True, exist_ok=True)

    if args.all:
        results = {k: fetch_style(k) for k in STYLES}
        success = sum(results.values())
        print(f"\nDownloaded {success}/{len(results)} styles")
        return 0 if success == len(results) else 1

    if args.style:
        return 0 if fetch_style(args.style) else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
