#!/usr/bin/env python3
"""Generate data/timezones.json and data/timezones_detailed.json.

timezones.json is the plain, sorted list of IANA zone names it has always been:
IANA's zone.tab, plus Asia/Choibalsan, which tzdb demoted to a link in 2024a but
which stays here so that values already stored by consumers remain valid.

timezones_detailed.json describes each of those zones. It deliberately does NOT
record a "current" UTC offset, because that would be wrong for half the year in
every zone that observes daylight saving time. It records the standard offset
and, separately, the daylight saving offset. Which one applies right now is a
question only a tz-aware library can answer.

Sources
  IANA tzdata zone.tab (public domain) -> zone names, countries, coordinates
  the tz database itself, via Python's zoneinfo -> offsets and abbreviations
"""
import datetime as dt
import zoneinfo

from _lib import fetch, read_json, write_json

ZONE_TAB = "https://data.iana.org/time-zones/tzdb/zone.tab"

# Demoted to a backward-compatibility link in tzdb 2024a. Still a valid
# identifier, and dropping it would invalidate stored user data.
RETAINED = ["Asia/Choibalsan"]


def parse_coord(text):
    """Decode zone.tab's ISO 6709 coordinates, e.g. +4230+00131 or +423000+0013100."""
    import re

    match = re.match(
        r"^([+-]\d{2})(\d{2})(\d{2})?([+-]\d{3})(\d{2})(\d{2})?$", text.strip()
    )
    if not match:
        return None
    lat_d, lat_m, lat_s, lon_d, lon_m, lon_s = match.groups()

    def combine(deg, minute, second):
        value = abs(int(deg)) + int(minute) / 60 + int(second or 0) / 3600
        return round(-value if deg.startswith("-") else value, 4)

    return [combine(lat_d, lat_m, lat_s), combine(lon_d, lon_m, lon_s)]


def offsets(zone_name):
    """(standard offset, dst offset or None, {abbreviation: offset}) in minutes."""
    try:
        tz = zoneinfo.ZoneInfo(zone_name)
    except Exception:  # noqa: BLE001 - zone missing from the local tzdata
        return None, None, {}
    year = dt.datetime.now(dt.timezone.utc).year
    std, dst, abbrevs = None, None, {}
    for month in range(1, 13):
        for day in (1, 15):
            moment = dt.datetime(year, month, day, 12, tzinfo=tz)
            total = int(moment.utcoffset().total_seconds() // 60)
            saving = int(moment.dst().total_seconds() // 60)
            name = moment.tzname()
            if name:
                abbrevs[name] = total
            if saving:
                dst = total if dst is None else max(dst, total)
            else:
                std = total if std is None else min(std, total)
    if std is None:  # zone is on DST the whole year round
        std, dst = dst, None
    return std, dst, abbrevs


def hhmm(minutes):
    if minutes is None:
        return None
    sign = "-" if minutes < 0 else "+"
    minutes = abs(minutes)
    return f"{sign}{minutes // 60:02d}:{minutes % 60:02d}"


def main():
    rows = []
    for line in fetch(ZONE_TAB, "zone.tab").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split("\t")
        rows.append((parts[0].split(","), parts[1], parts[2].strip(),
                     parts[3].strip() if len(parts) > 3 else None))

    known = {r[2] for r in rows}
    for name in RETAINED:
        if name not in known:
            rows.append((["MN"], "+4804+11430", name, "Dornod, Sukhbaatar"))

    names = sorted(r[2] for r in rows)
    write_json("timezones.json", names)

    countries = {c["cca2"]: c["cca3"] for c in read_json("countries.json") if c["cca2"]}

    detailed = {}
    missing = []
    for cca2_list, coord, name, comment in sorted(rows, key=lambda r: r[2]):
        std, dst, abbrevs = offsets(name)
        if std is None:
            missing.append(name)
        detailed[name] = {
            "name": name,
            "countries": sorted({countries[c] for c in cca2_list if c in countries}),
            "utcOffset": hhmm(std),
            "utcOffsetMinutes": std,
            "dstOffset": hhmm(dst),
            "dstOffsetMinutes": dst,
            "usesDst": dst is not None,
            "abbreviations": sorted(abbrevs),
            "latlng": parse_coord(coord),
            "comment": comment or None,
            "deprecated": name in RETAINED,
        }
    write_json("timezones_detailed.json", detailed)

    tzver = getattr(__import__("tzdata"), "IANA_VERSION", "unknown")
    print(f"  {len(names)} zones | tzdata {tzver} | "
          f"{sum(1 for v in detailed.values() if v['usesDst'])} observe DST")
    if missing:
        print(f"  WARNING: no offset resolved for {missing}")


if __name__ == "__main__":
    main()
