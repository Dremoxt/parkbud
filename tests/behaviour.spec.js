'use strict';

/**
 * Drives the filters, the show-all buttons, the transport bar and the mobile
 * menu on every language page.
 *
 * Each assertion here stands for a bug the site has actually had: the mobile
 * menu button pushed off-screen, a filter click leaving the grid uncapped
 * while the state flag said otherwise, and English labels overwriting the
 * translated ones at runtime.
 */
const { chromium } = require('playwright');
const { LAUNCH, PAGES, run } = require('./lib/harness');

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

    // Blocked external assets surface as network errors; they are not page bugs.
    const real = errors.filter(e => !/ERR_|net::|Failed to load resource/.test(e));
    r.check(tag, 'no JS errors', real.length === 0, real.join(' | '));

    // --- initial state: capped list, counter shows the full match total ---
    const totalParking = await page.locator('.parking-card').count();
    r.check(tag, 'parking list capped at 6',
      (await page.locator('.parking-card:not(.hidden)').count()) === 6);
    r.check(tag, 'counter shows every match, not just the visible ones',
      Number(await page.locator('#resultCount').textContent()) === totalParking);
    r.check(tag, 'show-all button offered', await page.locator('#showAllContainer').isVisible());

    const label = await page.locator('#showAllContainer button').textContent();
    r.check(tag, 'show-all label counts the remainder',
      label.includes(String(totalParking)) && label.includes(String(totalParking - 6)), label);

    // --- expand, then filter: the state race this suite exists for ---
    await page.locator('#showAllContainer button').click();
    await page.waitForTimeout(150);
    r.check(tag, 'show-all reveals every card',
      (await page.locator('.parking-card:not(.hidden)').count()) === totalParking);
    r.check(tag, 'show-all button hides once expanded',
      !(await page.locator('#showAllContainer').isVisible()));

    await page.locator('.filter-btn[data-filter="type"][data-value="offsite"]').click();
    await page.waitForTimeout(400);

    const offsiteTotal = await page.locator('.parking-card[data-type="offsite"]').count();
    r.check(tag, 'filtering after expanding re-caps the list',
      (await page.locator('.parking-card:not(.hidden)').count()) === Math.min(6, offsiteTotal));
    r.check(tag, 'show-all button comes back when it should',
      (await page.locator('#showAllContainer').isVisible()) === (offsiteTotal > 6));
    r.check(tag, 'counter reflects the filtered total',
      Number(await page.locator('#resultCount').textContent()) === offsiteTotal);
    r.check(tag, 'no cards of the excluded type remain',
      (await page.locator('.parking-card:not(.hidden):not([data-type="offsite"])').count()) === 0);
    r.check(tag, 'aria-pressed follows the selection',
      (await page.getAttribute('.filter-btn[data-filter="type"][data-value="offsite"]', 'aria-pressed')) === 'true' &&
      (await page.getAttribute('.filter-btn[data-filter="type"][data-value="all"]', 'aria-pressed')) === 'false');

    // --- feature filters combine with the type filter ---
    await page.locator('.filter-btn[data-filter="feature"][data-value="24h"]').click();
    await page.waitForTimeout(300);
    r.check(tag, 'feature filter intersects with type filter',
      (await page.locator('.parking-card:not(.hidden)').evaluateAll(
        els => els.filter(e => !(e.dataset.features || '').split(',').includes('24h')).length)) === 0);

    // --- reset ---
    await page.locator('.filter-reset').first().click();
    await page.waitForTimeout(300);
    r.check(tag, 'reset restores the cap',
      (await page.locator('.parking-card:not(.hidden)').count()) === 6);
    r.check(tag, 'reset restores the full count',
      Number(await page.locator('#resultCount').textContent()) === totalParking);
    r.check(tag, 'reset re-offers the show-all button',
      await page.locator('#showAllContainer').isVisible());

    // --- services mirror the parking behaviour ---
    r.check(tag, 'services list capped at 6',
      (await page.locator('.service-card:not(.hidden)').count()) === 6);
    await page.locator('#showAllServicesContainer button').click();
    await page.waitForTimeout(150);
    await page.locator('.service-filter-btn[data-category="fuel"]').click();
    await page.waitForTimeout(300);
    const fuelTotal = await page.locator('.service-card[data-category="fuel"]').count();
    r.check(tag, 'service filter after expanding re-caps',
      (await page.locator('.service-card:not(.hidden)').count()) === Math.min(6, fuelTotal));
    r.check(tag, 'service counter correct',
      Number(await page.locator('#serviceResultCount').textContent()) === fuelTotal);

    // --- transport bar keeps this page's language ---
    const showLabel = await page.locator('#transportToggleText').textContent();
    await page.locator('.transport-toggle').click();
    await page.waitForTimeout(150);
    const hideLabel = await page.locator('#transportToggleText').textContent();
    r.check(tag, 'transport panel opens', await page.locator('#transportBarContent').isVisible());
    r.check(tag, 'transport toggle reports expanded',
      (await page.getAttribute('.transport-toggle', 'aria-expanded')) === 'true');
    r.check(tag, 'transport label changes on toggle', hideLabel !== showLabel,
      `${showLabel} -> ${hideLabel}`);
    if (tag !== 'en') {
      r.check(tag, 'transport label stays translated',
        !/^(Show|Hide) Options$/.test(hideLabel), hideLabel);
    }
    await page.locator('.transport-toggle').click();
    await page.waitForTimeout(150);
    r.check(tag, 'transport label restores',
      (await page.locator('#transportToggleText').textContent()) === showLabel);

    // --- the footer link that was malformed ---
    const bkk = await page.getAttribute('a[href*="bkk.hu"]', 'href');
    r.check(tag, 'footer transport link is a well-formed URL', !/\s/.test(bkk), bkk);

    // --- mobile: the hamburger must be reachable and must close on navigate ---
    await page.setViewportSize({ width: 390, height: 800 });
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(250);

    const box = await page.locator('button.mobile-toggle').boundingBox();
    r.check(tag, 'hamburger sits inside the viewport',
      box !== null && box.x >= 0 && box.x + box.width <= 390,
      box ? `x=${Math.round(box.x)} right=${Math.round(box.x + box.width)}` : 'no box');

    await page.locator('button.mobile-toggle').click();
    await page.waitForTimeout(200);
    r.check(tag, 'mobile menu opens',
      (await page.getAttribute('button.mobile-toggle', 'aria-expanded')) === 'true');

    await page.locator('#mobileMenu a[href="#parking"]').click();
    await page.waitForTimeout(400);
    r.check(tag, 'mobile menu closes after navigating',
      (await page.getAttribute('button.mobile-toggle', 'aria-expanded')) === 'false' &&
      !(await page.locator('#mobileMenu').evaluate(e => e.classList.contains('active'))));
    r.check(tag, 'in-page navigation updates the URL hash', page.url().endsWith('#parking'),
      page.url());

    // --- no sideways scrolling at any phone width ---
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
