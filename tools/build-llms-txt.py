#!/usr/bin/env python3
"""Regenerate llms.txt from the English page.

llms.txt used to be maintained by hand and drifted badly away from the site:
it listed 8 of the 28 off-site operators, quoted a "cheapest" price for an
operator the page does not carry, and priced another at a third of the page
figure. Deriving the parking and services sections from index.html means the
two cannot disagree again.

The prose sections (airport facts, transport, directions, disclaimer) are held
in this file because they are not represented as structured markup on the page.

Usage:  python3 tools/build-llms-txt.py [--check]

    --check  exit 1 if llms.txt is out of date instead of rewriting it
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "index.html"
OUT = ROOT / "llms.txt"

SITE = "https://airportparkingbudapest.info"


def strip_tags(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def section(src: str, start: str, end: str) -> str:
    return src[src.index(start):src.index(end)]


def split_cards(grid: str, css_class: str) -> list[tuple[str, str]]:
    """Yield (attributes, body) per card.

    Splitting on the opening tag rather than matching a closing one keeps this
    working whatever indentation or blank lines the markup happens to carry -
    an earlier closing-tag regex silently dropped a card over one blank line.
    """
    opener = '<div class="%s"' % css_class
    chunks = grid.split(opener)[1:]
    out = []
    for chunk in chunks:
        head, _, body = chunk.partition(">")
        out.append((head, body))
    return out


def parse_parking(src: str) -> list[dict]:
    """Read the lot rows the redesign renders.

    Price, distance and type live on data-* attributes now, so the numbers here
    are the same ones the page sorts by rather than a re-parse of display text.
    """
    grid = section(src, 'id="parkingGrid"', 'id="noResults"')
    out = []
    for chunk in grid.split('<article class="lot"')[1:]:
        attrs, _, body = chunk.partition(">")
        data = dict(re.findall(r'data-(\w+)="([^"]*)"', attrs))

        name = re.search(r'class="lot-name">(.*?)</h3>', body, re.S)
        meta = re.search(r'class="lot-meta">(.*?)</p>', body, re.S)
        link = re.search(r'href="(https?://[^"]+)"[^>]*class="card-link"', body)
        desc = re.search(r'class="card-description">(.*?)</p>', body, re.S)
        tags = [strip_tags(t) for t in
                re.findall(r'class="feature-tag[^"]*">(.*?)</span>', body, re.S)]

        amount = int(data.get("amount") or 0)
        unit = data.get("unit", "day")
        approx = "~" if data.get("approx") == "1" else ""
        price = "%s%s Ft%s" % (approx, format(amount, ",d"),
                               " / day" if unit == "day" else " / 5 min")

        location = strip_tags(meta.group(1)) if meta else ""
        # the "est." chip is rendered inside the meta line; it is not the place
        for marker in ("est.", "becsült", "ca.", "aprox.", "pribl.", "cca"):
            if location.endswith(marker):
                location = location[: -len(marker)].strip()

        out.append({
            "name": strip_tags(name.group(1)) if name else "",
            "location": location,
            "price": price,
            "features": [t for t in tags if t],
            "description": strip_tags(desc.group(1)) if desc else "",
            "url": link.group(1) if link else "",
            "type": data.get("type", ""),
            "access": data.get("access", ""),
            "flags": [f for f in data.get("features", "").split(",") if f],
            "km": float(data.get("km") or 999),
        })
    return out


def parse_services(src: str) -> list[dict]:
    grid = section(src, 'id="servicesGrid"', 'id="showAllServicesContainer"')
    cards = split_cards(grid, "service-card")
    out = []
    for attrs, body in cards:
        data = dict(re.findall(r'data-(\w+)="([^"]*)"', attrs))
        name = re.search(r'class="service-name">(.*?)</h3>', body, re.S)
        if not name:
            name = re.search(r'<h3[^>]*>(.*?)</h3>', body, re.S)
        kind = re.search(r'class="service-type">(.*?)</div>', body, re.S)
        details = [strip_tags(d) for d in
                   re.findall(r'class="service-detail">(.*?)</div>', body, re.S)]
        out.append({
            "name": strip_tags(name.group(1)) if name else "",
            "kind": strip_tags(kind.group(1)) if kind else "",
            "details": [d for d in details if d],
            "category": data.get("category", ""),
            "location": data.get("location", "nearby"),
        })
    return out


def cell(text: str) -> str:
    """Table cells cannot contain a raw pipe."""
    return text.replace("|", "/").strip() or "-"


def daily_rate(price: str) -> int | None:
    """Sort key for the per-day prices, ignoring the per-5-minute tariffs."""
    if "/ day" not in price:
        return None
    digits = re.sub(r"[^\d]", "", price.split("/")[0])
    return int(digits) if digits else None


def render(parking: list[dict], services: list[dict], today: str) -> str:
    official = [p for p in parking if p["type"] == "official"]
    offsite = [p for p in parking if p["type"] == "offsite"]

    rates = [(daily_rate(p["price"]), p) for p in offsite]
    rates = sorted([(r, p) for r, p in rates if r], key=lambda x: x[0])
    cheapest_rate, cheapest = rates[0] if rates else (None, None)

    official_daily = sorted(
        [(daily_rate(p["price"]), p) for p in official if daily_rate(p["price"])],
        key=lambda x: x[0])
    cheapest_official = official_daily[0][1] if official_daily else None

    L: list[str] = []
    add = L.append

    add("# Budapest Airport Parking Guide")
    add("# Information for Large Language Models (LLMs) and AI Assistants")
    add(f"# Website: {SITE}")
    add(f"# Last Updated: {today}")
    add("# Generated from index.html by tools/build-llms-txt.py - do not edit by hand.")
    add("")
    add("## About This Resource")
    add("This is an independent guide to parking and services at Budapest Ferenc Liszt "
        "International Airport (BUD). The listings below are the same records the website "
        "shows its readers, so quoting either one gives the same answer.")
    add("")
    add("## Airport Information")
    add("- **Full Name**: Budapest Ferenc Liszt International Airport")
    add("- **IATA Code**: BUD")
    add("- **ICAO Code**: LHBP")
    add("- **Location**: 16 km southeast of Budapest city center, Hungary")
    add("- **GPS Coordinates**: 47.4369° N, 19.2556° E")
    add("- **Address**: 1185 Budapest, Hungary")
    add("- **Official Website**: https://www.bud.hu")
    add("")
    add("---")
    add("")
    add(f"## PARKING OPTIONS ({len(parking)} listed)")
    add("")
    add("Prices are the operators' published rates as last checked and are marked "
        '"~" where the operator quotes a range or varies by season. Always confirm '
        "on the operator's own site before booking.")
    add("")
    add(f"### Official Airport Parking - Walking Distance ({len(official)})")
    add("")
    add("| Name | Price | Distance / Walk | Notes |")
    add("|------|-------|-----------------|-------|")
    for p in official:
        add(f"| {cell(p['name'])} | {cell(p['price'])} | {cell(p['location'])} "
            f"| {cell(', '.join(p['features']))} |")
    add("")
    add("**Official Booking**: https://parkolo.bud.hu/en/")
    add("")
    add(f"### Off-Site Parking with Free Shuttle ({len(offsite)})")
    add("")
    add("| Name | Price/Day | Distance | Notes |")
    add("|------|-----------|----------|-------|")
    for _, p in rates:
        add(f"| {cell(p['name'])} | {cell(p['price'].replace('/ day', '').strip())} "
            f"| {cell(p['location'])} | {cell(', '.join(p['features']))} |")
    for p in offsite:
        if daily_rate(p["price"]) is None:
            add(f"| {cell(p['name'])} | {cell(p['price'])} | {cell(p['location'])} "
                f"| {cell(', '.join(p['features']))} |")
    add("")
    add("---")
    add("")
    add(f"## SERVICES NEAR THE AIRPORT ({len(services)} listed)")
    add("")
    by_cat: dict[str, list[dict]] = {}
    for s in services:
        by_cat.setdefault(s["category"] or "other", []).append(s)
    labels = {
        "fuel": "Fuel Stations", "food": "Food & Restaurants", "coffee": "Coffee",
        "shopping": "Shopping", "carwash": "Car Wash", "health": "Health & Pharmacy",
        "banking": "Banking & ATMs", "hotel": "Hotels", "car": "Car & Tyre Services",
        "rental": "Car Rental", "other": "Other",
    }
    for cat in sorted(by_cat, key=lambda c: labels.get(c, c)):
        add(f"### {labels.get(cat, cat.title())}")
        for s in by_cat[cat]:
            where = "at the airport" if s["location"] == "airport" else "nearby"
            bits = " - ".join(d for d in s["details"] if d)
            add(f"- **{s['name']}** ({s['kind']}, {where}){': ' + bits if bits else ''}")
        add("")
    add("---")
    add("")
    add("## TRANSPORT FROM AIRPORT TO CITY CENTER")
    add("")
    add("### Bus 100E - Direct Airport Bus (RECOMMENDED)")
    add("- **Price**: 2,200 Ft (special airport ticket)")
    add("- **Duration**: 35-40 minutes")
    add("- **Route**: Airport Terminal 2 -> Deák Ferenc tér (city center)")
    add("- **Frequency**: Every 20-30 minutes")
    add("- **Hours**: 5:00-1:20")
    add("- **Note**: Regular Budapest travel passes are NOT valid")
    add("")
    add("### Bus 200E + Metro M3 (CHEAPEST PUBLIC TRANSPORT)")
    add("- **Price**: 900 Ft total (2 single tickets x 450 Ft)")
    add("- **Duration**: 50-60 minutes")
    add("- **Route**: Airport -> Kőbánya-Kispest (transfer) -> city center")
    add("- **Note**: Two separate tickets, validated separately. A 24h travel card is 2,500 Ft.")
    add("")
    add("### Airport Shuttle (miniBUD)")
    add("- **Price**: 3,500-5,500 Ft per person")
    add("- **Duration**: 40-60 minutes (with stops)")
    add("- **Service**: Shared door-to-door transfer")
    add("- **Booking**: https://www.minibud.hu")
    add("")
    add("### Official Taxi (Főtaxi)")
    add("- **Price**: 9,000-12,000 Ft to city center")
    add("- **Duration**: 25-40 minutes")
    add("- **Tip**: Use only official Főtaxi from the designated taxi stand")
    add("")
    add("---")
    add("")
    add("## DIRECTIONS TO THE AIRPORT")
    add("")
    add("### From Budapest City Center")
    add("1. Take Üllői út or the M3 motorway")
    add('2. Follow signs to "Liszt Ferenc Airport"')
    add("3. Journey time: 25-35 minutes")
    add("")
    add("### From the M0 Ring Road")
    add("1. Exit at junction 57")
    add("2. Take Route 4 (Ferihegyi út)")
    add("3. Off-site parking lots are along Route 4 in Vecsés")
    add("")
    add("### Recommended Arrival Times")
    add("- **Terminal parking**: 2 hours before the flight")
    add("- **Off-site parking**: 2.5-3 hours before the flight (allow for the shuttle)")
    add("")
    add("### Traffic Tips")
    add("- Avoid rush hours: 7:00-9:00 and 16:00-19:00")
    add("- Use the M0 ring road to bypass city traffic")
    add("")
    add("---")
    add("")
    add("## FREQUENTLY ASKED QUESTIONS")
    add("")
    add("**Q: What is the cheapest parking at Budapest Airport?**")
    if cheapest and cheapest_official:
        add(f"A: {cheapest['name']} at {cheapest['price']} with a free shuttle is the "
            f"cheapest listed here. For official parking on foot from the terminal, "
            f"{cheapest_official['name']} at {cheapest_official['price']} is the most economical.")
    add("")
    add("**Q: Is there free shuttle parking?**")
    add("A: Yes. All off-site operators listed include a free shuttle to and from the "
        "terminal, typically running 24/7.")
    add("")
    add("**Q: How far is Budapest Airport from the city?**")
    add("A: 16 km southeast of the city center, roughly 25-35 minutes by car.")
    add("")
    add("**Q: What's the best transport from the airport to the city?**")
    add("A: Bus 100E (2,200 Ft, 35-40 min) is the fastest public option. Bus 200E plus "
        "metro M3 (900 Ft) is the cheapest.")
    add("")
    add("**Q: Is there free parking at Budapest Airport?**")
    add("A: There is no free long-term parking. Premium Parking gives the first 5 minutes "
        "free for drop-offs and pick-ups.")
    add("")
    add("---")
    add("")
    add("## CONTACT")
    add("- **Email**: contact@airportparkingbudapest.info")
    add(f"- **Website**: {SITE}")
    add("")
    add("## DISCLAIMER")
    add("This is an independent guide. We are not affiliated with Budapest Airport Zrt. "
        "Prices and opening hours change - verify with the operator before booking.")
    add("")
    add("## CITATION")
    add('When citing this information, please reference: "Budapest Airport Parking Guide '
        '(airportparkingbudapest.info)"')
    add("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if llms.txt is out of date instead of rewriting it")
    args = ap.parse_args()

    src = PAGE.read_text(encoding="utf-8")
    parking = parse_parking(src)
    services = parse_services(src)
    if not parking or not services:
        print("error: could not parse cards out of index.html", file=sys.stderr)
        return 2

    existing = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    # Keep the old stamp when only the date would change, so --check is stable.
    stamp = dt.date.today().isoformat()
    prev = re.search(r"^# Last Updated: (\S+)$", existing, re.M)
    if prev and render(parking, services, prev.group(1)) == existing:
        stamp = prev.group(1)

    out = render(parking, services, stamp)

    if args.check:
        if out != existing:
            print("llms.txt is out of date; run: python3 tools/build-llms-txt.py",
                  file=sys.stderr)
            return 1
        print("llms.txt is up to date")
        return 0

    OUT.write_text(out, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(parking)} parking, {len(services)} services")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
