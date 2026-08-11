#!/usr/bin/env python3
"""Update and enrich data/countries.json.

The file keeps its original schema - every field that existed before still
exists under the same name with the same type, so downstream consumers do not
break. Everything new is added alongside.

Sources
  mledoze/countries (ODbL)   -> the two missing territories, capital corrections
  Wikidata (CC0)             -> population, continents, IOC codes, driving side,
                                vehicle registration signs, OSM relation ids,
                                capital coordinates
  IANA tzdata (public domain)-> the time zones of each country
  Unicode CLDR               -> first day of the week
  Google/Chromium libaddressinput -> postal code format and pattern
"""
import json
import re

from _lib import binding, fetch, fetch_json, read_json, sparql, write_json

MLEDOZE = "https://raw.githubusercontent.com/mledoze/countries/master/countries.json"
ZONE_TAB = "https://data.iana.org/time-zones/tzdb/zone.tab"
CLDR_WEEK = "https://raw.githubusercontent.com/unicode-org/cldr-json/main/cldr-json/cldr-core/supplemental/weekData.json"
ADDRESS = "https://chromium-i18n.appspot.com/ssl-aggregate-address/data/{cc}"

# --- corrections -----------------------------------------------------------

# "spa" is the ISO 639-3 language code for Spanish and was used where the ISO
# 3166-1 alpha-3 country code ESP belongs. Spain was therefore unreachable from
# five of its six neighbours.
BORDER_CODE_FIX = {"spa": "ESP"}

# Sri Lanka is an island. The Palk Strait separates it from India, and India
# correctly does not list LKA in return.
BORDER_REMOVE = {"LKA": {"IND"}}

# Countries renamed by their governments and reflected in ISO 3166-1. The
# previous name is preserved in altSpellings so name lookups keep working.
RENAMES = {
    "TUR": ("Türkiye", "Republic of Türkiye"),
    "SWZ": ("Eswatini", "Kingdom of Eswatini"),
    "MKD": ("North Macedonia", "Republic of North Macedonia"),
    "CPV": ("Cabo Verde", "Republic of Cabo Verde"),
}

# Withdrawn ISO 4217 codes and their successors.
CURRENCY_SUCCESSOR = {
    "ANG": "XCG", "BGN": "EUR", "HRK": "EUR", "MRO": "MRU", "SLL": "SLE",
    "STD": "STN", "VEF": "VES", "ZWL": "ZWG",
}
# Withdrawn without a replacement in the same country.
CURRENCY_DROP = {"CUC", "USS"}
# In circulation but never assigned an ISO 4217 code.
CURRENCY_NON_ISO = {"CKD"}

WEEKDAY = {"mon": "monday", "sun": "sunday", "sat": "saturday", "fri": "friday"}

# Three entries cannot be resolved from the generic sources and are stated here
# explicitly rather than left silently empty.
OVERRIDES = {
    # XK is user-assigned, so Kosovo carries no ISO 3166-1 alpha-3 code and is
    # absent from both Wikidata's P298 index and IANA's zone.tab.
    "UNK": {"timezones": ["Europe/Belgrade"], "population": 1586659,
            "populationAsOf": "2024-01-01"},
    # Uninhabited dependencies: no permanent population, no IANA zone.
    "BVT": {"population": 0, "populationAsOf": None},
    "HMD": {"population": 0, "populationAsOf": None},
}


def load_mledoze():
    return {c["cca3"]: c for c in json.loads(fetch(MLEDOZE, "mledoze_countries.json"))}


def zone_tab():
    """cca2 -> sorted list of IANA zone names, from IANA zone.tab."""
    out = {}
    for line in fetch(ZONE_TAB, "zone.tab").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split("\t")
        for cc in parts[0].split(","):
            out.setdefault(cc, set()).add(parts[2].strip())
    return {k: sorted(v) for k, v in out.items()}


def first_day():
    doc = fetch_json(CLDR_WEEK, "cldr_weekdata.json")
    table = doc["supplemental"]["weekData"]["firstDay"]
    return {k: WEEKDAY.get(v, v) for k, v in table.items()}, WEEKDAY.get(table.get("001", "mon"))


def postal_codes(cca2_list):
    out = {}
    for cc in cca2_list:
        try:
            doc = fetch_json(ADDRESS.format(cc=cc), f"address_{cc}.json", max_age=30 * 86400)
        except Exception:  # noqa: BLE001 - territory not covered upstream
            continue
        rec = doc.get(f"data/{cc}") or {}
        pattern = rec.get("zip")
        if not pattern:
            continue
        out[cc] = {
            "pattern": f"^{pattern}$",
            "example": (rec.get("zipex") or "").split(",")[0] or None,
        }
    return out


def wikidata():
    """iso3 -> enrichment dict, assembled from several small SPARQL queries."""
    out = {}

    def collect(query, name, key, field, multi=False, cast=str):
        for row in sparql(query, name):
            iso3 = binding(row, "iso3")
            value = binding(row, key)
            if not iso3 or value is None:
                continue
            rec = out.setdefault(iso3, {})
            if multi:
                rec.setdefault(field, set()).add(cast(value))
            else:
                rec.setdefault(field, cast(value))

    collect("SELECT ?iso3 ?v WHERE { ?c wdt:P298 ?iso3; wdt:P984 ?v }",
            "wd_ioc.json", "v", "cioc")
    collect("SELECT ?iso3 ?v WHERE { ?c wdt:P298 ?iso3; wdt:P402 ?v }",
            "wd_osm.json", "v", "osm")
    collect('SELECT ?iso3 ?v WHERE { ?c wdt:P298 ?iso3; wdt:P1622 ?x . '
            '?x rdfs:label ?v FILTER(lang(?v)="en") }',
            "wd_side.json", "v", "side")
    collect('SELECT ?iso3 ?v WHERE { ?c wdt:P298 ?iso3; wdt:P30 ?x . '
            '?x rdfs:label ?v FILTER(lang(?v)="en") }',
            "wd_continent.json", "v", "continents", multi=True)
    collect("SELECT ?iso3 ?v WHERE { ?c wdt:P298 ?iso3; wdt:P395 ?v }",
            "wd_carsign.json", "v", "signs", multi=True)

    # population: keep the value with the most recent point-in-time qualifier
    latest = {}
    query = ("SELECT ?iso3 ?pop ?date WHERE { ?c wdt:P298 ?iso3 . "
             "?c p:P1082 ?st . ?st ps:P1082 ?pop . OPTIONAL { ?st pq:P585 ?date } "
             "FILTER NOT EXISTS { ?st wikibase:rank wikibase:DeprecatedRank } }")
    for row in sparql(query, "wd_population.json"):
        iso3, pop, date = binding(row, "iso3"), binding(row, "pop"), binding(row, "date") or ""
        if not iso3 or not pop:
            continue
        if iso3 not in latest or date > latest[iso3][1]:
            latest[iso3] = (int(float(pop)), date)
    for iso3, (pop, date) in latest.items():
        out.setdefault(iso3, {})["population"] = pop
        out[iso3]["populationAsOf"] = date[:10] or None

    # capital coordinates
    query = ('SELECT ?iso3 ?coord WHERE { ?c wdt:P298 ?iso3; wdt:P36 ?cap . '
             "?cap wdt:P625 ?coord }")
    for row in sparql(query, "wd_capital.json"):
        iso3, coord = binding(row, "iso3"), binding(row, "coord")
        if iso3 and coord and coord.startswith("Point("):
            lon, lat = coord[6:-1].split()
            out.setdefault(iso3, {}).setdefault(
                "capitalLatLng", [round(float(lat), 4), round(float(lon), 4)]
            )

    for rec in out.values():
        for field, value in list(rec.items()):
            if isinstance(value, set):
                rec[field] = sorted(value)
    return out


def to_v2(rec):
    """Map an mledoze v4 record onto this repository's v2-shaped schema."""
    demonyms = rec.get("demonyms") or {}
    return {
        "name": rec["name"],
        "tld": rec.get("tld") or [],
        "cca2": rec["cca2"],
        "ccn3": rec.get("ccn3") or "",
        "cca3": rec["cca3"],
        "cioc": rec.get("cioc") or "",
        "independent": bool(rec.get("independent")),
        "status": rec.get("status") or "officially-assigned",
        "currency": sorted((rec.get("currencies") or {}).keys()),
        "callingCode": [
            (rec.get("idd", {}).get("root", "").lstrip("+") + suffix)
            for suffix in rec.get("idd", {}).get("suffixes", [])
        ],
        "capital": rec.get("capital") or [],
        "altSpellings": rec.get("altSpellings") or [],
        "region": rec.get("region") or "",
        "subregion": rec.get("subregion") or "",
        "languages": rec.get("languages") or {},
        "translations": rec.get("translations") or {},
        "latlng": rec.get("latlng") or [],
        "demonym": (demonyms.get("eng") or {}).get("m") or "",
        "landlocked": bool(rec.get("landlocked")),
        "borders": rec.get("borders") or [],
        "area": rec.get("area") or 0,
        "flag": rec.get("flag") or "",
    }


def main():
    countries = read_json("countries.json")
    upstream = load_mledoze()
    zones = zone_tab()
    week_table, week_default = first_day()
    wd = wikidata()

    # 1. add the two territories that were never in the file
    have = {c["cca3"] for c in countries}
    for code in ("BES", "SHN"):
        if code not in have and code in upstream:
            countries.append(to_v2(upstream[code]))
            print(f"  added {code} ({upstream[code]['name']['common']})")

    postal = postal_codes(sorted({c["cca2"] for c in countries if c["cca2"]}))

    for c in countries:
        code = c["cca3"]
        up = upstream.get(code, {})

        # 2. border repairs
        borders = [BORDER_CODE_FIX.get(b, b) for b in c.get("borders") or []]
        borders = [b for b in borders if b not in BORDER_REMOVE.get(code, set())]
        c["borders"] = sorted(dict.fromkeys(borders))

        # 3. renames, with the previous names kept as alternative spellings
        if code in RENAMES:
            common, official = RENAMES[code]
            for field, value in (("common", common), ("official", official)):
                previous = c["name"][field]
                if previous == value:
                    continue
                c["name"][field] = value
                if previous not in c["altSpellings"]:
                    c["altSpellings"].append(previous)
                print(f"  renamed {code} ({field}): {previous} -> {value}")

        # 4. currencies: only valid, current codes remain in `currency`.
        # This script rewrites the file in place, so anything already moved to
        # currencyFormer by an earlier run has to survive this one.
        former, current = list(c.get("currencyFormer") or []), []
        for cur in c.get("currency") or []:
            if cur in CURRENCY_DROP:
                former.append(cur)
            elif cur in CURRENCY_SUCCESSOR:
                former.append(cur)
                current.append(CURRENCY_SUCCESSOR[cur])
            else:
                current.append(cur)
        # The order of `currency` is meaningful - the first entry is the
        # dominant currency of that country - so it is preserved, not sorted.
        c["currency"] = list(dict.fromkeys(current))
        c["currencyFormer"] = sorted(dict.fromkeys(former))

        # 5. capital corrections from upstream (Burundi moved to Gitega in 2019)
        if up.get("capital") and up["capital"] != c.get("capital"):
            print(f"  capital {code}: {c.get('capital')} -> {up['capital']}")
            c["capital"] = up["capital"]

        info = wd.get(code, {})

        # 6. fill gaps in existing fields, never overwrite a curated value
        if not c.get("cioc") and info.get("cioc"):
            c["cioc"] = info["cioc"]
        if not c.get("subregion") and up.get("subregion"):
            c["subregion"] = up["subregion"]
        if not c.get("demonym"):
            c["demonym"] = ((up.get("demonyms") or {}).get("eng") or {}).get("m") or ""

        # 7. new, additive fields
        c["unMember"] = bool(up.get("unMember", False))
        c["population"] = info.get("population")
        c["populationAsOf"] = info.get("populationAsOf")
        c["continents"] = info.get("continents") or ([c["region"]] if c.get("region") else [])
        c["timezones"] = zones.get(c["cca2"], [])
        c["startOfWeek"] = week_table.get(c["cca2"], week_default)
        c["capitalInfo"] = {"latlng": info.get("capitalLatLng")}
        c["car"] = {"signs": info.get("signs") or [], "side": info.get("side") or "right"}
        c["postalCode"] = postal.get(c["cca2"])
        cca2 = (c["cca2"] or "").lower()
        c["flags"] = {
            "png": f"https://flagcdn.com/w320/{cca2}.png",
            "svg": f"https://flagcdn.com/{cca2}.svg",
        } if cca2 else {"png": None, "svg": None}
        for field, value in OVERRIDES.get(code, {}).items():
            c[field] = value

        osm = info.get("osm")
        latlng = c.get("latlng") or []
        c["maps"] = {
            "openStreetMaps": f"https://www.openstreetmap.org/relation/{osm}" if osm else None,
            "googleMaps": (f"https://www.google.com/maps/@{latlng[0]},{latlng[1]},6z"
                           if len(latlng) == 2 else None),
        }

    countries.sort(key=lambda c: c["cca3"])
    write_json("countries.json", countries)
    print(f"  {len(countries)} countries")


if __name__ == "__main__":
    main()
