'use strict';

/**
 * Proves the analytics consent gate holds.
 *
 * The load-after-accept assertions read the DOM rather than the network, so a
 * runner that cannot reach Google still gives a truthful result. The
 * nothing-before-consent assertions stay request-based, which is the stronger
 * claim and the one that matters.
 */
const { chromium } = require('playwright');
const { LAUNCH, PAGES, TRACKER, run } = require('./lib/harness');

const STORAGE_KEY = 'parkbud:consent';

function trackerWatcher(page, sink) {
  page.on('request', req => { if (TRACKER.test(req.url())) sink.push(req.url()); });
}

const injectedTrackers = () => document.querySelectorAll(
  'script[src*="googletagmanager.com"], script[src*="contentsquare.net"]').length;

const consentCalls = () => (window.dataLayer || []).map(a => Array.from(a));

const usageEvents = () => (window.dataLayer || [])
  .map(a => Array.from(a)).filter(a => a[0] === 'event').map(a => a[1]);

/* Driven through the elements rather than the mouse: what is under test here
 * is the gate, not hit-testing, and the banner itself covers part of the page.
 */
const useTheResults = () => {
  document.querySelector('.sheet-opt input[data-value="official"]').click();
  document.querySelector('.sort-btn[data-sort="distance"]').click();
  document.querySelector('.lot-toggle').click();
  document.querySelector('.lot:not(.hidden) .card-link').dispatchEvent(
    new MouseEvent('click', { bubbles: true, cancelable: true }));
};

run('CONSENT GATE', async r => {
  const browser = await chromium.launch(LAUNCH);

  for (const [tag, path] of PAGES) {
    console.log(`\n=== ${tag} ===`);

    // ---------- 1. Fresh visit, no decision made ----------
    let context = await browser.newContext();
    await r.isolate(context);
    let page = await context.newPage();
    const hits = [];
    trackerWatcher(page, hits);

    await page.goto(r.baseUrl + path, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(900);

    r.check(tag, 'no tracker request before consent', hits.length === 0, hits.join(', '));
    r.check(tag, 'no tracker script injected before consent',
      (await page.evaluate(injectedTrackers)) === 0);
    r.check(tag, 'no cookies set before consent',
      (await context.cookies()).length === 0,
      (await context.cookies()).map(c => c.name).join(','));
    r.check(tag, 'banner is shown', await page.locator('#cookieConsent').isVisible());

    const defaults = (await page.evaluate(consentCalls)).find(
      a => a[0] === 'consent' && a[1] === 'default');
    r.check(tag, 'consent mode defaults every storage type to denied',
      defaults && Object.entries(defaults[2] || {})
        .filter(([k]) => k !== 'security_storage')
        .every(([, v]) => v === 'denied'),
      JSON.stringify(defaults && defaults[2]));

    if (tag !== 'en') {
      const body = await page.locator('#cookieConsent p').first().textContent();
      r.check(tag, 'banner copy is translated',
        !/We would like to load analytics/.test(body), body.slice(0, 45));
    }

    // Decline must be as reachable as accept, not hidden behind a settings page.
    const buttons = page.locator('#cookieConsent .cookie-actions button');
    r.check(tag, 'accept and decline are both offered up front',
      (await buttons.count()) === 2);

    // Using the page must not queue anything for GA4 either: gtag.js replays
    // whatever is already sitting in dataLayer the moment it loads, so an
    // event pushed "harmlessly" before a decision is sent after one.
    await page.evaluate(useTheResults);
    await page.waitForTimeout(300);
    let queued = await page.evaluate(usageEvents);
    r.check(tag, 'no usage event queued before a decision', queued.length === 0,
      queued.join(','));

    // ---------- 2. Decline ----------
    await buttons.nth(1).click();
    await page.waitForTimeout(600);

    r.check(tag, 'banner dismissed on decline',
      !(await page.locator('#cookieConsent').isVisible()));
    r.check(tag, 'still no tracker request after declining', hits.length === 0, hits.join(', '));
    r.check(tag, 'decline is stored',
      (await page.evaluate(k => localStorage.getItem(k), STORAGE_KEY)) === 'denied');

    await page.evaluate(useTheResults);
    await page.waitForTimeout(300);
    queued = await page.evaluate(usageEvents);
    r.check(tag, 'no usage event after declining', queued.length === 0, queued.join(','));

    const revisitHits = [];
    const revisit = await context.newPage();
    trackerWatcher(revisit, revisitHits);
    await revisit.goto(r.baseUrl + path, { waitUntil: 'domcontentloaded' });
    await revisit.waitForTimeout(900);
    r.check(tag, 'decline survives to the next page view',
      revisitHits.length === 0, revisitHits.join(', '));
    r.check(tag, 'banner does not nag after a decline',
      !(await revisit.locator('#cookieConsent').isVisible()));
    await context.close();

    // ---------- 3. Accept ----------
    context = await browser.newContext();
    await r.isolate(context);
    page = await context.newPage();
    const acceptHits = [];
    trackerWatcher(page, acceptHits);

    await page.goto(r.baseUrl + path, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);
    await page.locator('#cookieConsent .cookie-actions button').first().click();
    await page.waitForTimeout(900);

    r.check(tag, 'both tracker scripts injected after accepting',
      (await page.evaluate(injectedTrackers)) === 2);
    r.check(tag, 'tracker requests attempted after accepting', acceptHits.length > 0);

    // the other half of the contract: after a yes, usage does get measured
    await page.evaluate(useTheResults);
    await page.waitForTimeout(300);
    const measured = await page.evaluate(usageEvents);
    r.check(tag, 'usage is measured once accepted',
      ['filter_select', 'sort_change', 'lot_expand', 'booking_click']
        .every(name => measured.indexOf(name) !== -1),
      measured.join(','));

    r.check(tag, 'accept is stored',
      (await page.evaluate(k => localStorage.getItem(k), STORAGE_KEY)) === 'granted');
    r.check(tag, 'consent mode updated to granted',
      (await page.evaluate(consentCalls)).some(
        a => a[0] === 'consent' && a[1] === 'update' && a[2] &&
             a[2].analytics_storage === 'granted'));

    // ---------- 4. Changing your mind from the footer ----------
    await page.evaluate(() => window.ParkBUDConsent.reopen());
    await page.waitForTimeout(200);
    r.check(tag, 'footer control reopens the banner',
      await page.locator('#cookieConsent').isVisible());
    r.check(tag, 'footer links to the privacy policy',
      (await page.locator('.footer-legal a[href="/privacy/"]').count()) === 1);

    await page.locator('#cookieConsent .cookie-actions button').nth(1).click();
    await page.waitForTimeout(300);
    r.check(tag, 'withdrawal is stored',
      (await page.evaluate(k => localStorage.getItem(k), STORAGE_KEY)) === 'denied');

    await context.close();
  }

  // ---------- The policy page itself ----------
  console.log('\n=== /privacy/ ===');
  const context = await browser.newContext();
  await r.isolate(context);
  const page = await context.newPage();
  const hits = [];
  const errors = [];
  trackerWatcher(page, hits);
  page.on('pageerror', e => errors.push(String(e)));

  await page.goto(r.baseUrl + '/privacy/', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(700);

  r.check('privacy', 'page loads without JS errors', errors.length === 0, errors.join(' | '));
  r.check('privacy', 'the policy page loads no trackers itself', hits.length === 0, hits.join(', '));
  r.check('privacy', 'reports the current setting',
    /have not chosen yet/.test(await page.locator('#consentStatus').textContent()));

  await page.locator('#acceptBtn').click();
  await page.waitForTimeout(250);
  r.check('privacy', 'accept control writes consent',
    (await page.evaluate(k => localStorage.getItem(k), STORAGE_KEY)) === 'granted');

  await page.locator('#rejectBtn').click();
  await page.waitForTimeout(250);
  r.check('privacy', 'withdraw control writes denial',
    (await page.evaluate(k => localStorage.getItem(k), STORAGE_KEY)) === 'denied');

  await context.close();
  await browser.close();
});
