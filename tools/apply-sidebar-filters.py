#!/usr/bin/env python3
"""Shorten the mobile run-up to the results and give desktop a permanent
filter sidebar.

On a phone the filter controls sat roughly 1,440px down the page: a two-row
header, a 2x2 stats block and a section header padded for a desktop screen all
came first. On a wide screen the same filters were locked behind a modal even
though there was empty gutter beside the list.

This edits the seven built pages in place -- build-redesign.py only knows how
to run against the pre-redesign source, so incremental layout work happens
here, the way the earlier maintenance passes did it.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = ["index.html", "hu/index.html", "de/index.html", "ro/index.html",
         "sr/index.html", "hr/index.html", "sk/index.html"]

MARKER = "/* ---- results layout: filters as a desktop sidebar ---- */"


def outer_html(src, open_tag):
    """Span of a <div> block including its own closing tag.

    Counting opens and closes is the only way to get this right: a lazy regex
    stops at the first </div>, which truncates any block with nested divs.
    """
    at = src.find(open_tag)
    if at == -1:
        raise SystemExit("anchor not found: %s" % open_tag[:60])
    depth = 1
    for m in re.finditer(r"<div\b|</div>", src[at + len(open_tag):]):
        depth += 1 if m.group(0) != "</div>" else -1
        if depth == 0:
            return at, at + len(open_tag) + m.end()
    raise SystemExit("unbalanced block at: %s" % open_tag[:60])


CSS = '''
        /* ---- results layout: filters as a desktop sidebar ---- */

        /* Phones keep the modal sheet; from 1024px up the same markup becomes
           the left column, so the filters are never more than a glance away. */
        @media (min-width: 1024px) {
            .results-layout {
                display: grid;
                grid-template-columns: 272px minmax(0, 1fr);
                gap: 1.75rem;
                /* Sticky only works if the column is not stretched to the
                   full row height, which is the grid default. */
                align-items: start;
                max-width: 1240px;
                margin: 0 auto;
            }

            .results-side {
                position: sticky;
                top: calc(var(--header-h) + 1rem);
                max-height: calc(100vh - var(--header-h) - 2rem);
                overflow-y: auto;
            }

            /* The sheet stops being a dialog here: no backdrop, no apply
               button to dismiss it, nothing to open. Overriding [hidden] keeps
               it painted before the script has run. */
            .results-side .sheet,
            .results-side .sheet[hidden] {
                display: flex;
                position: static;
                width: auto;
                max-height: none;
                transform: none;
                border: 1px solid var(--mist);
                border-radius: var(--radius-md);
                box-shadow: none;
            }

            .results-side .sheet-body { overflow: visible; }
            .results-side .sheet-foot { display: none; }
            .results-side .sheet-head { padding-left: 1rem; }
            .results-side .sheet-body { padding: 0 1rem 0.75rem; }
            .results-side .sheet-opt { min-height: 42px; }

            .filter-open { display: none; }

            /* With the filters gone from the toolbar there is room to put
               search and sort on one line instead of stacking them. */
            .results-toolbar {
                flex-flow: row wrap;
                align-items: center;
                gap: 0.75rem;
                padding-left: 0;
                padding-right: 0;
            }

            .search-row { flex: 1 1 260px; }
            .sort-seg { flex: 0 0 260px; }
            .active-chips { flex: 1 1 100%; }
            .results-summary { flex: 1 1 100%; }

            .results-list { margin-top: 1rem; max-width: none; }
            .no-results { padding-left: 0; padding-right: 0; }
        }

        /* ---- phone: get the filters above the fold ---- */
        @media (max-width: 768px) {
            /* The picker used to claim a whole second header row, which is
               what made the sticky header 105px instead of ~72px. It now
               shares the row and scrolls sideways if seven codes will not
               fit; syncHeaderHeight() still measures the real value. */
            :root { --header-h: 72px; }

            header { padding: 0.6rem 1rem; }

            nav {
                flex-wrap: nowrap;
                gap: 0.5rem;
            }

            .logo { gap: 0.5rem; min-width: 0; }
            .logo-icon { width: 34px; height: 34px; border-radius: 9px; }
            .logo-icon svg { width: 18px; height: 18px; }
            .logo-text { font-size: 1.05rem; }

            /* order:3 used to push the picker past the menu button and onto
               a row of its own; back to source order it sits between the
               wordmark and the button. flex-start keeps the current language,
               always the first chip, from scrolling out of sight. */
            .lang-picker {
                order: 0;
                flex: 0 1 auto;
                min-width: 0;
                flex-wrap: nowrap;
                overflow-x: auto;
                justify-content: flex-start;
                gap: 0.15rem;
                margin-left: 0;
                margin-top: 0;
                scrollbar-width: none;
                -ms-overflow-style: none;
            }

            .lang-picker::-webkit-scrollbar { display: none; }

            /* Small, but not below the 24px minimum target size: seven codes
               will not all fit on a 360px screen at a tappable size, so the
               strip scrolls rather than shrinking past usable. */
            .lang-link {
                flex: 0 0 auto;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                min-width: 28px;
                min-height: 28px;
                font-size: 0.66rem;
                padding: 0 0.28rem;
                border-radius: 5px;
            }

            .mobile-toggle { padding: 8px 0 8px 6px; }

            /* One row of four, not a 2x2 block: the same four facts in about
               a third of the height. */
            .stats-strip { padding: 0.7rem 1rem; }

            .stats-grid {
                grid-template-columns: repeat(4, 1fr);
                gap: 0.4rem;
            }

            .stat-value {
                font-size: 1.35rem;
                white-space: nowrap;
            }

            .stat-label {
                font-size: 0.62rem;
                line-height: 1.2;
                margin-top: 0.1rem;
            }

            /* Section padding was tuned for a desktop column. */
            .section { padding: 2.5rem 1rem; }
            .section-header { margin-bottom: 1.25rem; }
            .section-title { font-size: 1.5rem; }
            .section-subtitle { font-size: 0.95rem; }
            .section-tag { margin-bottom: 0.6rem; padding: 0.3rem 0.75rem; font-size: 0.7rem; }

            /* The summary line and the checked-on date each have to hold a
               single row; at 0.8rem they wrapped to two. */
            .results-summary { gap: 0.5rem; font-size: 0.72rem; }
            .results-summary .checked { font-size: 0.66rem; text-align: right; }
            .filter-open { padding: 0 0.7rem; font-size: 0.85rem; gap: 0.35rem; }

            .hero { padding-top: calc(var(--header-h) + 0.25rem); }
            .hero-content { padding: 0.25rem 1rem 0.75rem; }
            .hero p { font-size: 0.95rem; margin-bottom: 0.85rem; }
            .hero-buttons { gap: 0.5rem; }
            .hero-buttons .btn { padding: 0.6rem 1rem; font-size: 0.85rem; }
        }

        /* The stat figure is a single token; it must never break across
           lines, whatever the column width. */
        .stat-value { white-space: nowrap; }
'''


def restructure(src, rel):
    """Wrap toolbar + list in a results-main column and move the sheet beside it."""
    if 'class="results-layout"' in src:
        raise SystemExit("%s: already restructured" % rel)

    sheet_open = '    <div class="sheet" id="filterSheet"'
    at = src.find(sheet_open)
    if at == -1:
        raise SystemExit("%s: filter sheet not found" % rel)
    start, end = outer_html(src, src[at:src.index(">", at) + 1])
    sheet = src[start:end]
    src = src[:start] + src[end:]
    # ...and the blank line it left behind.
    src = src.replace("hidden></div>\n\n    </main>", "hidden></div>\n    </main>", 1)

    # Re-indent the sheet one level in for its new home.
    sheet = "\n".join(("    " + line) if line.strip() else line
                      for line in sheet.split("\n"))

    toolbar = '        <div class="results-toolbar container">'
    if toolbar not in src:
        raise SystemExit("%s: results toolbar not found" % rel)
    opening = (
        '        <div class="results-layout">\n'
        '        <aside class="results-side">\n'
        + sheet + "\n"
        '        </aside>\n'
        '        <div class="results-main">\n'
    )
    src = src.replace(toolbar, opening + toolbar, 1)

    no_results = '        <div class="no-results container" id="noResults">'
    start, end = outer_html(src, no_results)
    src = src[:end] + "\n        </div>\n        </div>" + src[end:]
    return src


JS_OLD = """        /* ---- sheet ---- */
        var sheet = byId('filterSheet'), backdrop = byId('filterBackdrop'), opener = byId('filterOpen');
        function setSheet(open) {
            if (!sheet) return;
            sheet.hidden = !open;
"""

JS_NEW = """        /* ---- filters: a modal sheet on phones, a static sidebar on desktop ---- */
        var sheet = byId('filterSheet'), backdrop = byId('filterBackdrop'), opener = byId('filterOpen');
        var sidebarMQ = w.matchMedia ? w.matchMedia('(min-width: 1024px)') : null;
        function asSidebar() { return !!(sidebarMQ && sidebarMQ.matches); }

        /* In the sidebar there is nothing to open or dismiss, so the dialog
           role has to come off: otherwise a screen reader announces a modal
           that is permanently open and traps nothing. */
        function syncSheetMode() {
            if (!sheet) return;
            var side = asSidebar();
            sheet.hidden = !side;
            if (side) {
                sheet.removeAttribute('role');
                sheet.removeAttribute('aria-modal');
            } else {
                sheet.setAttribute('role', 'dialog');
                sheet.setAttribute('aria-modal', 'true');
            }
            if (backdrop) backdrop.hidden = true;
            if (opener) opener.setAttribute('aria-expanded', 'false');
        }

        if (sidebarMQ) {
            if (sidebarMQ.addEventListener) sidebarMQ.addEventListener('change', syncSheetMode);
            else if (sidebarMQ.addListener) sidebarMQ.addListener(syncSheetMode);
        }
        syncSheetMode();

        function setSheet(open) {
            if (!sheet || asSidebar()) return;
            /* The consent banner is fixed to the same corner and outranks
               everything by design, so on a phone it covered the apply
               button for anyone who opened the filters before answering it. */
            if (open) {
                var notice = byId('cookieConsent');
                var clear = (notice && !notice.hidden) ? notice.getBoundingClientRect().height + 24 : 0;
                sheet.style.paddingBottom = clear ? clear + 'px' : '';
            }
            sheet.hidden = !open;
"""

ESC_OLD = "            if (sheet && !sheet.hidden) setSheet(false);"
ESC_NEW = "            if (sheet && !sheet.hidden && !asSidebar()) setSheet(false);"

LANG_OLD = """        if (w.ResizeObserver && header) new ResizeObserver(syncHeaderHeight).observe(header);
"""

LANG_NEW = """        if (w.ResizeObserver && header) new ResizeObserver(syncHeaderHeight).observe(header);

        /* The picker scrolls sideways on a narrow phone, and the current
           language is not always the first chip -- on /sk/ it is the last.
           Centre it, or a Slovak reader lands on a strip that looks English. */
        function showActiveLang() {
            var chip = d.querySelector('.lang-link.active');
            if (!chip) return;
            var strip = chip.parentNode;
            if (strip.scrollWidth <= strip.clientWidth) return;
            /* Rects, not offsetLeft: the strip is not positioned, so
               offsetLeft is measured from the fixed header instead. */
            var box = strip.getBoundingClientRect(), at = chip.getBoundingClientRect();
            strip.scrollLeft += (at.left - box.left) - (box.width - at.width) / 2;
        }
        showActiveLang();
        w.addEventListener('resize', showActiveLang);
"""


def main():
    changed = 0
    for rel in PAGES:
        path = os.path.join(ROOT, rel)
        with open(path, encoding="utf-8") as fh:
            src = fh.read()

        if MARKER in src:
            raise SystemExit("%s: layout pass already applied" % rel)

        src = restructure(src, rel)

        if "    </style>" not in src:
            raise SystemExit("%s: no stylesheet close" % rel)
        src = src.replace("    </style>", CSS + "    </style>", 1)

        if JS_OLD not in src:
            raise SystemExit("%s: sheet runtime not found where expected" % rel)
        src = src.replace(JS_OLD, JS_NEW, 1)

        if ESC_OLD not in src:
            raise SystemExit("%s: escape handler not found" % rel)
        src = src.replace(ESC_OLD, ESC_NEW, 1)

        if LANG_OLD not in src:
            raise SystemExit("%s: header sync not found" % rel)
        src = src.replace(LANG_OLD, LANG_NEW, 1)

        with open(path, "w", encoding="utf-8") as fh:
            fh.write(src)
        changed += 1
        print("updated %s" % rel)

    print("%d page(s) updated" % changed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
