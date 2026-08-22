#!/usr/bin/env python3
"""Apply the Aviation Authority redesign to every language page.

Transforms the parking section from a grid of tall cards into a dense,
sortable, filterable result list, and re-skins the whole page onto the new
palette and typeface.

Localized copy is never invented: lot names, locations, descriptions, feature
tags and filter labels are read from each page and carried across unchanged.
Only the small set of strings genuinely new to this design is translated here.

Usage:  python3 tools/build-redesign.py


SUPERSEDED. The lot rows now come from data/lots.csv via
tools/build-lots.py; data/prices.csv is gone and this script cannot
run against a built page anyway. Kept only as the record of how the
redesign was applied.
"""
from __future__ import annotations

import csv
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PAGES = ["index.html", "hu/index.html", "de/index.html", "ro/index.html",
         "sr/index.html", "hr/index.html", "sk/index.html"]

# Strings with no existing equivalent on the page. Everything else is reused.
S = {
    "index.html": dict(
        search="Search a lot or feature", price="Price", distance="Distance",
        filters="Filters", show="Show {n} lots",
        byPrice="{n} lots · cheapest first", byDistance="{n} lots · nearest first",
        checked="Prices checked 21 Aug 2026", trip="Trip length", days="days",
        total="Total for {n} days", perDay="/ day", shortStay="short-stay tariff",
        verified="Rate checked on {d}", est="est.", details="Details", one="1 lot"),
    "hu/index.html": dict(
        search="Keresés parkoló vagy szolgáltatás", price="Ár", distance="Távolság",
        filters="Szűrők", show="{n} parkoló mutatása",
        byPrice="{n} parkoló · legolcsóbb elöl", byDistance="{n} parkoló · legközelebbi elöl",
        checked="Árak ellenőrizve: 2026. aug. 21.", trip="Utazás hossza", days="nap",
        total="Összesen {n} napra", perDay="/ nap", shortStay="rövid távú tarifa",
        verified="Ár ellenőrizve: {d}", est="becsült", details="Részletek", one="1 parkoló"),
    "de/index.html": dict(
        search="Parkplatz oder Merkmal suchen", price="Preis", distance="Entfernung",
        filters="Filter", show="{n} Parkplätze anzeigen",
        byPrice="{n} Parkplätze · günstigste zuerst", byDistance="{n} Parkplätze · nächste zuerst",
        checked="Preise geprüft am 21. Aug. 2026", trip="Reisedauer", days="Tage",
        total="Gesamt für {n} Tage", perDay="/ Tag", shortStay="Kurzzeittarif",
        verified="Preis geprüft am {d}", est="ca.", details="Details", one="1 Parkplatz"),
    "ro/index.html": dict(
        search="Caută o parcare sau o facilitate", price="Preț", distance="Distanță",
        filters="Filtre", show="Arată {n} parcări",
        byPrice="{n} parcări · cele mai ieftine primele", byDistance="{n} parcări · cele mai apropiate primele",
        checked="Prețuri verificate la 21 aug. 2026", trip="Durata călătoriei", days="zile",
        total="Total pentru {n} zile", perDay="/ zi", shortStay="tarif de scurtă durată",
        verified="Preț verificat la {d}", est="aprox.", details="Detalii", one="1 parcare"),
    "sr/index.html": dict(
        search="Pretraži parking ili uslugu", price="Cena", distance="Udaljenost",
        filters="Filteri", show="Prikaži {n} parkinga",
        byPrice="{n} parkinga · najjeftiniji prvi", byDistance="{n} parkinga · najbliži prvi",
        checked="Cene proverene 21. avg 2026.", trip="Dužina putovanja", days="dana",
        total="Ukupno za {n} dana", perDay="/ dan", shortStay="tarifa za kratak boravak",
        verified="Cena proverena {d}", est="pribl.", details="Detalji", one="1 parking"),
    "hr/index.html": dict(
        search="Pretraži parkiralište ili uslugu", price="Cijena", distance="Udaljenost",
        filters="Filtri", show="Prikaži {n} parkirališta",
        byPrice="{n} parkirališta · najjeftinija prva", byDistance="{n} parkirališta · najbliža prva",
        checked="Cijene provjerene 21. kol 2026.", trip="Trajanje putovanja", days="dana",
        total="Ukupno za {n} dana", perDay="/ dan", shortStay="tarifa za kratak boravak",
        verified="Cijena provjerena {d}", est="pribl.", details="Detalji", one="1 parkiralište"),
    "sk/index.html": dict(
        search="Hľadať parkovisko alebo službu", price="Cena", distance="Vzdialenosť",
        filters="Filtre", show="Zobraziť {n} parkovísk",
        byPrice="{n} parkovísk · najlacnejšie prvé", byDistance="{n} parkovísk · najbližšie prvé",
        checked="Ceny overené 21. aug 2026", trip="Dĺžka cesty", days="dní",
        total="Spolu za {n} dní", perDay="/ deň", shortStay="krátkodobá tarifa",
        verified="Cena overená {d}", est="cca", details="Detaily", one="1 parkovisko"),
}

def load_prices() -> list[dict]:
    """Verified figures from data/prices.csv, in page order.

    A row only counts as verified when it carries checked_on: that is the
    difference between a figure someone read on the operator\'s site and a
    figure someone typed. Unverified rows keep whatever the page shows today.
    """
    path = ROOT / "data" / "prices.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        checked = (row.get("checked_on") or "").strip()
        frm = (row.get("from_ft_per_day") or "").strip()
        till = (row.get("till_ft_per_day") or "").strip()
        row["_verified"] = bool(checked and (frm or till))
        row["_from"] = frm
        row["_till"] = till
        row["_checked"] = checked
    return rows


DELTA = "M12 3.2l7.4 15.9-7.4-3.9-7.4 3.9z"


def text_of(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def inner_html(src: str, open_tag: str) -> str:
    """Content of the div that open_tag starts, found by balancing the tags.

    A non-greedy regex stops at the first </div>, which silently truncates any
    block containing nested divs — that mistake emptied every card body once.
    """
    at = src.find(open_tag)
    if at == -1:
        return ""
    start = at + len(open_tag)
    depth, i = 1, start
    for m in re.finditer(r"<div\b|</div>", src[start:]):
        depth += 1 if m.group(0) != "</div>" else -1
        if depth == 0:
            return src[start:start + m.start()].strip()
        i = m.end()
    return src[start:].strip()


def outer_html(src: str, open_tag: str) -> str:
    """The whole element, opening and closing tags included."""
    at = src.find(open_tag)
    if at == -1:
        return ""
    start = at + len(open_tag)
    depth = 1
    for m in re.finditer(r"<div\b|</div>", src[start:]):
        depth += 1 if m.group(0) != "</div>" else -1
        if depth == 0:
            return src[at:start + m.end()]
    return src[at:]


# ---------------------------------------------------------------- palette ---
PALETTE = [
    ("--white: #ffffff;", "--white: #FFFFFF;"),
    ("--snow: #f8fafc;", "--snow: #F7F9FC;"),
    ("--cloud: #f1f5f9;", "--cloud: #EDF1F5;"),
    ("--mist: #e2e8f0;", "--mist: #DDE3EA;"),
    ("--slate: #94a3b8;", "--slate: #8A97A6;"),
    ("--gray: #64748b;", "--gray: #5B6B7C;"),
    ("--dark: #1e293b;", "--dark: #33414F;"),
    ("--midnight: #0f172a;", "--midnight: #0B1F33;"),
    ("--sky: #0ea5e9;", "--sky: #0B5FCE;"),
    ("--sky-light: #e0f2fe;", "--sky-light: #E8F0FB;"),
    ("--sky-dark: #0284c7;", "--sky-dark: #094BA3;"),
    ("--gold: #f59e0b;", "--gold: #A8641A;"),
    ("--gold-light: #fef3c7;", "--gold-light: #F6EEE2;"),
    ("--gold-dark: #d97706;", "--gold-dark: #8A5214;"),
    ("--emerald: #10b981;", "--emerald: #0E7C5A;"),
    ("--emerald-light: #d1fae5;", "--emerald-light: #E3F3EC;"),
    ("--rose: #f43f5e;", "--rose: #C0392B;"),
    ("--violet: #8b5cf6;", "--violet: #0B5FCE;"),
    ("--violet-light: #ede9fe;", "--violet-light: #E8F0FB;"),
    ("--radius-sm: 8px;", "--radius-sm: 6px;"),
    ("--radius-md: 12px;", "--radius-md: 8px;"),
    ("--radius-lg: 16px;", "--radius-lg: 10px;"),
    ("--radius-xl: 24px;", "--radius-xl: 12px;"),
]

FONTS_OLD = ("https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700"
             "&family=Fraunces:opsz,wght@9..144,600;9..144,700&display=swap")
FONTS_NEW = "https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700&display=swap"

# CSS for the styles the redesign introduces. Appended so it wins over the
# older rules it supersedes; the card rules it replaces are deleted below.
NEW_CSS = """
        /* ============ RESULTS: toolbar, list, filter sheet ============ */
        .results-toolbar {
            position: sticky;
            top: var(--header-h);
            z-index: 90;
            background: var(--white);
            border-bottom: 1px solid var(--mist);
            padding: 0.75rem 1.5rem 0.6rem;
            display: flex;
            flex-direction: column;
            gap: 0.6rem;
        }

        .trip-row { display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; }

        .trip-label {
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.09em;
            text-transform: uppercase;
            color: var(--slate);
        }

        .trip-select {
            font: inherit;
            font-size: 0.95rem;
            font-weight: 600;
            color: var(--midnight);
            background: var(--white);
            border: 1.5px solid var(--mist);
            border-radius: var(--radius-sm);
            padding: 0.4rem 0.6rem;
            min-height: 44px;
            cursor: pointer;
        }

        .trip-unit { font-size: 0.9rem; color: var(--gray); font-weight: 500; }

        .search-row { display: flex; gap: 0.5rem; align-items: center; }

        .search-field {
            flex: 1 1 auto;
            min-width: 0;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            height: 46px;
            padding: 0 0.8rem;
            border: 1.5px solid var(--mist);
            border-radius: var(--radius-sm);
            background: var(--white);
        }

        .search-field:focus-within { border-color: var(--sky); }

        .search-field input {
            flex: 1 1 auto;
            min-width: 0;
            border: none;
            outline: none;
            font: inherit;
            font-size: 0.95rem;
            color: var(--midnight);
            background: transparent;
        }

        .filter-open {
            flex: 0 0 auto;
            display: flex;
            align-items: center;
            gap: 0.45rem;
            height: 46px;
            padding: 0 0.9rem;
            border: 1.5px solid var(--mist);
            border-radius: var(--radius-sm);
            background: var(--white);
            font: inherit;
            font-size: 0.9rem;
            font-weight: 600;
            color: var(--midnight);
            cursor: pointer;
        }

        .filter-open[data-active="true"] { border-color: var(--sky); background: var(--sky-light); color: var(--sky); }

        .filter-open .filter-count {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 20px;
            height: 20px;
            padding: 0 5px;
            border-radius: 10px;
            background: var(--sky);
            color: var(--white);
            font-size: 0.72rem;
            font-weight: 700;
        }

        .sort-seg { display: flex; gap: 3px; padding: 3px; background: var(--cloud); border-radius: var(--radius-sm); }

        .sort-btn {
            flex: 1 1 0;
            min-height: 40px;
            border: none;
            background: transparent;
            border-radius: 5px;
            font: inherit;
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--gray);
            cursor: pointer;
        }

        .sort-btn[aria-pressed="true"] {
            background: var(--white);
            color: var(--midnight);
            box-shadow: 0 1px 2px rgba(11, 31, 51, 0.10);
        }

        .active-chips { display: flex; gap: 0.4rem; overflow-x: auto; scrollbar-width: none; }
        .active-chips::-webkit-scrollbar { display: none; }
        .active-chips:empty { display: none; }

        .active-chips button {
            flex: 0 0 auto;
            display: flex;
            align-items: center;
            gap: 0.35rem;
            height: 34px;
            padding: 0 0.6rem;
            border: none;
            border-radius: var(--radius-sm);
            background: var(--sky-light);
            color: var(--sky);
            font: inherit;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
        }

        .results-summary {
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            gap: 0.6rem;
            font-size: 0.8rem;
        }

        .results-summary .count { font-weight: 600; color: var(--midnight); }
        .results-summary .checked { color: var(--slate); font-size: 0.72rem; }

        /* One surface with hairline dividers reads better than many cards. */
        .results-list {
            max-width: 900px;
            margin: 1.25rem auto 0;
            background: var(--white);
            border: 1px solid var(--mist);
            border-radius: var(--radius-md);
            overflow: hidden;
        }

        .lot { border-bottom: 1px solid var(--cloud); }
        .lot:last-child { border-bottom: none; }
        .lot.hidden { display: none; }
        .lot[data-cheapest="true"] { background: #F3F8F5; box-shadow: inset 3px 0 0 var(--emerald); }

        .lot-row { display: flex; align-items: center; gap: 0.4rem; padding: 0.65rem 0.25rem 0.65rem 0.75rem; }

        .lot-main { flex: 1 1 auto; min-width: 0; }

        .lot-tag {
            display: inline-block;
            font-size: 0.6rem;
            font-weight: 700;
            letter-spacing: 0.07em;
            text-transform: uppercase;
            padding: 2px 6px;
            border-radius: 3px;
            margin-bottom: 3px;
        }

        .lot-tag.official { color: var(--sky); background: var(--sky-light); }
        .lot-tag.cheapest { color: var(--emerald); background: var(--emerald-light); }

        .lot-name {
            font-size: 0.97rem;
            font-weight: 600;
            color: var(--midnight);
            margin: 0;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .lot-meta {
            margin: 3px 0 0;
            font-size: 0.75rem;
            color: var(--gray);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .lot-est {
            display: inline-block;
            font-size: 0.62rem;
            font-weight: 600;
            color: var(--gray);
            border: 1px solid var(--mist);
            padding: 0 4px;
            border-radius: 3px;
            margin-left: 0.35rem;
        }

        /* Read from the operator's own site on a known date. */
        .lot-checked {
            display: inline-flex;
            align-items: center;
            gap: 3px;
            font-size: 0.62rem;
            font-weight: 600;
            color: var(--emerald);
            background: var(--emerald-light);
            padding: 1px 5px;
            border-radius: 3px;
            margin-left: 0.35rem;
            white-space: nowrap;
        }

        /* Fixed width so prices form a column the eye can run down. Wide
           enough for a three-week total, and clipped rather than allowed to
           overflow back over the lot name. */
        .lot-price { flex: 0 0 116px; min-width: 0; text-align: right; overflow: hidden; }
        .lot-total { font-size: 0.94rem; font-weight: 700; color: var(--sky); letter-spacing: -0.01em; white-space: nowrap; }
        .lot-day { font-size: 0.68rem; color: var(--slate); font-weight: 500; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

        .lot-toggle {
            flex: 0 0 auto;
            width: 44px;
            height: 44px;
            border: none;
            background: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--slate);
        }

        .lot-toggle svg { transition: transform 0.2s ease; }
        .lot-toggle[aria-expanded="true"] svg { transform: rotate(90deg); }
        .lot-body { padding: 0 1rem 1rem; }
        .lot-body[hidden] { display: none; }

        /* ---- filter sheet ---- */
        .sheet-backdrop {
            position: fixed;
            inset: 0;
            background: rgba(11, 31, 51, 0.45);
            z-index: 1500;
        }

        .sheet-backdrop[hidden], .sheet[hidden] { display: none; }

        .sheet {
            position: fixed;
            left: 0;
            right: 0;
            bottom: 0;
            max-height: 88vh;
            z-index: 1600;
            background: var(--white);
            border-radius: 14px 14px 0 0;
            box-shadow: 0 -8px 24px rgba(11, 31, 51, 0.16);
            display: flex;
            flex-direction: column;
        }

        @media (min-width: 720px) {
            .sheet { left: 50%; right: auto; bottom: 5vh; width: 460px; transform: translateX(-50%); border-radius: 14px; }
        }

        .sheet-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.9rem 0.5rem 0.8rem 1.25rem;
            border-bottom: 1px solid var(--mist);
        }

        .sheet-head h2 { font-size: 1.05rem; font-weight: 700; color: var(--midnight); }

        .sheet-clear {
            min-height: 44px;
            padding: 0 0.75rem;
            border: none;
            background: none;
            font: inherit;
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--sky);
            cursor: pointer;
        }

        .sheet-body { flex: 1 1 auto; overflow-y: auto; padding: 0 1.25rem 0.5rem; }

        .sheet-group { padding-top: 1rem; }

        .sheet-group h3 {
            font-size: 0.68rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: var(--slate);
            margin-bottom: 0.5rem;
        }

        /* Whole row is the target, never just the box. */
        .sheet-opt {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            min-height: 48px;
            border-bottom: 1px solid var(--cloud);
            cursor: pointer;
        }

        .sheet-opt:last-child { border-bottom: none; }
        .sheet-opt input { position: absolute; opacity: 0; pointer-events: none; }

        .sheet-opt .box {
            flex: 0 0 auto;
            width: 22px;
            height: 22px;
            border: 1.5px solid var(--slate);
            border-radius: 5px;
            background: var(--white);
            display: flex;
            align-items: center;
            justify-content: center;
            color: transparent;
        }

        .sheet-opt input:checked + .box { border-color: var(--sky); background: var(--sky); color: var(--white); }
        .sheet-opt input:focus-visible + .box { outline: 3px solid var(--sky-dark); outline-offset: 2px; }
        .sheet-opt .label { flex: 1 1 auto; font-size: 0.92rem; color: var(--midnight); font-weight: 500; }
        .sheet-opt .n { flex: 0 0 auto; font-size: 0.8rem; color: var(--slate); font-weight: 600; }
        .sheet-opt[data-empty="true"] .label { color: var(--slate); }
        .sheet-opt[data-empty="true"] .box { border-color: var(--mist); background: var(--snow); }

        .sheet-foot { flex: 0 0 auto; padding: 0.8rem 1.25rem 1.25rem; border-top: 1px solid var(--mist); }

        .sheet-apply {
            width: 100%;
            min-height: 52px;
            border: none;
            border-radius: var(--radius-sm);
            background: var(--midnight);
            color: var(--white);
            font: inherit;
            font-size: 1rem;
            font-weight: 700;
            cursor: pointer;
        }

        /* German and Hungarian compounds ("Flughafennähe") are longer than a
           320px column; without this they paint straight past the viewport. */
        h1, h2, h3, h4, p, .section-title, .section-subtitle { overflow-wrap: break-word; }

        /* Long localized labels overflowed this header on a 320px screen. */
        .filter-bar-header { flex-wrap: wrap; gap: 0.5rem; }
        .filter-reset { white-space: normal; text-align: left; }

        @media (max-width: 768px) {
            .results-toolbar { padding: 0.7rem 1rem 0.55rem; }
            .results-list { border-radius: 0; border-left: none; border-right: none; margin: 1rem 0 0; }
        }
"""

# Card rules the list supersedes. The expanded body still uses .card-body,
# .card-features, .feature-tag, .card-description and .card-link.
DEAD_RULES = [".parking-grid", ".parking-card", ".card-header", ".card-title-group",
              ".card-title", ".card-location", ".card-price", ".price-from",
              ".price-value", ".price-period"]


def strip_dead_css(src: str) -> tuple[str, int]:
    removed = 0
    for sel in DEAD_RULES:
        pattern = re.compile(r"\n *" + re.escape(sel) + r"(?:[:.][\w-]+)?(?:,\s*[^{\n]+)? \{[^}]*\}")
        src, n = pattern.subn("", src)
        removed += n
    return src, removed


# ------------------------------------------------------------------ cards ---
def parse_km(location: str) -> float:
    """Distance in km from the lot's own location line; 999 when absent."""
    m = re.search(r"([\d]+(?:[.,][\d]+)?)\s*km", location)
    return float(m.group(1).replace(",", ".")) if m else 999.0


def parse_price(price_html: str) -> dict:
    flat = text_of(price_html)
    approx = "~" in flat
    unit = "5min" if "5min" in flat or "5 min" in flat else "day"
    m = re.search(r"([\d][\d\s.,]*)\s*Ft", flat)
    amount = int(re.sub(r"[^\d]", "", m.group(1))) if m else 0
    sep = " " if re.search(r"\d\s\d", flat) else ","
    return dict(amount=amount, unit=unit, approx=approx, sep=sep, text=flat)


def transform_cards(grid: str, strings: dict, prices: list[dict],
                    strict_names: bool = False) -> tuple[str, int, str]:
    chunks = grid.split('<div class="parking-card"')
    head, cards = chunks[0], chunks[1:]
    out, sep = [], ","

    for i, chunk in enumerate(cards, start=1):
        attrs, _, body = chunk.partition(">")
        data = dict(re.findall(r'data-(\w+)="([^"]*)"', attrs))

        name = re.search(r'class="card-title">(.*?)</h3>', body, re.S)
        loc = re.search(r'class="card-location">(.*?)</div>', body, re.S)
        price = re.search(r'class="price-value">(.*?)</div>', body, re.S)
        badge = re.search(r'class="card-type-badge (\w+)">(.*?)</span>', body, re.S)
        card_body = inner_html(body, '<div class="card-body">')

        name_t = text_of(name.group(1)) if name else ""
        loc_t = text_of(loc.group(1)).lstrip("📍").strip() if loc else ""
        p = parse_price(price.group(1)) if price else dict(amount=0, unit="day", approx=False, sep=",", text="")
        sep = p["sep"]
        km = parse_km(loc_t)

        haystack = " ".join([name_t, loc_t, text_of(card_body)]).lower()

        tag = ""
        if badge and badge.group(1) == "official":
            tag = '<span class="lot-tag official">%s</span>' % html.escape(
                text_of(badge.group(2)).lstrip("✈️ ").strip() or "Official")

        row = prices[i - 1] if i - 1 < len(prices) else {}
        # Position is the key: card order is identical across the language
        # pages. Names are only checked against English, the page the CSV was
        # generated from — a few lot names are localized elsewhere.
        if strict_names and row.get("lot") and row["lot"] != name_t:
            raise SystemExit("prices.csv row %d is %r but the page has %r"
                             % (i, row["lot"], name_t))

        verified = bool(row.get("_verified"))
        price_data = ""
        if verified:
            price_data = ' data-from="%s" data-till="%s" data-checked="%s"' % (
                row["_from"], row["_till"], html.escape(row["_checked"], quote=True))
            est = ('<span class="lot-checked" title="%s">'
                   '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor"'
                   ' stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
                   '<path d="M5 12.5l4.5 4.5L19 7"/></svg>%s</span>'
                   % (html.escape(strings["verified"].replace("{d}", row["_checked"]), quote=True),
                      html.escape(row["_checked"])))
        else:
            est = ('<span class="lot-est">%s</span>' % html.escape(strings["est"])) if p["approx"] else ""

        out.append(
            '            <article class="lot" data-type="%s" data-access="%s" data-features="%s"'
            ' data-amount="%d" data-unit="%s" data-approx="%s" data-km="%s"%s\n'
            '                     data-search="%s">\n'
            '                <div class="lot-row">\n'
            '                    <div class="lot-main">\n'
            '                        %s\n'
            '                        <h3 class="lot-name">%s</h3>\n'
            '                        <p class="lot-meta">%s%s</p>\n'
            '                    </div>\n'
            '                    <div class="lot-price">\n'
            '                        <div class="lot-total" data-total></div>\n'
            '                        <div class="lot-day" data-rate></div>\n'
            '                    </div>\n'
            '                    <button class="lot-toggle" type="button" aria-expanded="false"'
            ' aria-controls="lot-body-%d" aria-label="%s: %s">\n'
            '                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none"'
            ' stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"'
            ' aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>\n'
            '                    </button>\n'
            '                </div>\n'
            '                <div class="lot-body card-body" id="lot-body-%d" hidden>\n'
            '                    %s\n'
            '                </div>\n'
            '            </article>\n'
            % (data.get("type", ""), data.get("access", ""), data.get("features", ""),
               p["amount"], p["unit"], "1" if p["approx"] else "0",
               ("%g" % km), price_data,
               html.escape(haystack, quote=True),
               tag, html.escape(name_t), html.escape(loc_t), est,
               i, html.escape(strings["details"]), html.escape(name_t),
               i, card_body))

    return head + "\n" + "".join(out), len(cards), sep


# ---------------------------------------------------------------- toolbar ---
def extract_labels(src: str) -> dict:
    """Reuse the filter wording already translated on the page."""
    bar = src[src.index('<div class="filter-bar container">'):src.index('id="parkingGrid"')]
    opts = {}
    for m in re.finditer(r'<button class="filter-btn[^"]*" data-filter="(\w+)" data-value="([\w]+)"[^>]*>(.*?)</button>',
                         bar, re.S):
        # reuse the translation, drop the emoji the redesign replaces
        label = re.sub(r"^[^\w(]+", "", text_of(m.group(3))).strip()
        opts[(m.group(1), m.group(2))] = label
    groups = re.findall(r'class="filter-group-label">([^<]*)<', bar)
    reset = text_of(re.search(r'class="filter-reset"[^>]*>(.*?)</button>', bar, re.S).group(1))
    title = text_of(re.search(r'filter-bar-title">\s*<span>(.*?)</span>', bar, re.S).group(1))
    return dict(opts=opts, groups=groups, reset=reset, title=title)


def build_toolbar(s: dict, L: dict) -> str:
    return f"""        <div class="results-toolbar container">
            <div class="search-row">
                <div class="search-field">
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true" style="color: var(--slate); flex: 0 0 auto;"><circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/></svg>
                    <input type="search" id="lotSearch" autocomplete="off" placeholder="{html.escape(s['search'])}" aria-label="{html.escape(s['search'])}">
                </div>
                <button class="filter-open" id="filterOpen" type="button" aria-expanded="false" aria-controls="filterSheet">
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 6h16M7 12h10M10 18h4"/></svg>
                    <span>{html.escape(s['filters'])}</span>
                    <span class="filter-count" id="filterCount" hidden>0</span>
                </button>
            </div>

            <div class="sort-seg" role="group" aria-label="{html.escape(s['price'])} / {html.escape(s['distance'])}">
                <button class="sort-btn" type="button" data-sort="price" aria-pressed="true">{html.escape(s['price'])}</button>
                <button class="sort-btn" type="button" data-sort="distance" aria-pressed="false">{html.escape(s['distance'])}</button>
            </div>

            <div class="active-chips" id="activeChips"></div>

            <div class="results-summary">
                <span class="count" id="resultSummary"><span id="resultCount">33</span></span>
                <span class="checked">{html.escape(s['checked'])}</span>
            </div>
        </div>
"""


def build_sheet(s: dict, L: dict) -> str:
    o = L["opts"]
    g = L["groups"] + ["", "", ""]

    def opt(kind, value, label):
        return (f'                    <label class="sheet-opt" data-kind="{kind}" data-value="{value}">\n'
                f'                        <input type="checkbox" data-kind="{kind}" data-value="{value}">\n'
                f'                        <span class="box" aria-hidden="true"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7"/></svg></span>\n'
                f'                        <span class="label">{html.escape(label)}</span>\n'
                f'                        <span class="n" data-count>0</span>\n'
                f'                    </label>\n')

    type_opts = "".join(opt("type", v, o.get(("type", v), v))
                        for v in ("official", "offsite") if ("type", v) in o)
    access_opts = "".join(opt("access", v, o.get(("access", v), v))
                          for v in ("walking", "shuttle") if ("access", v) in o)
    feat_opts = "".join(opt("feature", v, o.get(("feature", v), v))
                        for v in ("24h", "ev", "carwash", "covered") if ("feature", v) in o)

    return f"""    <div class="sheet-backdrop" id="filterBackdrop" hidden></div>
    <div class="sheet" id="filterSheet" role="dialog" aria-modal="true" aria-labelledby="filterSheetTitle" hidden>
        <div class="sheet-head">
            <h2 id="filterSheetTitle">{html.escape(s['filters'])}</h2>
            <button class="sheet-clear" id="filterClear" type="button">{html.escape(L['reset'])}</button>
        </div>
        <div class="sheet-body">
            <div class="sheet-group">
                <h3>{html.escape(g[0])}</h3>
{type_opts}            </div>
            <div class="sheet-group">
                <h3>{html.escape(g[1])}</h3>
{access_opts}            </div>
            <div class="sheet-group">
                <h3>{html.escape(g[2])}</h3>
{feat_opts}            </div>
        </div>
        <div class="sheet-foot">
            <button class="sheet-apply" id="filterApply" type="button">{html.escape(s['show']).replace('{n}', '<span id="applyCount">0</span>')}</button>
        </div>
    </div>
"""


# --------------------------------------------------------------------- JS ---
JS = r"""    <script>
    (function (w, d) {
        'use strict';

        var T = __STRINGS__;
        var SEP = '__SEP__';
        var CARD_LIMIT_REMOVED = true;

        function byId(id) { return d.getElementById(id); }
        function fmt(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, SEP); }
        function fill(tpl, n) { return tpl.replace('{n}', fmt(n)); }

        /* ============ HEADER HEIGHT ============ */
        var header = d.querySelector('header');
        function syncHeaderHeight() {
            if (!header) return;
            d.documentElement.style.setProperty(
                '--header-h', Math.round(header.getBoundingClientRect().height) + 'px');
        }
        syncHeaderHeight();
        w.addEventListener('resize', syncHeaderHeight);
        if (w.ResizeObserver && header) new ResizeObserver(syncHeaderHeight).observe(header);

        /* ============ MOBILE MENU ============ */
        var mobileMenu = byId('mobileMenu');
        var mobileToggle = d.querySelector('.mobile-toggle');
        function setMobileMenu(open) {
            if (!mobileMenu) return;
            mobileMenu.classList.toggle('active', open);
            if (mobileToggle) mobileToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        }
        function toggleMobileMenu() {
            setMobileMenu(!(mobileMenu && mobileMenu.classList.contains('active')));
        }

        /* ============ RESULTS ============ */
        var lots = Array.prototype.slice.call(d.querySelectorAll('.lot'));
        var list = byId('parkingGrid');
        var searchInput = byId('lotSearch');
        var summary = byId('resultSummary');
        var noResults = byId('noResults');

        var state = { sort: 'price', q: '', type: [], access: [], feature: [] };

        /* The daily rate as the operator publishes it. Multiplying it out over
           a trip would be a guess: several operators price in tiers, and this
           site does not hold those tiers. Lots on a per-5-minute drop-off
           tariff have no daily rate to compare at all. */
        function dailyRate(lot) {
            if (lot.dataset.unit !== 'day') return null;
            var from = parseInt(lot.dataset.from, 10);
            if (lot.dataset.checked && !isNaN(from)) return from;
            return parseInt(lot.dataset.amount, 10) || 0;
        }

        function matchesFacets(lot, skipKind) {
            var kinds = ['type', 'access', 'feature'];
            for (var i = 0; i < kinds.length; i++) {
                var k = kinds[i];
                if (k === skipKind) continue;
                var picked = state[k];
                if (!picked.length) continue;
                if (k === 'feature') {
                    var have = (lot.dataset.features || '').split(',');
                    for (var j = 0; j < picked.length; j++) {
                        if (have.indexOf(picked[j]) === -1) return false;
                    }
                } else if (picked.indexOf(lot.dataset[k]) === -1) {
                    return false;
                }
            }
            return true;
        }

        function matchesQuery(lot) {
            return !state.q || (lot.dataset.search || '').indexOf(state.q) !== -1;
        }

        function visibleLots() {
            return lots.filter(function (lot) { return matchesFacets(lot) && matchesQuery(lot); });
        }

        /* Where an operator's own site was read, show the spread between the
           long-stay and one-day per-day rates. Anything unverified keeps the
           single figure the page already published. */
        function renderPrices() {
            lots.forEach(function (lot) {
                var main = lot.querySelector('[data-total]');
                var unit = lot.querySelector('[data-rate]');
                var amount = parseInt(lot.dataset.amount, 10) || 0;
                var approx = lot.dataset.approx === '1' ? '~' : '';
                var from = parseInt(lot.dataset.from, 10);
                var till = parseInt(lot.dataset.till, 10);
                var hasRange = lot.dataset.checked && !isNaN(from) && !isNaN(till);

                if (hasRange) {
                    main.textContent = from === till
                        ? fmt(from) + ' Ft'
                        : fmt(from) + '\u2013' + fmt(till) + ' Ft';
                    unit.textContent = T.perDay;
                    lot.setAttribute('data-range', from === till ? 'single' : 'range');
                } else if (lot.dataset.checked && !isNaN(from)) {
                    main.textContent = fmt(from) + ' Ft';
                    unit.textContent = T.perDay;
                } else {
                    main.textContent = approx + fmt(amount) + ' Ft';
                    unit.textContent = lot.dataset.unit === 'day' ? T.perDay : T.shortStay;
                }
            });
        }

        /* Not `parseFloat(x) || 999` — a lot at 0 km is falsy and would sort
           as if it were the furthest away. */
        function km(lot) {
            var v = parseFloat(lot.dataset.km);
            return isNaN(v) ? 999 : v;
        }

        function sortLots() {
            /* Sort the array in place, not a copy: everything downstream
               (which lot is cheapest, chip counts) reads this order. */
            lots.sort(function (a, b) {
                if (state.sort === 'distance') {
                    return km(a) - km(b);
                }
                var ta = dailyRate(a), tb = dailyRate(b);
                /* Short-stay tariffs have no daily rate: keep them last. */
                if (ta === null && tb === null) return 0;
                if (ta === null) return 1;
                if (tb === null) return -1;
                return ta - tb;
            });
            lots.forEach(function (lot) { list.appendChild(lot); });
        }

        function renderChips() {
            var wrap = byId('activeChips');
            if (!wrap) return;
            wrap.textContent = '';
            ['type', 'access', 'feature'].forEach(function (kind) {
                state[kind].forEach(function (value) {
                    var input = d.querySelector('.sheet-opt input[data-kind="' + kind + '"][data-value="' + value + '"]');
                    var label = input ? input.parentNode.querySelector('.label').textContent : value;
                    var b = d.createElement('button');
                    b.type = 'button';
                    b.textContent = label;
                    b.setAttribute('aria-label', label);
                    var x = d.createElementNS('http://www.w3.org/2000/svg', 'svg');
                    x.setAttribute('width', '12'); x.setAttribute('height', '12');
                    x.setAttribute('viewBox', '0 0 24 24'); x.setAttribute('fill', 'none');
                    x.setAttribute('stroke', 'currentColor'); x.setAttribute('stroke-width', '2.6');
                    x.setAttribute('aria-hidden', 'true');
                    var p = d.createElementNS('http://www.w3.org/2000/svg', 'path');
                    p.setAttribute('d', 'M6 6l12 12M18 6L6 18');
                    p.setAttribute('stroke-linecap', 'round');
                    x.appendChild(p); b.appendChild(x);
                    b.addEventListener('click', function () { toggleFacet(kind, value, false); });
                    wrap.appendChild(b);
                });
            });
        }

        /* Counts show what a tap would leave, so no option is a dead end. */
        function renderCounts() {
            d.querySelectorAll('.sheet-opt').forEach(function (opt) {
                var kind = opt.dataset.kind, value = opt.dataset.value;
                var n = lots.filter(function (lot) {
                    if (!matchesFacets(lot, kind) || !matchesQuery(lot)) return false;
                    if (kind === 'feature') return (lot.dataset.features || '').split(',').indexOf(value) !== -1;
                    return lot.dataset[kind] === value;
                }).length;
                var cell = opt.querySelector('[data-count]');
                if (cell) cell.textContent = n;
                opt.setAttribute('data-empty', n === 0 ? 'true' : 'false');
            });
        }

        function apply() {
            renderPrices();
            sortLots();

            var shown = visibleLots();
            lots.forEach(function (lot) {
                lot.classList.toggle('hidden', shown.indexOf(lot) === -1);
                lot.removeAttribute('data-cheapest');
            });

            if (state.sort === 'price') {
                for (var i = 0; i < shown.length; i++) {
                    if (dailyRate(shown[i]) !== null) { shown[i].setAttribute('data-cheapest', 'true'); break; }
                }
            }

            var tpl = state.sort === 'distance' ? T.byDistance : T.byPrice;
            if (summary) summary.textContent = shown.length === 1 ? T.one : fill(tpl, shown.length);
            var legacy = byId('resultCount');
            if (legacy) legacy.textContent = shown.length;
            if (noResults) noResults.classList.toggle('visible', shown.length === 0);

            var n = state.type.length + state.access.length + state.feature.length;
            var badge = byId('filterCount'), open = byId('filterOpen');
            if (badge) { badge.textContent = n; badge.hidden = n === 0; }
            if (open) open.setAttribute('data-active', n > 0 ? 'true' : 'false');
            var applyCount = byId('applyCount');
            if (applyCount) applyCount.textContent = fmt(shown.length);

            renderCounts();
            renderChips();
        }

        function toggleFacet(kind, value, on) {
            var arr = state[kind];
            var at = arr.indexOf(value);
            if (on && at === -1) arr.push(value);
            if (!on && at !== -1) arr.splice(at, 1);
            var input = d.querySelector('.sheet-opt input[data-kind="' + kind + '"][data-value="' + value + '"]');
            if (input) input.checked = on;
            apply();
        }

        d.querySelectorAll('.sheet-opt input').forEach(function (input) {
            input.addEventListener('change', function () {
                toggleFacet(this.dataset.kind, this.dataset.value, this.checked);
            });
        });

        d.querySelectorAll('.sort-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                d.querySelectorAll('.sort-btn').forEach(function (b) { b.setAttribute('aria-pressed', 'false'); });
                this.setAttribute('aria-pressed', 'true');
                state.sort = this.dataset.sort;
                apply();
            });
        });

        if (searchInput) {
            searchInput.addEventListener('input', function () {
                state.q = this.value.trim().toLowerCase();
                apply();
            });
        }

        d.querySelectorAll('.lot-toggle').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var body = byId(this.getAttribute('aria-controls'));
                var open = this.getAttribute('aria-expanded') === 'true';
                this.setAttribute('aria-expanded', open ? 'false' : 'true');
                if (body) body.hidden = open;
            });
        });

        /* ---- sheet ---- */
        var sheet = byId('filterSheet'), backdrop = byId('filterBackdrop'), opener = byId('filterOpen');
        function setSheet(open) {
            if (!sheet) return;
            sheet.hidden = !open;
            if (backdrop) backdrop.hidden = !open;
            if (opener) opener.setAttribute('aria-expanded', open ? 'true' : 'false');
            if (open) { var f = sheet.querySelector('input'); if (f) f.focus(); }
            else if (opener) opener.focus();
        }
        if (opener) opener.addEventListener('click', function () { setSheet(sheet.hidden); });
        if (backdrop) backdrop.addEventListener('click', function () { setSheet(false); });
        var applyBtn = byId('filterApply');
        if (applyBtn) applyBtn.addEventListener('click', function () { setSheet(false); });
        var clearBtn = byId('filterClear');
        if (clearBtn) {
            clearBtn.addEventListener('click', function () {
                state.type = []; state.access = []; state.feature = [];
                d.querySelectorAll('.sheet-opt input').forEach(function (i) { i.checked = false; });
                apply();
            });
        }

        d.addEventListener('keydown', function (e) {
            if (e.key !== 'Escape') return;
            setMobileMenu(false);
            if (sheet && !sheet.hidden) setSheet(false);
        });

        /* ============ SERVICES ============ */
        var serviceCards = d.querySelectorAll('.service-card');
        var serviceCategoryButtons = d.querySelectorAll('.service-filter-btn:not(.service-location-btn)');
        var serviceLocationButtons = d.querySelectorAll('.service-location-btn');
        var activeServiceCategory = 'all', activeServiceLocation = 'all';

        function setPressed(btn, pressed) {
            btn.classList.toggle('active', pressed);
            btn.setAttribute('aria-pressed', pressed ? 'true' : 'false');
        }

        /* Services keep their card layout and their 6-item cap; this redesign
           is scoped to the parking results. */
        function showAllServicesLabel(total, more) { return __SHOW_ALL_SERVICES__; }

        var SERVICE_LIMIT = 6;
        var showAllServicesEnabled = false;

        function applyServiceFilters() {
            var capped = !showAllServicesEnabled;
            var shown = 0, matching = 0;

            serviceCards.forEach(function (card) {
                var okCat = activeServiceCategory === 'all' || card.dataset.category === activeServiceCategory;
                var okLoc = activeServiceLocation === 'all' || (card.dataset.location || 'nearby') === activeServiceLocation;
                var visible = false;
                if (okCat && okLoc) {
                    matching++;
                    visible = !(capped && shown >= SERVICE_LIMIT);
                    if (visible) shown++;
                }
                card.classList.toggle('hidden', !visible);
                card.style.display = visible ? '' : 'none';
            });

            byId('serviceResultCount').textContent = matching;
            byId('noServiceResults').classList.toggle('visible', matching === 0);

            var c = byId('showAllServicesContainer');
            if (c) {
                var offer = capped && matching > SERVICE_LIMIT;
                c.style.display = offer ? 'block' : 'none';
                var btn = c.querySelector('button');
                if (offer && btn) btn.textContent = showAllServicesLabel(matching, matching - SERVICE_LIMIT);
            }
        }

        function showAllServices() {
            showAllServicesEnabled = true;
            applyServiceFilters();
        }

        serviceCategoryButtons.forEach(function (btn) {
            setPressed(btn, btn.classList.contains('active'));
            btn.addEventListener('click', function () {
                serviceCategoryButtons.forEach(function (b) { setPressed(b, false); });
                setPressed(this, true);
                activeServiceCategory = this.dataset.category;
                showAllServicesEnabled = false;
                applyServiceFilters();
            });
        });

        serviceLocationButtons.forEach(function (btn) {
            setPressed(btn, btn.classList.contains('active'));
            btn.addEventListener('click', function (e) {
                e.stopPropagation();
                serviceLocationButtons.forEach(function (b) { setPressed(b, false); });
                setPressed(this, true);
                activeServiceLocation = this.dataset.location;
                showAllServicesEnabled = false;
                applyServiceFilters();
            });
        });

        function resetServiceFilters() {
            activeServiceCategory = 'all'; activeServiceLocation = 'all'; showAllServicesEnabled = false;
            serviceCategoryButtons.forEach(function (b) { setPressed(b, false); });
            serviceLocationButtons.forEach(function (b) { setPressed(b, false); });
            var ac = d.querySelector('.service-filter-btn[data-category="all"]');
            var al = d.querySelector('.service-location-btn[data-location="all"]');
            if (ac) setPressed(ac, true);
            if (al) setPressed(al, true);
            applyServiceFilters();
        }

        /* ============ TRANSPORT BAR ============ */
        var transportBarContent = byId('transportBarContent');
        var transportToggleButton = d.querySelector('.transport-toggle');
        function toggleTransportBar() {
            if (!transportBarContent) return;
            var open = transportBarContent.style.display === 'none';
            transportBarContent.style.display = open ? 'block' : 'none';
            var text = byId('transportToggleText'), icon = byId('transportToggleIcon');
            if (text) text.textContent = open ? T.transportHide : T.transportShow;
            if (icon) icon.classList.toggle('rotated', open);
            if (transportToggleButton) transportToggleButton.setAttribute('aria-expanded', open ? 'true' : 'false');
        }

        /* ============ IN-PAGE NAVIGATION ============ */
        d.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
            anchor.addEventListener('click', function (e) {
                var href = this.getAttribute('href');
                setMobileMenu(false);
                if (!href || href === '#') {
                    e.preventDefault();
                    w.scrollTo({ top: 0, behavior: 'smooth' });
                    return;
                }
                var target = d.querySelector(href);
                if (!target) return;
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                if (target.hasAttribute('tabindex')) target.focus({ preventScroll: true });
                if (w.history && w.history.replaceState) w.history.replaceState(null, '', href);
            });
        });

        w.toggleMobileMenu = toggleMobileMenu;
        w.toggleTransportBar = toggleTransportBar;
        w.resetServiceFilters = resetServiceFilters;
        w.showAllServices = showAllServices;

        apply();
        applyServiceFilters();
    })(window, document);
    </script>
"""


def build_js(s: dict, sep: str, transport_show: str, transport_hide: str,
             show_all_services: str) -> str:
    import json
    strings = dict(perDay=s["perDay"], shortStay=s["shortStay"], byPrice=s["byPrice"],
                   byDistance=s["byDistance"], one=s["one"],
                   transportShow=transport_show, transportHide=transport_hide)
    return (JS.replace("__STRINGS__", json.dumps(strings, ensure_ascii=False))
              .replace("__SEP__", sep)
              .replace("__SHOW_ALL_SERVICES__", show_all_services))


# ---------------------------------------------------------------- assemble ---
LOGO_SVG = ('<svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor" '
            'aria-hidden="true"><path d="%s"/></svg>' % DELTA)


def build(rel: str) -> str:
    path = ROOT / rel
    src = path.read_text(encoding="utf-8")
    if 'class="lot"' in src:
        raise SystemExit("%s is already built — reset it from git first" % rel)
    s = S[rel]
    L = extract_labels(src)
    prices = load_prices()
    notes = []

    tshow = re.search(r"transportShow: '([^']*)'", src)
    thide = re.search(r"transportHide: '([^']*)'", src)
    sas = re.search(r"showAllServices: function \(total, more\) \{ return (.*?); \}", src)
    sas = sas.group(1) if sas else "'Show all ' + total + ' services'"
    tshow = tshow.group(1) if tshow else "Show Options"
    thide = thide.group(1) if thide else "Hide Options"

    # 1. typeface
    src = src.replace(FONTS_OLD, FONTS_NEW)
    src = src.replace("font-family: 'Plus Jakarta Sans', sans-serif;",
                      "font-family: 'Archivo', system-ui, sans-serif;")
    src = re.sub(r"font-family: 'Fraunces', serif;\s*", "", src)
    notes.append("typeface")

    # 2. palette
    for a, b in PALETTE:
        src = src.replace(a, b)
    notes.append("palette")

    # 3. flat mark instead of the gradient tile and the emoji glyph
    src = src.replace("background: linear-gradient(135deg, var(--sky), var(--violet));",
                      "background: var(--midnight);")
    src = src.replace('<div class="logo-icon">✈</div>',
                      '<div class="logo-icon" aria-hidden="true">%s</div>' % LOGO_SVG)
    notes.append("mark")

    # 4. stylesheet
    src, dead = strip_dead_css(src)
    src = src.replace("    </style>", NEW_CSS + "    </style>", 1)
    notes.append("css(-%d dead rules)" % dead)

    # 5. results section
    start = src.index('<section class="section parking-section" id="parking">')
    end = src.index("</section>", src.index('id="noResults"')) + len("</section>")
    section = src[start:end]

    header = outer_html(section, '<div class="section-header">')
    no_results = outer_html(section, '<div class="no-results container" id="noResults">')
    grid = section[section.index('<div class="parking-grid container" id="parkingGrid">'):
                   section.index('<div class="show-all-container')]
    rows, count, sep = transform_cards(grid, s, prices, strict_names=(rel == "index.html"))
    rows = rows.split("\n", 1)[1]  # drop the old opening div

    new_section = (
        '    <section class="section results-section" id="parking">\n'
        '        %s\n'
        '%s\n'
        '        <div class="results-list" id="parkingGrid">\n'
        '%s'
        '        </div>\n\n'
        '        %s'
        '    </section>' % (header, build_toolbar(s, L), rows, no_results + "\n\n")
    )
    src = src[:start] + new_section + src[end:]
    notes.append("%d lots" % count)

    # 6. filter sheet
    src = src.replace("    </main>", build_sheet(s, L) + "    </main>", 1)
    notes.append("filter sheet")

    # 7. runtime
    anchor = "    <script>\n    (function () {"
    if anchor not in src:
        raise SystemExit("%s: page runtime not found where expected" % rel)
    js_start = src.index(anchor)
    if "ParkBUDConsent" in src[js_start:js_start + 4000]:
        raise SystemExit("%s: refusing to overwrite the consent gate" % rel)
    js_end = src.index("    </script>", js_start) + len("    </script>\n")
    src = src[:js_start] + build_js(s, sep, tshow, thide, sas) + src[js_end:]
    notes.append("runtime")

    path.write_text(src, encoding="utf-8")
    return "; ".join(notes)


if __name__ == "__main__":
    for rel in PAGES:
        print("%-16s %s" % (rel, build(rel)))
