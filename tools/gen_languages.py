#!/usr/bin/env python3
"""Generate data/languages.json.

Keys stay two-letter ISO 639-1 codes, as they always were, so existing lookups
like languages["de"] keep working. Every entry additionally carries iso2/iso3/
iso3b so that it can be joined against countries.json, which uses ISO 639-3.

Sources
  ISO 639-2 registry (Library of Congress) -> the 639-1/639-2/639-3 mapping
  Wikidata (CC0)                           -> English, German and native names
  data/countries.json                      -> countries where the language is
                                              official, and the icon3 fallback

`icon3` is a display fallback only: an ISO 3166-1 alpha-3 code whose flag can
stand in for the language in a user interface. It is not a claim about where
the language is spoken, and it is null when no single country is a sensible
representative.
"""
from _lib import binding, fetch, read_json, sparql, write_json

ISO639 = "https://raw.githubusercontent.com/haliaeetus/iso-639/master/data/iso_639-1.json"
LOC_639_2 = "https://www.loc.gov/standards/iso639-2/ISO-639-2_utf-8.txt"

# Curated flag choices that predate this generator, kept so the UI does not
# change under the user's feet. "JAP" was not a valid ISO 3166-1 code at all;
# Japan is JPN.
ICON_OVERRIDES = {
    "ar": "EGY", "ca": "AND", "da": "DNK", "de": "DEU", "en": "USA",
    "es": "ESP", "fr": "FRA", "it": "ITA", "ja": "JPN", "lv": "LVA",
    "nl": "NLD", "pt": "PRT", "ru": "RUS", "sv": "SWE", "uk": "UKR",
}

# German names that were curated by hand before this generator existed and are
# better than what Wikidata returns.
NAME_DE_OVERRIDES = {
    "nl": "niederländisch",  # was "holländisch", which names only two provinces
    "lg": "luganda",
    "os": "ossetisch",
    "tl": "tagalog",
}

# Wikidata has no native label for these.
NAME_NATIVE_OVERRIDES = {
    "ae": "avesta",
}


def loc_registry():
    """ISO 639-1 -> (bibliographic 639-2, terminological 639-2, English name)."""
    out = {}
    for line in fetch(LOC_639_2, "iso639-2.txt").lstrip("\ufeff").splitlines():
        parts = line.split("|")
        if len(parts) < 4 or not parts[2].strip():
            continue
        bib, term, alpha2, english = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
        out[alpha2] = (bib, term or bib, english.split(";")[0].strip())
    return out


def wikidata_names():
    """ISO 639-1 -> {'en':…, 'de':…, 'native':…}"""
    out = {}
    rows = sparql(
        'SELECT ?code ?en ?de ?native WHERE { ?l wdt:P218 ?code . '
        'OPTIONAL { ?l rdfs:label ?en FILTER(lang(?en)="en") } '
        'OPTIONAL { ?l rdfs:label ?de FILTER(lang(?de)="de") } '
        'OPTIONAL { ?l wdt:P1705 ?native } }',
        "wd_languages.json",
    )
    for row in rows:
        code = binding(row, "code")
        if not code:
            continue
        rec = out.setdefault(code, {})
        for key in ("en", "de", "native"):
            value = binding(row, key)
            if value and not rec.get(key):
                rec[key] = value
    return out


def main():
    registry = loc_registry()
    names = wikidata_names()
    countries = read_json("countries.json")

    # which countries list this language as official, keyed by ISO 639-3
    spoken = {}
    for country in countries:
        for iso3 in (country.get("languages") or {}):
            spoken.setdefault(iso3, []).append(country["cca3"])

    out = {}
    for alpha2, (bib, term, english) in sorted(registry.items()):
        wd = names.get(alpha2, {})
        # The ISO 639-2 registry is authoritative for the English name; Wikidata
        # labels drift (it returns "iron dialect" for Ossetian, for example).
        name_en = (english or wd.get("en") or "").lower() or None
        name_de = NAME_DE_OVERRIDES.get(alpha2) or (wd.get("de") or "").lower() or None
        out[alpha2] = {
            "name": {
                "native": NAME_NATIVE_OVERRIDES.get(alpha2) or wd.get("native"),
                "de": name_de,
                "en": name_en,
            },
            "iso2": alpha2,
            "iso3": term,
            "iso3b": bib,
            "icon3": ICON_OVERRIDES.get(alpha2),
            "countries": sorted(spoken.get(term, [])),
        }

    # A language that is official in exactly one country gets that country's
    # flag as its display fallback. Anything ambiguous stays null.
    for alpha2, rec in out.items():
        if rec["icon3"] is None and len(rec["countries"]) == 1:
            rec["icon3"] = rec["countries"][0]

    write_json("languages.json", out)
    with_icon = sum(1 for v in out.values() if v["icon3"])
    with_de = sum(1 for v in out.values() if v["name"]["de"])
    with_native = sum(1 for v in out.values() if v["name"]["native"])
    print(f"  {len(out)} languages | de names {with_de} | native {with_native} | icon3 {with_icon}")


if __name__ == "__main__":
    main()
