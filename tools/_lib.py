"""Shared helpers for the data generators in this repository.

Every generator is offline-deterministic apart from the network fetches it
declares here, and every fetch is cached under tools/.cache so that a rerun
does not hammer the upstream services.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

UA = "andreaskasper-assets-datagen/1.0 (+https://github.com/andreaskasper/assets)"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
CACHE = os.path.join(ROOT, "tools", ".cache")

WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"


def _cache_path(name):
    os.makedirs(CACHE, exist_ok=True)
    return os.path.join(CACHE, name)


def fetch(url, name, binary=False, max_age=86400):
    """GET *url*, caching the body under tools/.cache/<name>."""
    path = _cache_path(name)
    if os.path.exists(path) and (time.time() - os.path.getmtime(path)) < max_age:
        mode = "rb" if binary else "r"
        with open(path, mode, **({} if binary else {"encoding": "utf-8"})) as fh:
            return fh.read()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=180) as resp:
        raw = resp.read()
    with open(path, "wb") as fh:
        fh.write(raw)
    return raw if binary else raw.decode("utf-8")


def fetch_json(url, name, max_age=86400):
    return json.loads(fetch(url, name, max_age=max_age))


def sparql(query, name, tries=4):
    """Run a SPARQL query against Wikidata and return the result bindings."""
    path = _cache_path(name)
    if os.path.exists(path) and (time.time() - os.path.getmtime(path)) < 86400:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    url = WIKIDATA_SPARQL + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "application/sparql-results+json"}
    )
    last = None
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                rows = json.load(resp)["results"]["bindings"]
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(rows, fh)
            return rows
        except Exception as exc:  # noqa: BLE001 - retry any transport error
            last = exc
            sys.stderr.write(f"  wikidata retry {attempt + 1}/{tries}: {exc}\n")
            time.sleep(5 * (attempt + 1))
    raise SystemExit(f"SPARQL query {name} failed: {last}")


def binding(row, key):
    """Read one value out of a SPARQL binding row, or None."""
    cell = row.get(key)
    if not cell:
        return None
    value = cell["value"]
    return value.rsplit("/", 1)[-1] if cell["type"] == "uri" else value


# Each data file keeps the indentation it was originally committed with, so
# that a regeneration produces a content diff rather than a whitespace diff.
INDENT = {"countries.json": 4, "timezones.json": 4}


def write_json(relpath, payload, sort_keys=False, indent=None):
    """Write *payload* to data/<relpath> in the repository's house format."""
    path = os.path.join(DATA, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    indent = indent if indent is not None else INDENT.get(os.path.basename(relpath), 2)
    text = json.dumps(payload, ensure_ascii=False, indent=indent, sort_keys=sort_keys)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(f"  wrote data/{relpath}  ({len(text) + 1:,} bytes)")
    return path


def read_json(relpath):
    with open(os.path.join(DATA, relpath), encoding="utf-8") as fh:
        return json.load(fh)
