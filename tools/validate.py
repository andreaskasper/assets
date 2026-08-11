#!/usr/bin/env python3
"""Validate every file in data/. Exits non-zero on the first failure.

This is what the CI workflow runs on each push. It is deliberately strict about
the things that have gone wrong in this repository before: a language code used
where a country code belongs, a border that only one of the two countries knows
about, and currency codes that quietly stopped existing.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

ERRORS = []
CHECKS = 0


def check(condition, message):
    global CHECKS
    CHECKS += 1
    if not condition:
        ERRORS.append(message)
    return condition


def load(name):
    path = os.path.join(DATA, name)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        ERRORS.append(f"{name}: invalid JSON - {exc}")
        raise SystemExit(report())


def report():
    if ERRORS:
        print(f"\nFAILED - {len(ERRORS)} problem(s) out of {CHECKS} checks:\n")
        for err in ERRORS:
            print(f"  - {err}")
        return 1
    print(f"\nOK - {CHECKS} checks passed.")
    return 0


def main():
    countries = load("countries.json")
    currencies = load("currencies.json")
    languages = load("languages.json")
    zones = load("timezones.json")
    zones_detailed = load("timezones_detailed.json")

    # ---- countries -------------------------------------------------------
    check(isinstance(countries, list), "countries.json must be a JSON array")
    by_cca3 = {}
    for c in countries:
        code = c.get("cca3")
        check(bool(code) and re.fullmatch(r"[A-Z]{3}", code or ""),
              f"countries.json: bad cca3 {code!r}")
        check(code not in by_cca3, f"countries.json: duplicate cca3 {code}")
        by_cca3[code] = c
        check(bool(re.fullmatch(r"[A-Z]{2}", c.get("cca2") or "")),
              f"{code}: bad cca2 {c.get('cca2')!r}")
        check(bool(re.fullmatch(r"\d{3}", c.get("ccn3") or "")) or c.get("status") == "user-assigned",
              f"{code}: bad ccn3 {c.get('ccn3')!r}")
        check(isinstance(c.get("latlng"), list) and len(c["latlng"]) == 2,
              f"{code}: latlng must hold two numbers")

    check(sorted(by_cca3) == [c["cca3"] for c in countries],
          "countries.json must be sorted by cca3")

    # borders must be real countries, and must be mutual
    for c in countries:
        for other in c.get("borders") or []:
            if not check(other in by_cca3, f"{c['cca3']}: border {other!r} is not a known cca3"):
                continue
            check(c["cca3"] in (by_cca3[other].get("borders") or []),
                  f"border not reciprocal: {c['cca3']} lists {other}, "
                  f"but {other} does not list {c['cca3']}")
        check(not (c.get("landlocked") and not c.get("borders")),
              f"{c['cca3']}: marked landlocked but has no borders")

    # ---- currencies ------------------------------------------------------
    for code, cur in currencies.items():
        check(bool(re.fullmatch(r"[A-Z]{3}", code)), f"currencies.json: bad code {code!r}")
        check(cur.get("minorUnit") is not None, f"{code}: minorUnit must be set")
        check(bool(cur.get("name", {}).get("en")), f"{code}: missing English name")
        check(bool(cur.get("name", {}).get("de")), f"{code}: missing German name")
        if not cur.get("active"):
            check("successor" in cur, f"{code}: withdrawn currency needs a successor key")
            successor = cur.get("successor")
            check(successor is None or successor in currencies,
                  f"{code}: successor {successor!r} is not in currencies.json")

    for c in countries:
        for code in c.get("currency") or []:
            if check(code in currencies, f"{c['cca3']}: currency {code} missing from currencies.json"):
                check(currencies[code]["active"],
                      f"{c['cca3']}: currency {code} is withdrawn and belongs in currencyFormer")
        for code in c.get("currencyFormer") or []:
            if check(code in currencies,
                     f"{c['cca3']}: currencyFormer {code} missing from currencies.json"):
                check(not currencies[code]["active"],
                      f"{c['cca3']}: currencyFormer {code} is still active")

    # ---- languages -------------------------------------------------------
    for code, lang in languages.items():
        check(bool(re.fullmatch(r"[a-z]{2}", code)), f"languages.json: bad code {code!r}")
        check(lang.get("iso2") == code, f"{code}: iso2 must equal the key")
        check(bool(re.fullmatch(r"[a-z]{3}", lang.get("iso3") or "")),
              f"{code}: bad iso3 {lang.get('iso3')!r}")
        for field in ("native", "de", "en"):
            check(bool(lang.get("name", {}).get(field)), f"{code}: missing name.{field}")
        icon = lang.get("icon3")
        check(icon is None or icon in by_cca3,
              f"{code}: icon3 {icon!r} is not a valid cca3")
        for country in lang.get("countries") or []:
            check(country in by_cca3, f"{code}: countries lists unknown cca3 {country!r}")

    # ---- timezones -------------------------------------------------------
    check(zones == sorted(zones), "timezones.json must be sorted")
    check(len(zones) == len(set(zones)), "timezones.json contains duplicates")
    check(set(zones) == set(zones_detailed),
          "timezones.json and timezones_detailed.json describe different zones")
    for name, tz in zones_detailed.items():
        check(tz.get("utcOffset") is not None, f"{name}: missing utcOffset")
        check(tz.get("usesDst") == (tz.get("dstOffset") is not None),
              f"{name}: usesDst disagrees with dstOffset")
        for country in tz.get("countries") or []:
            check(country in by_cca3, f"{name}: unknown country {country!r}")

    known_zones = set(zones)
    for c in countries:
        for name in c.get("timezones") or []:
            check(name in known_zones, f"{c['cca3']}: timezone {name!r} not in timezones.json")

    return report()


if __name__ == "__main__":
    sys.exit(main())
