#!/usr/bin/env python3
"""Generate data/currencies.json.

Sources
  ISO 4217 list-one / list-three (SIX Group, the ISO 4217 maintenance agency)
      -> code, numeric code, minor unit, English name, active vs. withdrawn
  Unicode CLDR (cldr-numbers-full)
      -> display names and symbols for en and de
  data/countries.json
      -> which countries use which currency

Withdrawn currencies are only included when they are relevant to records that
may still exist in downstream databases: the predecessors of the euro and the
currencies replaced since 2015. Shipping all ~600 historic ISO 4217 codes would
add noise without adding value.
"""
import re
import xml.etree.ElementTree as ET

from _lib import fetch, fetch_json, read_json, write_json

ISO_ACTIVE = "https://www.six-group.com/dam/download/financial-information/data-center/iso-currrency/lists/list-one.xml"
ISO_HISTORIC = "https://www.six-group.com/dam/download/financial-information/data-center/iso-currrency/lists/list-three.xml"
CLDR = "https://raw.githubusercontent.com/unicode-org/cldr-json/main/cldr-json/cldr-numbers-full/main/{loc}/currencies.json"
CLDR_FRACTIONS = "https://raw.githubusercontent.com/unicode-org/cldr-json/main/cldr-json/cldr-core/supplemental/currencyData.json"

# Withdrawn codes worth keeping, with the code that replaced them.
KEEP_HISTORIC = {
    # replaced since 2015 - these still appear in live application data
    "ANG": "XCG", "BGN": "EUR", "BYR": "BYN", "CUC": "CUP", "HRK": "EUR", "LTL": "EUR",
    "MRO": "MRU", "SLL": "SLE", "STD": "STN", "VEF": "VES", "ZMK": "ZMW",
    "ZWL": "ZWG", "ZWD": "ZWG", "ZWN": "ZWG", "ZWR": "ZWG", "USS": "USD",
    # euro predecessors - relevant for any historic European bookkeeping
    "ATS": "EUR", "BEF": "EUR", "CYP": "EUR", "DEM": "EUR", "EEK": "EUR",
    "ESP": "EUR", "FIM": "EUR", "FRF": "EUR", "GRD": "EUR", "IEP": "EUR",
    "ITL": "EUR", "LUF": "EUR", "LVL": "EUR", "MTL": "EUR", "NLG": "EUR",
    "PTE": "EUR", "SIT": "EUR", "SKK": "EUR",
}

# Currencies in circulation that ISO 4217 never assigned a code to. They are
# marked iso:false so that a strict consumer can filter them out.
NON_ISO = {
    "CKD": {
        "name": {"en": "Cook Islands Dollar", "de": "Cook-Islands-Dollar"},
        "symbol": "$",
        "minorUnit": 2,
        "note": "Circulates at par with NZD; no ISO 4217 code assigned.",
    },
}


def _text(node, tag):
    child = node.find(tag)
    return child.text.strip() if child is not None and child.text else None


def parse_iso(xml_text, historic=False):
    root = ET.fromstring(xml_text)
    published = root.get("Pblshd")
    out = {}
    entry_tag = "HstrcCcyNtry" if historic else "CcyNtry"
    for node in root.iter(entry_tag):
        code = _text(node, "Ccy")
        if not code:
            continue
        rec = out.setdefault(
            code,
            {
                "name_iso": _text(node, "CcyNm"),
                "numeric": _text(node, "CcyNbr"),
                "minorUnit": _text(node, "CcyMnrUnts"),
                "countries_iso": [],
                "until": _text(node, "WthdrwlDt"),
            },
        )
        country = _text(node, "CtryNm")
        if country:
            rec["countries_iso"].append(country)
        if historic:
            # A code can appear several times (once per country, and again after
            # a redenomination). The date that matters is the last one.
            seen = _text(node, "WthdrwlDt")
            if seen and (rec.get("until") is None or seen > rec["until"]):
                rec["until"] = seen
    return published, out


def cldr(locale):
    doc = fetch_json(CLDR.format(loc=locale), f"cldr_currencies_{locale}.json")
    return doc["main"][locale]["numbers"]["currencies"]


def main():
    published, active = parse_iso(fetch(ISO_ACTIVE, "iso4217_one.xml"))
    _, historic = parse_iso(fetch(ISO_HISTORIC, "iso4217_three.xml"), historic=True)
    names = {loc: cldr(loc) for loc in ("en", "de")}
    fractions = fetch_json(CLDR_FRACTIONS, "cldr_currencydata.json")[
        "supplemental"]["currencyData"]["fractions"]
    default_digits = int(fractions["DEFAULT"]["_digits"])

    countries = read_json("countries.json")
    used_by = {}
    for country in countries:
        for code in country.get("currency") or []:
            used_by.setdefault(code, []).append(country["cca3"])
        for code in country.get("currencyFormer") or []:
            used_by.setdefault(code, []).append(country["cca3"])

    out = {}

    def emit(code, rec, is_active):
        minor = rec.get("minorUnit")
        if not (minor and minor.isdigit()):
            # ISO's historic list omits the minor unit; CLDR still carries it.
            minor = fractions.get(code, {}).get("_digits", str(default_digits))
        entry = {
            "name": {
                "en": (names["en"].get(code, {}).get("displayName") or rec.get("name_iso")),
                "de": (names["de"].get(code, {}).get("displayName")
                       or names["en"].get(code, {}).get("displayName")
                       or rec.get("name_iso")),
            },
            "symbol": names["en"].get(code, {}).get("symbol") or code,
            "symbolNarrow": names["en"].get(code, {}).get("symbol-alt-narrow"),
            "numeric": rec.get("numeric"),
            "minorUnit": int(minor) if minor and minor.isdigit() else None,
            "iso": True,
            "active": is_active,
            "countries": sorted(used_by.get(code, [])),
        }
        if not is_active:
            entry["until"] = (rec.get("until") or None)
            entry["successor"] = KEEP_HISTORIC.get(code)
        out[code] = entry

    for code, rec in active.items():
        emit(code, rec, True)
    for code in KEEP_HISTORIC:
        if code in out:
            continue
        emit(code, historic.get(code, {"name_iso": code, "numeric": None,
                                       "minorUnit": None, "until": None}), False)
    for code, rec in NON_ISO.items():
        out[code] = {
            "name": rec["name"],
            "symbol": rec["symbol"],
            "symbolNarrow": rec["symbol"],
            "numeric": None,
            "minorUnit": rec["minorUnit"],
            "iso": False,
            "active": True,
            "countries": sorted(used_by.get(code, [])),
            "note": rec["note"],
        }

    payload = dict(sorted(out.items()))
    write_json("currencies.json", payload)
    active_n = sum(1 for v in payload.values() if v["active"])
    print(f"  ISO 4217 published {published}: "
          f"{active_n} active, {len(payload) - active_n} withdrawn, {len(payload)} total")


if __name__ == "__main__":
    main()
