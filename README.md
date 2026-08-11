# assets

Reference data and shared front-end assets used across the goo1 projects —
countries, currencies, languages and time zones as plain JSON, served straight
from GitHub with no build step, no package manager and no API key.

### Status & Stats

![Last Commit](https://img.shields.io/github/last-commit/andreaskasper/assets.svg)
![Commit Activity](https://img.shields.io/github/commit-activity/m/andreaskasper/assets.svg)
[![Issues](https://img.shields.io/github/issues/andreaskasper/assets.svg)](https://github.com/andreaskasper/assets/issues)
![Repo Size](https://img.shields.io/github/repo-size/andreaskasper/assets.svg)
[![Validate data](https://img.shields.io/github/actions/workflow/status/andreaskasper/assets/validate.yml?branch=master&label=data%20validation)](https://github.com/andreaskasper/assets/actions/workflows/validate.yml)
[![Code: MIT](https://img.shields.io/badge/code-MIT-green.svg)](LICENSE)
[![Data: ODbL](https://img.shields.io/badge/data-ODbL--1.0-blue.svg)](data/LICENSE)
![Stars](https://img.shields.io/github/stars/andreaskasper/assets.svg?style=social)

---

## Contents

| Path | What it is |
| --- | --- |
| [`data/countries.json`](data/countries.json) | 250 countries and territories, ISO 3166-1 |
| [`data/currencies.json`](data/currencies.json) | 213 currencies, ISO 4217, active and withdrawn |
| [`data/languages.json`](data/languages.json) | 183 languages, ISO 639-1 |
| [`data/timezones.json`](data/timezones.json) | 419 IANA time zone names |
| [`data/timezones_detailed.json`](data/timezones_detailed.json) | the same zones with offsets, countries and coordinates |
| [`css/materialdesign-bootstrap.css`](css/materialdesign-bootstrap.css) | Material Design colour palette as CSS custom properties |
| [`nagios_icons/`](nagios_icons/) | host icons for Nagios |
| [`tools/`](tools/) | the generators that produce `data/` |

Every file in `data/` also exists as a `.min.json` twin. The pretty-printed
file is the one to read and review; the minified one is the one to ship. CI
fails if the two ever drift apart.

## Using it

Load a file straight from the repository:

```
https://raw.githubusercontent.com/andreaskasper/assets/master/data/countries.json
```

Or through the jsDelivr CDN, which adds caching and proper CORS headers:

```
https://cdn.jsdelivr.net/gh/andreaskasper/assets@master/data/countries.min.json
```

> **Pin your version.** `master` moves. For anything in production, replace it
> with a commit SHA or a tag — jsDelivr accepts both
> (`…/assets@86efac1/data/…`). A pinned URL cannot change under your feet, and
> jsDelivr caches it permanently.

```js
const countries = await fetch(
  "https://cdn.jsdelivr.net/gh/andreaskasper/assets@master/data/countries.min.json"
).then((r) => r.json());

const byCca3 = Object.fromEntries(countries.map((c) => [c.cca3, c]));
byCca3.DEU.name.common;   // "Germany"
byCca3.DEU.currency;      // ["EUR"]
byCca3.DEU.timezones;     // ["Europe/Berlin", "Europe/Busingen"]
```

```php
$countries = json_decode(file_get_contents(
    'https://cdn.jsdelivr.net/gh/andreaskasper/assets@master/data/countries.min.json'
), true);
```

The four files are designed to join on each other:

| From | Field | To |
| --- | --- | --- |
| `countries.json` | `currency[]`, `currencyFormer[]` | keys of `currencies.json` |
| `countries.json` | `timezones[]` | entries of `timezones.json` |
| `countries.json` | `languages{}` keys | `languages.json` → `iso3` |
| `languages.json` | `icon3`, `countries[]` | `countries.json` → `cca3` |
| `currencies.json` | `countries[]`, `successor` | `countries.json` → `cca3`, `currencies.json` |

CI checks every one of these references on each push, so a dangling code is a
build failure rather than a runtime surprise.

---

## `data/countries.json`

A JSON **array**, sorted by `cca3`. 250 entries: the 249 codes officially
assigned in ISO 3166-1 plus `UNK` for Kosovo, which has only the user-assigned
`XK`.

| Field | Type | Notes |
| --- | --- | --- |
| `name` | object | `common`, `official`, and `native` keyed by ISO 639-3 |
| `tld` | string[] | country-code top-level domains, with the leading dot |
| `cca2` | string | ISO 3166-1 alpha-2 |
| `ccn3` | string | ISO 3166-1 numeric, zero-padded; empty for `UNK` |
| `cca3` | string | ISO 3166-1 alpha-3 — the primary key of this file |
| `cioc` | string | IOC code; empty where the territory has none |
| `independent` | bool | sovereign state |
| `status` | string | `officially-assigned` or `user-assigned` |
| `currency` | string[] | **active** ISO 4217 codes only |
| `currencyFormer` | string[] | withdrawn codes this country used to use |
| `callingCode` | string[] | without the leading `+` |
| `capital` | string[] | more than one where a country has several seats |
| `altSpellings` | string[] | includes former names after a rename |
| `region` / `subregion` | string | UN geoscheme |
| `languages` | object | ISO 639-3 → English name |
| `translations` | object | ISO 639-3 → `{official, common}` |
| `latlng` | number[2] | latitude, longitude of the country |
| `demonym` | string | English, masculine form |
| `landlocked` | bool | |
| `borders` | string[] | `cca3` of every land neighbour, sorted, always mutual |
| `area` | number | km² |
| `flag` | string | emoji |
| `unMember` | bool | UN member state |
| `population` | number | |
| `populationAsOf` | string | ISO date the population figure refers to |
| `continents` | string[] | |
| `timezones` | string[] | IANA zone names |
| `startOfWeek` | string | `monday`, `sunday`, `friday` or `saturday` |
| `capitalInfo` | object | `{latlng}` of the capital, `null` where unknown |
| `car` | object | `{signs[], side}` — vehicle registration code, `left`/`right` |
| `postalCode` | object | `{pattern, example}`; `null` where no postal codes |
| `flags` | object | `{png, svg}` on flagcdn.com |
| `maps` | object | `{openStreetMaps, googleMaps}` |

```json
{
  "name": { "common": "Germany", "official": "Federal Republic of Germany" },
  "cca2": "DE", "ccn3": "276", "cca3": "DEU", "cioc": "GER",
  "currency": ["EUR"], "currencyFormer": [],
  "callingCode": ["49"], "capital": ["Berlin"],
  "region": "Europe", "subregion": "Western Europe",
  "borders": ["AUT", "BEL", "CHE", "CZE", "DNK", "FRA", "LUX", "NLD", "POL"],
  "population": 83577140, "populationAsOf": "2024-12-31",
  "timezones": ["Europe/Berlin", "Europe/Busingen"],
  "startOfWeek": "monday",
  "car": { "signs": ["D"], "side": "right" },
  "postalCode": { "pattern": "^\\d{5}$", "example": "26133" },
  "flag": "🇩🇪"
}
```

### Things worth knowing

- **`currency` only ever contains codes that are valid today.** When a country
  changes currency the old code moves to `currencyFormer`; it never silently
  disappears, so a historic record stays resolvable against `currencies.json`.
- **`borders` is symmetric.** If A lists B, B lists A. CI enforces it.
- **Empty is not the same as missing.** `borders` is empty for islands and
  `subregion` is empty for the Antarctic entries because that is the correct
  answer, not because the data is incomplete.
- **`postalCode` is `null` for 70 entries** — those territories genuinely do
  not use postal codes.

## `data/currencies.json`

A JSON **object** keyed by currency code. 179 active, 34 withdrawn.

| Field | Type | Notes |
| --- | --- | --- |
| `name` | object | `en`, `de` |
| `symbol` | string | falls back to the code where no symbol exists |
| `symbolNarrow` | string | the short form, e.g. `kn`; may be `null` |
| `numeric` | string | ISO 4217 numeric code |
| `minorUnit` | number | decimal places — **0** for JPY, **3** for TND, **4** for CLF |
| `iso` | bool | `false` for currencies ISO never assigned a code to |
| `active` | bool | |
| `countries` | string[] | `cca3` of every country using it, past or present |
| `until` | string | withdrawal date, withdrawn currencies only |
| `successor` | string | the code that replaced it, withdrawn currencies only |

```json
"HRK": {
  "name": { "en": "Croatian Kuna", "de": "Kroatischer Kuna" },
  "symbol": "HRK", "symbolNarrow": "kn",
  "numeric": "191", "minorUnit": 2,
  "iso": true, "active": false,
  "countries": ["HRV"], "until": "2023-01", "successor": "EUR"
}
```

> Never assume two decimal places. `minorUnit` is `0` for the Japanese yen and
> `3` for the Tunisian dinar; formatting either with two is wrong.

`CKD`, the Cook Islands dollar, is in circulation but has no ISO 4217 code. It
is included with `"iso": false` so a strict consumer can filter it out.

## `data/languages.json`

A JSON **object** keyed by ISO 639-1 alpha-2 code. 183 entries.

| Field | Type | Notes |
| --- | --- | --- |
| `name` | object | `native`, `de`, `en` — all three always populated |
| `iso2` | string | equal to the key |
| `iso3` | string | ISO 639-3 / 639-2/T — **use this to join `countries.json`** |
| `iso3b` | string | ISO 639-2/B, the bibliographic variant (`ger`, not `deu`) |
| `icon3` | string | display fallback, see below; may be `null` |
| `countries` | string[] | `cca3` where the language is official |

```json
"de": {
  "name": { "native": "Deutsch", "de": "deutsch", "en": "german" },
  "iso2": "de", "iso3": "deu", "iso3b": "ger",
  "icon3": "DEU",
  "countries": ["BEL", "DEU", "LIE", "LUX", "NAM"]
}
```

> **`icon3` is a UI convenience, not a fact.** It names a country whose flag
> can stand in for the language in a picker — English gets `USA`, Arabic gets
> `EGY`. That is a display choice, not a statement about where the language
> comes from or who speaks it. It is `null` for 101 languages that have no
> single sensible representative, including Esperanto and Latin; render a
> generic icon in that case. Use `countries[]` when you need the real answer.

## `data/timezones.json` and `data/timezones_detailed.json`

`timezones.json` is a flat, sorted array of 419 IANA zone names — IANA's
`zone.tab`, plus `Asia/Choibalsan`, which tzdb demoted to an alias in 2024a but
which is kept here so that values already stored by applications stay valid.

`timezones_detailed.json` is an object keyed by the same names:

| Field | Type | Notes |
| --- | --- | --- |
| `countries` | string[] | `cca3` |
| `utcOffset` / `utcOffsetMinutes` | string / number | **standard** time, e.g. `+01:00` |
| `dstOffset` / `dstOffsetMinutes` | string / number | daylight saving time, `null` if none |
| `usesDst` | bool | |
| `abbreviations` | string[] | e.g. `["CEST", "CET"]` |
| `latlng` | number[2] | |
| `comment` | string | IANA's own note, e.g. `"most of Germany"` |
| `deprecated` | bool | `true` for zones tzdb has turned into aliases |

```json
"Europe/Berlin": {
  "name": "Europe/Berlin", "countries": ["DEU"],
  "utcOffset": "+01:00", "utcOffsetMinutes": 60,
  "dstOffset": "+02:00", "dstOffsetMinutes": 120,
  "usesDst": true, "abbreviations": ["CEST", "CET"],
  "latlng": [52.5, 13.3667], "comment": "most of Germany",
  "deprecated": false
}
```

> **There is deliberately no "current offset" field.** A static file cannot
> hold one: it would be wrong for half the year in all 130 zones that observe
> daylight saving time. Use `utcOffset` for sorting and labelling, and ask a
> tz-aware library which offset applies at an actual moment in time.

Offsets are not all whole hours. `Asia/Kolkata` is `+05:30`, `Pacific/Chatham`
is `+12:45`, and `Australia/Lord_Howe` shifts by only 30 minutes for DST.

---

## `css/materialdesign-bootstrap.css`

The [Material Design 2 colour system](https://m2.material.io/design/color/the-color-system.html)
exposed as CSS custom properties, so Material palettes can be used inside a
Bootstrap project without pulling in a Material framework.

```css
@import url(https://raw.githubusercontent.com/andreaskasper/assets/master/css/materialdesign-bootstrap.css);
```

```css
.alert-danger { background-color: var(--color-md-red-900); }
.badge-accent { color: var(--color-md-pink-a400); }
```

Every hue is available from `-50` through `-900` plus the `-a100` … `-a700`
accents, following Material's own naming.

## `nagios_icons/`

Host icons for Nagios/Icinga host definitions, in the `.png`, `.gif` and `.gd2`
trio that Nagios expects.

```
avm_fritzbox  cloudflare  debian  mycloud_pr4100  nagios  server_doksite
```

```cfg
define host {
    host_name   fritzbox
    icon_image  avm_fritzbox.png
    statusmap_image  debian.gd2
}
```

> These files contain third-party logos and trademarks. See the licence note
> below.

---

## Regenerating the data

```bash
pip install tzdata
python3 tools/build.py
```

`tools/build.py` runs the generators in order, rewrites the minified twins and
validates the result. Upstream responses are cached for a day under
`tools/.cache/`, so a rerun is cheap and does not hammer anyone's servers.

| Script | Produces |
| --- | --- |
| `tools/enrich_countries.py` | `countries.json` — updates the file in place, and is idempotent |
| `tools/gen_currencies.py` | `currencies.json` |
| `tools/gen_languages.py` | `languages.json` |
| `tools/gen_timezones.py` | `timezones.json`, `timezones_detailed.json` |
| `tools/minify.py` | every `*.min.json`; `--check` verifies they are in sync |
| `tools/validate.py` | nothing — exits non-zero on the first problem |

`tools/validate.py` runs roughly 7,600 assertions: JSON shape, ISO code
formats, sorting, duplicate keys, border reciprocity in both directions, and
every cross-file reference listed above. It runs on every push and once a week
on a schedule, because ISO 4217 withdrawals and new tzdb releases arrive
whether or not anyone is looking.

## Sources

| Data | Source | Licence |
| --- | --- | --- |
| Country base data | [mledoze/countries](https://github.com/mledoze/countries) | ODbL 1.0 |
| Currency codes, minor units | [ISO 4217](https://www.six-group.com/en/products-services/financial-information/data-standards.html), via SIX Group | ISO / SIX |
| Currency and language names, symbols, first day of week | [Unicode CLDR](https://github.com/unicode-org/cldr-json) | Unicode-3.0 |
| Language code registry | [ISO 639-2 Registration Authority](https://www.loc.gov/standards/iso639-2/), Library of Congress | public |
| Population, continents, IOC codes, driving side, vehicle signs, capital coordinates | [Wikidata](https://www.wikidata.org) | CC0 1.0 |
| Time zones, coordinates, offsets | [IANA tzdata](https://www.iana.org/time-zones) | public domain |
| Postal code patterns | [Google libaddressinput](https://github.com/google/libaddressinput) | Apache 2.0 |
| Flag images | [flagcdn.com](https://flagcdn.com) | public domain |

## Licence

This repository is licensed in two parts, because code and data are not the
same kind of thing:

- **`tools/`, `.github/` and `css/` — [MIT](LICENSE).**
- **`data/` — [Open Database License (ODbL) v1.0](data/LICENSE).** The country
  data derives from [mledoze/countries](https://github.com/mledoze/countries),
  which is ODbL, and ODbL is share-alike: a derived database has to stay under
  the same terms. If you publicly use a modified version of these files, you
  have to make that version available under ODbL too.

**`nagios_icons/` is not covered by either.** Those files contain the logos and
trademarks of Cloudflare, Debian, AVM (FRITZ!Box) and Nagios. They belong to
their respective owners and are included here only for use in Nagios host
definitions.

Flag emoji and flag images are not covered by the ODbL grant either; see
[Wikipedia on copyright of emblems](https://en.wikipedia.org/wiki/Wikipedia:Copyright_on_emblems).
