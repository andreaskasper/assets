#!/usr/bin/env python3
"""Write a minified twin for every data/*.json file.

The pretty-printed file is the one that is edited and reviewed; the .min.json
is what production should load. Regenerating is idempotent, and CI fails if the
two ever drift apart.
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def minified(path):
    with open(path, encoding="utf-8") as fh:
        return json.dumps(json.load(fh), ensure_ascii=False, separators=(",", ":")) + "\n"


def main(check_only=False):
    stale = []
    for path in sorted(glob.glob(os.path.join(DATA, "*.json"))):
        if path.endswith(".min.json"):
            continue
        target = path[: -len(".json")] + ".min.json"
        text = minified(path)
        current = None
        if os.path.exists(target):
            with open(target, encoding="utf-8") as fh:
                current = fh.read()
        if current == text:
            continue
        if check_only:
            stale.append(os.path.basename(target))
            continue
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(text)
        saved = 100 - (len(text.encode()) * 100 // max(os.path.getsize(path), 1))
        print(f"  {os.path.basename(target):32} {len(text.encode()):>9,} bytes  (-{saved}%)")
    if stale:
        print("Minified files are out of date; run tools/minify.py:")
        for name in stale:
            print(f"  - {name}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(check_only="--check" in sys.argv))
