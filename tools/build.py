#!/usr/bin/env python3
"""Regenerate every data file, then validate and minify.

    python3 tools/build.py

Network access is required; responses are cached under tools/.cache for a day.
The order matters: countries.json is the cross-reference target for the other
three generators.
"""
import subprocess
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = [
    ("enrich_countries.py", "countries"),
    ("gen_currencies.py", "currencies"),
    ("gen_languages.py", "languages"),
    ("gen_timezones.py", "timezones"),
    ("minify.py", "minified twins"),
    ("validate.py", "validation"),
]


def main():
    for script, label in STEPS:
        print(f"\n== {label} ({script})")
        result = subprocess.run([sys.executable, os.path.join(HERE, script)], cwd=HERE)
        if result.returncode != 0:
            print(f"\n{script} failed with exit code {result.returncode}")
            return result.returncode
    print("\nAll data files regenerated and validated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
