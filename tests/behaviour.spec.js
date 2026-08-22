'use strict';

/**
 * Drives the parking results — search, both sorts, the filter sheet — plus
 * the services section, the transport bar and the mobile menu, on every
 * language page.
 *
 * Each assertion stands for a defect this site has actually shipped: a menu
 * button pushed off-screen, a filter click leaving stale state, English labels
 * overwriting translated ones, and a "cheapest" marker computed from unsorted
 * order.
 */
const { chromium } = require('playwright');
const { LAUNCH, PAGES, run } = require('./lib/harness');

const money = t => parseInt(String(t).replace(/[^\d]/g, ''), 10);

run('BEHAVIOUR', async r => {
  const browser = await chromium.launch(LAUNCH);

  for (const [tag, path] of PAGES) {
    console.log(`\n=== ${tag} ===`);
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    await r.isolate(context);
    const page = await context.newPage();

    const errors = [];
    page.on('pageerror', e => errors.push(String(e)));
    page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });

    await page.goto(r.baseUrl + path, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(400);

    // Blocked external assets surface as network errors; not page bugs.
    const real = errors.filter(e => !/ERR_|net::|Failed to load resource/.test(e));
    r.check(tag, 'no JS errors', real.length === 0, real.join(' | '));

    const total = await page.locator('.lot').count();
    r.check(tag, 'every lot is listed', total === 33, `${total}`);
    r.check(tag, 'all lots visible before filtering',
      (await page.locator('.lot:not(.hidden)').count()) === total);

    // --- the price shown is the operator's published rate, not a derived total ---
    const rate = money(await page.locator('.lot:not(.hidden)').first().getAttribute('data-amount'));
    const shownPrice = money(await page.locator('.lot:not(.hidden) [data-total]').first().textContent());
    r.check(tag, 'price shown is the published rate, unmultiplied', shownPrice === rate,
      `${shownPrice} vs ${rate}`);
    r.check(tag, 'no trip-length control exists',
      (await page.locator('#tripNights').count()) === 0);

    // --- price sort ---
    const totals = await page.locator('.lot:not(.hidden)').evaluateAll(els =>
      els.map(e => ({ unit: e.dataset.unit, amount: parseInt(e.dataset.amount, 10) })));
    const dayRates = totals.filter(t => t.unit === 'day').map(t => t.amount);
    r.check(tag, 'price sort is ascending by daily rate',
      dayRates.every((v, i, a) => i === 0 || a[i - 1] <= v), dayRates.slice(0, 4).join(','));

    // A per-5-minute drop-off tariff has no daily rate, so it sorts last.
    const firstShortStay = totals.findIndex(t => t.unit !== 'day');
    r.check(tag, 'short-stay tariffs sort after every daily rate',
      firstShortStay === -1 || totals.slice(firstShortStay).every(t => t.unit !== 'day'));

    // --- the cheapest marker follows the sorted order ---
    const marked = await page.locator('.lot[data-cheapest] .lot-name').textContent();
    const firstName = await page.locator('.lot:not(.hidden) .lot-name').first().textContent();
    r.check(tag, 'cheapest marker is on the first result', marked === firstName,
      `${marked} vs ${firstName}`);

    // --- distance sort ---
    await page.locator('.sort-btn[data-sort="distance"]').click();
    await page.waitForTimeout(300);
    const kms = await page.locator('.lot:not(.hidden)').evaluateAll(els =>
      els.map(e => parseFloat(e.dataset.km)));
    r.check(tag, 'distance sort is ascending',
      kms.every((v, i, a) => i === 0 || a[i - 1] <= v), kms.slice(0, 4).join(','));
    r.check(tag, 'sort buttons track pressed state',
      (await page.getAttribute('.sort-btn[data-sort="distance"]', 'aria-pressed')) === 'true' &&
      (await page.getAttribute('.sort-btn[data-sort="price"]', 'aria-pressed')) === 'false');

    await page.locator('.sort-btn[data-sort="price"]').click();
    await page.waitForTimeout(300);

    // --- search ---
    await page.fill('#lotSearch', 'zzzznomatch');
    await page.waitForTimeout(250);
    r.check(tag, 'search with no match empties the list',
      (await page.locator('.lot:not(.hidden)').count()) === 0);
    r.check(tag, 'no-results message shows',
      await page.locator('#noResults').evaluate(e => e.classList.contains('visible')));

    await page.fill('#lotSearch', '');
    await page.waitForTimeout(250);
    r.check(tag, 'clearing search restores every lot',
      (await page.locator('.lot:not(.hidden)').count()) === total);

    // --- desktop: the filters are a permanent left column, not a modal ---
    r.check(tag, 'filter sidebar is visible without opening',
      await page.locator('#filterSheet').isVisible());
    r.check(tag, 'no modal opener on desktop',
      !(await page.locator('#filterOpen').isVisible()));
    r.check(tag, 'sidebar drops its dialog role',
      (await page.getAttribute('#filterSheet', 'role')) === null);
    const sideBox = await page.locator('#filterSheet').boundingBox();
    const listBox = await page.locator('#parkingGrid').boundingBox();
    r.check(tag, 'sidebar sits left of the results, not over them',
      sideBox.x + sideBox.width <= listBox.x + 1,
      `${Math.round(sideBox.x + sideBox.width)} vs ${Math.round(listBox.x)}`);
    r.check(tag, 'sidebar filters the list in place', await (async () => {
      await page.locator('.sheet-opt[data-value="official"] .label').click();
      await page.waitForTimeout(300);
      const n = await page.locator('.lot:not(.hidden)').count();
      await page.locator('#filterClear').click();
      await page.waitForTimeout(300);
      return n === 5 && (await page.locator('.lot:not(.hidden)').count()) === total;
    })());

    // --- phone: the same filters come back as a modal sheet ---
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(250);
    r.check(tag, 'filter sheet starts closed on a phone',
      !(await page.locator('#filterSheet').isVisible()));
    await page.locator('#filterOpen').click();
    await page.waitForTimeout(250);
    r.check(tag, 'filter sheet opens', await page.locator('#filterSheet').isVisible());
    r.check(tag, 'sheet reports expanded',
      (await page.getAttribute('#filterOpen', 'aria-expanded')) === 'true');

    // counts tell you what a tap will leave
    const counts = await page.locator('.sheet-opt').evaluateAll(els =>
      els.map(e => ({ v: e.dataset.value, n: parseInt(e.querySelector('[data-count]').textContent, 10) })));
    r.check(tag, 'every filter option shows a count',
      counts.length === 8 && counts.every(c => Number.isFinite(c.n)),
      JSON.stringify(counts));
    const official = counts.find(c => c.v === 'official');
    r.check(tag, 'official count matches the markup', official && official.n === 5,
      official && String(official.n));

    await page.locator('.sheet-opt[data-value="official"] .label').click();
    await page.waitForTimeout(300);
    r.check(tag, 'filtering narrows the list',
      (await page.locator('.lot:not(.hidden)').count()) === 5);
    r.check(tag, 'apply button names the result count',
      (await page.locator('#applyCount').textContent()).trim() === '5');
    r.check(tag, 'only the chosen type remains',
      (await page.locator('.lot:not(.hidden):not([data-type="official"])').count()) === 0);

    await page.locator('#filterApply').click();
    await page.waitForTimeout(250);
    r.check(tag, 'apply closes the sheet', !(await page.locator('#filterSheet').isVisible()));
    r.check(tag, 'active filter appears as a chip',
      (await page.locator('#activeChips button').count()) === 1);
    r.check(tag, 'filter button shows a badge',
      (await page.locator('#filterCount').textContent()) === '1');

    // dismissing the chip undoes the filter without reopening the sheet
    await page.locator('#activeChips button').first().click();
    await page.waitForTimeout(300);
    r.check(tag, 'dismissing the chip restores the list',
      (await page.locator('.lot:not(.hidden)').count()) === total);
    r.check(tag, 'chip row empties', (await page.locator('#activeChips button').count()) === 0);

    // search and filter compose
    await page.locator('#filterOpen').click();
    await page.waitForTimeout(200);
    await page.locator('.sheet-opt[data-value="offsite"] .label').click();
    await page.waitForTimeout(200);
    await page.locator('#filterApply').click();
    await page.fill('#lotSearch', 'vecs');
    await page.waitForTimeout(300);
    const composed = await page.locator('.lot:not(.hidden)').count();
    r.check(tag, 'search narrows within the active filter',
      composed > 0 && composed < 28, String(composed));
    r.check(tag, 'composed results are all off-site',
      (await page.locator('.lot:not(.hidden):not([data-type="offsite"])').count()) === 0);

    await page.fill('#lotSearch', '');
    await page.locator('#filterOpen').click();
    await page.waitForTimeout(200);
    await page.locator('#filterClear').click();
    await page.waitForTimeout(300);
    r.check(tag, 'clear all resets every filter',
      (await page.locator('.lot:not(.hidden)').count()) === total);
    await page.keyboard.press('Escape');
    await page.waitForTimeout(200);
    r.check(tag, 'Escape closes the sheet', !(await page.locator('#filterSheet').isVisible()));

    // back to desktop, where the sidebar has to come back on its own
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.waitForTimeout(250);
    r.check(tag, 'sidebar returns when the viewport widens again',
      await page.locator('#filterSheet').isVisible());

    // --- row expansion keeps the detail the old card carried ---
    const toggle = page.locator('.lot-toggle').first();
    const bodyId = await toggle.getAttribute('aria-controls');
    r.check(tag, 'lot body starts collapsed',
      await page.locator('#' + bodyId).evaluate(e => e.hidden));
    await toggle.click();
    await page.waitForTimeout(200);
    r.check(tag, 'expanding reveals the detail',
      !(await page.locator('#' + bodyId).evaluate(e => e.hidden)) &&
      (await page.getAttribute('.lot-toggle', 'aria-expanded')) === 'true');
    r.check(tag, 'detail still carries the booking link',
      (await page.locator('#' + bodyId + ' .card-link').count()) === 1);
    await toggle.click();
    await page.waitForTimeout(200);

    // --- services still work ---
    const services = await page.locator('.service-card').count();
    r.check(tag, 'services capped at 6',
      (await page.locator('.service-card:not(.hidden)').count()) === 6, String(services));
    await page.locator('#showAllServicesContainer button').click();
    await page.waitForTimeout(250);
    r.check(tag, 'show all reveals every service',
      (await page.locator('.service-card:not(.hidden)').count()) === services);
    await page.locator('.service-filter-btn[data-category="fuel"]').click();
    await page.waitForTimeout(300);
    const fuel = await page.locator('.service-card[data-category="fuel"]').count();
    r.check(tag, 'service filter re-caps after show all',
      (await page.locator('.service-card:not(.hidden)').count()) === Math.min(6, fuel));
    r.check(tag, 'service counter correct',
      Number(await page.locator('#serviceResultCount').textContent()) === fuel);

    // --- transport bar keeps this page's language ---
    const showLabel = await page.locator('#transportToggleText').textContent();
    await page.locator('.transport-toggle').click();
    await page.waitForTimeout(200);
    const hideLabel = await page.locator('#transportToggleText').textContent();
    r.check(tag, 'transport panel opens', await page.locator('#transportBarContent').isVisible());
    r.check(tag, 'transport label changes', hideLabel !== showLabel, `${showLabel} -> ${hideLabel}`);
    if (tag !== 'en') {
      r.check(tag, 'transport label stays translated',
        !/^(Show|Hide) Options$/.test(hideLabel), hideLabel);
    }

    // --- results copy is translated ---
    if (tag !== 'en') {
      const summary = await page.locator('#resultSummary').textContent();
      r.check(tag, 'result summary is translated', !/lots · cheapest first/.test(summary),
        summary.trim());
      const ph = await page.getAttribute('#lotSearch', 'placeholder');
      r.check(tag, 'search placeholder is translated', !/Search a lot or feature/.test(ph), ph);
    }

    // --- footer link that was once malformed ---
    const bkk = await page.getAttribute('a[href*="bkk.hu"]', 'href');
    r.check(tag, 'footer transport link is well formed', !/\s/.test(bkk), bkk);

    // --- mobile ---
    await page.setViewportSize({ width: 390, height: 844 });
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(250);

    const box = await page.locator('button.mobile-toggle').boundingBox();
    r.check(tag, 'hamburger sits inside the viewport',
      box !== null && box.x >= 0 && box.x + box.width <= 390,
      box ? `x=${Math.round(box.x)}` : 'no box');

    // The picker used to take a second header row, and the results toolbar
    // then started ~1,440px down the page.
    const tops = await page.locator('.lang-link').evaluateAll(els =>
      [...new Set(els.map(e => Math.round(e.getBoundingClientRect().top)))]);
    r.check(tag, 'language pills stay on one row', tops.length === 1, tops.join(','));

    // the strip scrolls on a narrow phone; the current language must not be
    // the chip that gets scrolled out of sight
    const activeChip = await page.locator('.lang-link.active').evaluate(e => {
      const strip = e.parentNode.getBoundingClientRect(), c = e.getBoundingClientRect();
      return c.left >= strip.left - 1 && c.right <= strip.right + 1;
    });
    r.check(tag, 'current language chip is in view', activeChip);

    const headerH = await page.locator('header').evaluate(e => e.getBoundingClientRect().height);
    r.check(tag, 'header is a single row on a phone', headerH <= 80, `${Math.round(headerH)}px`);

    // "30+", "16km" are single tokens; they must never break.
    const wrapped = await page.locator('.stat-value').evaluateAll(els =>
      els.filter(e => e.getBoundingClientRect().height >
        parseFloat(getComputedStyle(e).lineHeight || 0) * 1.5).map(e => e.textContent.trim()));
    r.check(tag, 'stat figures render on one line', wrapped.length === 0, wrapped.join(', '));

    // measure a first load, not the transport panel the assertions above left open
    if (await page.locator('#transportBarContent').isVisible()) {
      await page.locator('.transport-toggle').click();
      await page.waitForTimeout(250);
    }
    const toolbarTop = await page.evaluate(() =>
      Math.round(document.querySelector('.results-toolbar').getBoundingClientRect().top + window.scrollY));
    r.check(tag, 'filters are reachable without a long scroll', toolbarTop <= 1150,
      `${toolbarTop}px`);

    await page.locator('button.mobile-toggle').click();
    await page.waitForTimeout(200);
    r.check(tag, 'mobile menu opens',
      (await page.getAttribute('button.mobile-toggle', 'aria-expanded')) === 'true');
    await page.locator('#mobileMenu a[href="#parking"]').click();
    await page.waitForTimeout(400);
    r.check(tag, 'mobile menu closes after navigating',
      (await page.getAttribute('button.mobile-toggle', 'aria-expanded')) === 'false');

    // the lot name must have real room, not be crushed by the price column
    const nameWidth = await page.locator('.lot-main').first().evaluate(e => e.getBoundingClientRect().width);
    r.check(tag, 'lot name column has room on a phone', nameWidth >= 140,
      `${Math.round(nameWidth)}px`);

    // every control stays tappable
    const small = await page.evaluate(() => {
      const bad = [];
      document.querySelectorAll('.results-toolbar button, .results-toolbar select, .lot-toggle, .sheet-opt, .sheet-apply')
        .forEach(el => {
          const r = el.getBoundingClientRect();
          if (r.width > 0 && r.height > 0 && r.height < 40) bad.push(el.className + ':' + Math.round(r.height));
        });
      return bad;
    });
    r.check(tag, 'result controls meet the tap-target floor', small.length === 0, small.join(', '));

    for (const width of [320, 360, 390, 414, 768]) {
      await page.setViewportSize({ width, height: 800 });
      await page.waitForTimeout(150);
      const size = await page.evaluate(() => ({
        client: document.documentElement.clientWidth,
        scroll: document.documentElement.scrollWidth,
      }));
      r.check(tag, `no horizontal overflow at ${width}px`, size.scroll <= size.client + 1,
        `scrollWidth=${size.scroll} clientWidth=${size.client}`);
    }

    await context.close();
  }

  await browser.close();
});
