#!/usr/bin/env python3
"""Measure how the results are actually used: which filters get picked, and
which lots send a reader on to the operator's own booking site.

Two constraints shape this:

  * Nothing may reach GA4 before an explicit yes. Pushing an event onto
    dataLayer early is not harmless -- gtag.js replays whatever is already
    queued the moment it loads -- so every event goes through one helper that
    checks the stored choice first.

  * A report split seven ways by language is useless. Facet values are already
    language-independent tokens; lot names are not, so each lot gets a stable
    data-lot-id derived from its English name and applied by position, the same
    way data/prices.csv is matched.

Edits the seven built pages in place. Refuses to run twice.
"""
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = ["index.html", "hu/index.html", "de/index.html", "ro/index.html",
         "sr/index.html", "hr/index.html", "sk/index.html"]

LOT_OPEN = '<article class="lot"'


def slug(name):
    flat = unicodedata.normalize("NFKD", name)
    flat = "".join(c for c in flat if not unicodedata.combining(c))
    flat = re.sub(r"[^A-Za-z0-9]+", "-", flat).strip("-").lower()
    return flat


def lot_ids():
    """Stable ids, taken once from the English page and reused everywhere.

    The name is what makes a report readable, so it is the id. Two different
    operators are named "Reptéri Parkolás" and "Repteri Parkolas" and collide
    once the accents are folded away; they are told apart by the only thing
    that actually differs, the domain they book through. Five official lots all
    share parkolo.bud.hu, which is why the host cannot be the id on its own.
    """
    src = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    names = re.findall(r'<h3 class="lot-name">([^<]+)</h3>', src)
    hosts = re.findall(r'<a href="https?://([^/"]+)[^"]*"[^>]*class="card-link"', src)
    if len(hosts) != len(names):
        raise SystemExit("%d lot names but %d booking links" % (len(names), len(hosts)))

    ids = [slug(n) for n in names]
    seen = {}
    for i in ids:
        seen[i] = seen.get(i, 0) + 1
    ids = [i if seen[i] == 1 else i + "-" + slug(h.rsplit(".", 1)[-1])
           for i, h in zip(ids, hosts)]

    if len(ids) != len(set(ids)):
        dupes = sorted(i for i in set(ids) if ids.count(i) > 1)
        raise SystemExit("lot ids are not unique: %s" % ", ".join(dupes))
    return ids


TRACKER = """
        /* Events reach GA4 only after an explicit yes. Queuing them earlier is
           not harmless: gtag.js replays whatever is already sitting in
           dataLayer the moment it loads. */
        w.ParkBUDTrack = function (name, params) {
            if (read() !== 'granted') return false;
            var payload = {}, key;
            for (key in (params || {})) payload[key] = params[key];
            payload.page_language = d.documentElement.lang || 'en';
            gtag('event', name, payload);
            return true;
        };

"""

TRACKER_AT = "        function start() {\n"

STATE_OLD = "        var state = { sort: 'price', q: '', type: [], access: [], feature: [] };\n"

STATE_NEW = """        var state = { sort: 'price', q: '', type: [], access: [], feature: [] };
        var shownCount = 0;

        /* ---- analytics ---- */
        function track(name, params) {
            if (typeof w.ParkBUDTrack === 'function') w.ParkBUDTrack(name, params);
        }

        /* Facet values are the same tokens on every language page, so a report
           grouped by them does not fragment into seven. */
        function activeFilters() {
            return state.type.concat(state.access, state.feature).join('|');
        }

        function lotParams(lot) {
            return {
                lot_id: lot.dataset.lotId || '',
                lot_type: lot.dataset.type || '',
                lot_access: lot.dataset.access || '',
                list_position: visibleLots().indexOf(lot) + 1,
                sort_by: state.sort,
                active_filters: activeFilters()
            };
        }
"""

APPLY_OLD = """            renderCounts();
            renderChips();
        }
"""

APPLY_NEW = """            shownCount = shown.length;
            renderCounts();
            renderChips();
        }
"""

FACET_OLD = """            var input = d.querySelector('.sheet-opt input[data-kind="' + kind + '"][data-value="' + value + '"]');
            if (input) input.checked = on;
            apply();
        }
"""

FACET_NEW = """            var input = d.querySelector('.sheet-opt input[data-kind="' + kind + '"][data-value="' + value + '"]');
            if (input) input.checked = on;
            apply();
            /* Covers both entry points: the checkbox and the chip's dismiss. */
            track(on ? 'filter_select' : 'filter_deselect', {
                filter_kind: kind,
                filter_value: value,
                results_shown: shownCount,
                active_filters: activeFilters()
            });
        }
"""

SORT_OLD = """                this.setAttribute('aria-pressed', 'true');
                state.sort = this.dataset.sort;
                apply();
"""

SORT_NEW = """                this.setAttribute('aria-pressed', 'true');
                var was = state.sort;
                state.sort = this.dataset.sort;
                apply();
                if (was !== state.sort) {
                    track('sort_change', { sort_by: state.sort, results_shown: shownCount });
                }
"""

SEARCH_OLD = """        if (searchInput) {
            searchInput.addEventListener('input', function () {
                state.q = this.value.trim().toLowerCase();
                apply();
            });
        }
"""

SEARCH_NEW = """        if (searchInput) {
            var searchTimer = null;
            searchInput.addEventListener('input', function () {
                state.q = this.value.trim().toLowerCase();
                apply();
                /* One event per query, not one per keystroke. */
                if (searchTimer) clearTimeout(searchTimer);
                var typed = state.q;
                searchTimer = setTimeout(function () {
                    if (typed) track('search', { search_term: typed, results_shown: shownCount });
                }, 900);
            });
        }
"""

TOGGLE_OLD = """                this.setAttribute('aria-expanded', open ? 'false' : 'true');
                if (body) body.hidden = open;
            });
        });
"""

TOGGLE_NEW = """                this.setAttribute('aria-expanded', open ? 'false' : 'true');
                if (body) body.hidden = open;
                var row = this.closest && this.closest('.lot');
                if (!open && row) track('lot_expand', lotParams(row));
            });
        });

        /* Delegated, because sorting moves the rows around, and because this
           click is the one outcome the page exists to produce. */
        if (list) {
            list.addEventListener('click', function (e) {
                var link = e.target.closest && e.target.closest('a.card-link');
                var row = link && link.closest('.lot');
                if (!row) return;
                var params = lotParams(row);
                params.link_url = link.href;
                params.link_domain = link.hostname.replace(/^www\\./, '');
                track('booking_click', params);
            });
        }
"""

CLEAR_OLD = """                d.querySelectorAll('.sheet-opt input').forEach(function (i) { i.checked = false; });
                apply();
"""

CLEAR_NEW = """                d.querySelectorAll('.sheet-opt input').forEach(function (i) { i.checked = false; });
                apply();
                track('filter_clear', { results_shown: shownCount });
"""

EDITS = [
    ("page runtime state", STATE_OLD, STATE_NEW),
    ("result counter", APPLY_OLD, APPLY_NEW),
    ("facet toggle", FACET_OLD, FACET_NEW),
    ("sort buttons", SORT_OLD, SORT_NEW),
    ("search field", SEARCH_OLD, SEARCH_NEW),
    ("row expander", TOGGLE_OLD, TOGGLE_NEW),
    ("reset all", CLEAR_OLD, CLEAR_NEW),
]


def main():
    ids = lot_ids()

    for rel in PAGES:
        path = os.path.join(ROOT, rel)
        with open(path, encoding="utf-8") as fh:
            src = fh.read()

        if "ParkBUDTrack" in src:
            raise SystemExit("%s: analytics events already added" % rel)

        # --- stable lot ids, by position ---
        parts = src.split(LOT_OPEN)
        if len(parts) - 1 != len(ids):
            raise SystemExit("%s: %d lots, expected %d"
                             % (rel, len(parts) - 1, len(ids)))
        src = parts[0]
        for lot_id, chunk in zip(ids, parts[1:]):
            src += '%s data-lot-id="%s"%s' % (LOT_OPEN, lot_id, chunk)

        # --- the consent-gated helper ---
        if TRACKER_AT not in src:
            raise SystemExit("%s: consent gate not found where expected" % rel)
        src = src.replace(TRACKER_AT, TRACKER + TRACKER_AT, 1)

        # --- the call sites ---
        for label, old, new in EDITS:
            if src.count(old) != 1:
                raise SystemExit("%s: %s not found exactly once (%d)"
                                 % (rel, label, src.count(old)))
            src = src.replace(old, new, 1)

        with open(path, "w", encoding="utf-8") as fh:
            fh.write(src)
        print("updated %s" % rel)

    print("%d page(s) instrumented, %d lots" % (len(PAGES), len(ids)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
