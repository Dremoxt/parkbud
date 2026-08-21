#!/usr/bin/env python3
"""Structural checks over the built site. No browser required.

Covers the classes of breakage this site has actually shipped: malformed
markup, references to files that do not exist, external links without
rel=noopener, analytics tags escaping the consent gate, and a sitemap
pointing at pages that are not there.

Usage:  python3 tests/static_checks.py
"""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://airportparkingbudapest.info"

LANG_PAGES = ["index.html", "hu/index.html", "de/index.html", "ro/index.html",
              "sr/index.html", "hr/index.html", "sk/index.html"]
ALL_PAGES = LANG_PAGES + ["404.html", "privacy/index.html"]

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print("FAIL: " + msg)


def ok(msg: str) -> None:
    print("ok:   " + msg)


class Nesting(HTMLParser):
    """Reports tags closed out of order and tags never closed."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, tuple[int, int]]] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append((tag, self.getpos()))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append("stray </%s> at line %d" % (tag, self.getpos()[0]))
            return
        if self.stack[-1][0] != tag:
            open_tag, open_pos = self.stack[-1]
            self.errors.append("</%s> at line %d closes <%s> opened at line %d"
                               % (tag, self.getpos()[0], open_tag, open_pos[0]))
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][0] == tag:
                    del self.stack[i:]
                    break
        else:
            self.stack.pop()


def check_markup(rel: str, src: str) -> None:
    parser = Nesting()
    parser.feed(src)
    parser.close()
    if parser.errors:
        fail("%s: %s" % (rel, "; ".join(parser.errors[:3])))
    elif parser.stack:
        fail("%s: unclosed %s" % (rel, ", ".join("<%s>" % t for t, _ in parser.stack[:3])))
    else:
        ok("%s markup nests correctly" % rel)


def check_local_references(rel: str, src: str) -> None:
    """Every root-relative asset and page link must exist on disk."""
    refs = set()
    for attr in ("href", "src"):
        refs |= set(re.findall(r'%s="(/[^"#?]*)"' % attr, src))
    for meta in re.findall(r'content="(%s/[^"]*)"' % re.escape(SITE), src):
        refs.add(meta[len(SITE):])

    missing = []
    for ref in sorted(refs):
        target = ROOT / ref.lstrip("/")
        if ref.endswith("/"):
            target = target / "index.html"
        if not target.exists():
            missing.append(ref)

    if missing:
        fail("%s references missing files: %s" % (rel, ", ".join(missing)))
    else:
        ok("%s: all %d local references resolve" % (rel, len(refs)))


def check_external_links(rel: str, src: str) -> None:
    """target=_blank without rel leaks the opener and the referrer."""
    bad = [tag for tag in re.findall(r'<a\b[^>]*target="_blank"[^>]*>', src)
           if "noopener" not in tag]
    if bad:
        fail("%s: %d target=_blank link(s) without rel=noopener" % (rel, len(bad)))
    else:
        ok("%s: every target=_blank link sets rel=noopener" % rel)


def check_json_ld(rel: str, src: str) -> None:
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', src, re.S)
    broken = 0
    for block in blocks:
        try:
            json.loads(block)
        except json.JSONDecodeError as exc:
            broken += 1
            fail("%s: invalid JSON-LD (%s)" % (rel, exc))
    if not broken:
        ok("%s: %d JSON-LD block(s) parse" % (rel, len(blocks)))


def check_analytics_gated(rel: str, src: str) -> None:
    """Analytics must never be a plain script tag in the markup."""
    hosts = ("googletagmanager.com", "google-analytics.com", "contentsquare.net")
    leaked = [tag for tag in re.findall(r"<script\b[^>]*\bsrc=[^>]*>", src)
              if any(host in tag for host in hosts)]
    if leaked:
        fail("%s: analytics loaded outside the consent gate: %s" % (rel, leaked[0]))
    else:
        ok("%s: no analytics tag bypasses the consent gate" % rel)


def check_no_derived_totals(rel: str, src: str) -> None:
    """Daily rates must not be multiplied out into trip totals.

    Several operators price in tiers and the site does not hold those tiers,
    so any multi-day total computed here would be a guess presented as a fact.
    """
    if 'id="tripNights"' in src or "state.nights" in src:
        fail("%s: a trip-length calculation is back" % rel)
    else:
        ok("%s: prices are shown as published, not multiplied out" % rel)


def check_results_ui(rel: str, src: str) -> None:
    """The controls the redesign depends on."""
    needed = {
        'id="lotSearch"': "search field",
        'data-sort="price"': "price sort",
        'data-sort="distance"': "distance sort",
        'id="filterSheet"': "filter sheet",
        'id="filterApply"': "apply button",
        'class="lot-toggle"': "row expander",
    }
    missing = [label for token, label in needed.items() if token not in src]
    if missing:
        fail("%s: results UI missing %s" % (rel, ", ".join(missing)))
    else:
        ok("%s: search, both sorts and filter sheet present" % rel)


def check_lot_data(rel: str, src: str) -> None:
    """Every lot needs the attributes the sorting reads."""
    lots = re.findall(r'<article class="lot"([^>]*)>', src)
    bad = [a for a in lots if not (re.search(r'data-amount="\d+"', a)
                                   and re.search(r'data-km="[\d.]+"', a)
                                   and re.search(r'data-unit="(day|5min)"', a))]
    if bad:
        fail("%s: %d lot(s) missing sort data" % (rel, len(bad)))
    else:
        ok("%s: all %d lots carry price and distance data" % (rel, len(lots)))


def check_content_preserved(rel: str, src: str) -> None:
    """The expandable body must still carry what the old card showed."""
    lots = len(re.findall(r'class="lot"[ >]', src))
    links = src.count('class="card-link"')
    descs = src.count('class="card-description"')
    if links < lots or descs < lots:
        fail("%s: %d lots but %d booking links and %d descriptions"
             % (rel, lots, links, descs))
    else:
        ok("%s: every lot kept its description and booking link" % rel)


def check_consent_wiring(rel: str, src: str) -> None:
    needed = {
        'id="cookieConsent"': "consent banner",
        "ParkBUDConsent.accept()": "accept control",
        "ParkBUDConsent.reject()": "decline control",
        'href="/privacy/"': "privacy policy link",
    }
    missing = [label for token, label in needed.items() if token not in src]
    if missing:
        fail("%s: consent UI missing %s" % (rel, ", ".join(missing)))
    else:
        ok("%s: consent banner, both controls and policy link present" % rel)


def check_accessibility_basics(rel: str, src: str) -> None:
    needed = {
        '<main id="main"': "main landmark",
        'class="skip-link"': "skip link",
        '<button class="mobile-toggle"': "hamburger as a button",
        'aria-expanded': "aria-expanded on the menu toggle",
    }
    missing = [label for token, label in needed.items() if token not in src]
    if missing:
        fail("%s: missing %s" % (rel, ", ".join(missing)))
    else:
        ok("%s: landmark, skip link and accessible menu toggle present" % rel)


def check_counts_match_cards(rel: str, src: str) -> None:
    """The static counters are what crawlers and no-JS visitors read."""
    for card_class, counter_id, label in (
            ("lot", "resultCount", "parking"),
            ("service-card", "serviceResultCount", "services")):
        actual = len(re.findall(r'class="%s"[ >]' % card_class, src))
        m = re.search(r'id="%s">(\d+)' % counter_id, src)
        if not m:
            fail("%s: no %s counter found" % (rel, label))
        elif int(m.group(1)) != actual:
            fail("%s: %s counter says %s but %d cards are present"
                 % (rel, label, m.group(1), actual))
        else:
            ok("%s: %s counter matches %d cards" % (rel, label, actual))


def check_hreflang(rel: str, src: str) -> None:
    expected = {"en", "hu", "de", "ro", "sr", "hr", "sk", "x-default"}
    found = set(re.findall(r'<link rel="alternate" hreflang="([^"]+)"', src))
    if not expected <= found:
        fail("%s: hreflang missing %s" % (rel, ", ".join(sorted(expected - found))))
    else:
        ok("%s: hreflang covers every language" % rel)


def check_sitemap() -> None:
    path = ROOT / "sitemap.xml"
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        fail("sitemap.xml is not valid XML: %s" % exc)
        return

    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    locs = [u.findtext(ns + "loc", "") for u in root.findall(ns + "url")]

    problems = []
    for loc in locs:
        if "#" in loc:
            problems.append("%s is a fragment, not a page" % loc)
            continue
        target = ROOT / urlparse(loc).path.lstrip("/")
        if loc.endswith("/"):
            target = target / "index.html"
        if not target.exists():
            problems.append("%s has no file behind it" % loc)

    if problems:
        fail("sitemap.xml: " + "; ".join(problems))
    else:
        ok("sitemap.xml: %d URLs, all backed by a file" % len(locs))


def check_manifest() -> None:
    path = ROOT / "site.webmanifest"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail("site.webmanifest: %s" % exc)
        return

    missing = [icon["src"] for icon in manifest.get("icons", [])
               if not (ROOT / icon["src"].lstrip("/")).exists()]
    if missing:
        fail("site.webmanifest points at missing icons: %s" % ", ".join(missing))
    else:
        ok("site.webmanifest: valid JSON, every icon exists")


def check_no_stripped_characters() -> None:
    """Accented characters were once dropped from these place names."""
    broken = {
        "lli út": "Üllői út",
        "Lrinci": "Lőrinci",
        "ll / Gyál": "Üllő / Gyál",
    }
    hits = []
    for rel in ALL_PAGES:
        src = (ROOT / rel).read_text(encoding="utf-8")
        for bad, good in broken.items():
            if bad in src and good not in src.replace(bad, ""):
                hits.append("%s: %r (should be %r)" % (rel, bad, good))
        # A bare variation selector is an emoji that lost its base character.
        for m in re.finditer("️", src):
            if ord(src[m.start() - 1]) < 0x2000:
                hits.append("%s: orphaned variation selector near %r"
                            % (rel, src[max(0, m.start() - 20):m.start()]))
                break

    if hits:
        fail("stripped characters: " + "; ".join(hits[:4]))
    else:
        ok("no stripped accents or orphaned emoji selectors")


def main() -> int:
    for rel in ALL_PAGES:
        path = ROOT / rel
        if not path.exists():
            fail("%s is missing" % rel)
            continue
        src = path.read_text(encoding="utf-8")

        check_markup(rel, src)
        check_local_references(rel, src)
        check_external_links(rel, src)
        check_json_ld(rel, src)
        check_analytics_gated(rel, src)

        if rel in LANG_PAGES:
            check_consent_wiring(rel, src)
            check_results_ui(rel, src)
            check_no_derived_totals(rel, src)
            check_lot_data(rel, src)
            check_content_preserved(rel, src)
            check_accessibility_basics(rel, src)
            check_counts_match_cards(rel, src)
            check_hreflang(rel, src)

    check_sitemap()
    check_manifest()
    check_no_stripped_characters()

    print()
    if failures:
        print("%d CHECK(S) FAILED" % len(failures))
        return 1
    print("ALL STATIC CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
