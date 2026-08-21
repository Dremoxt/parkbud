'use strict';

const BASE_URL = process.env.BASE_URL || 'http://localhost:8099';

// Chromium ships in the CI image at a known path; locally Playwright finds its own.
const LAUNCH = process.env.CHROMIUM_PATH
  ? { executablePath: process.env.CHROMIUM_PATH }
  : {};

const PAGES = [
  ['en', '/'],
  ['hu', '/hu/'],
  ['de', '/de/'],
  ['ro', '/ro/'],
  ['sr', '/sr/'],
  ['hr', '/hr/'],
  ['sk', '/sk/'],
];

const TRACKER = /googletagmanager\.com|google-analytics\.com|contentsquare\.net|analytics\.google\.com/;

/**
 * Cut the page off from the internet.
 *
 * Requests still fire their events, so "nothing was requested before consent"
 * stays meaningful, but no test outcome depends on Google or Contentsquare
 * being reachable from the runner.
 */
async function isolate(context) {
  await context.route('**/*', route => {
    const url = route.request().url();
    if (url.startsWith(BASE_URL)) return route.continue();
    return route.abort();
  });
}

function reporter() {
  const state = { failures: 0 };

  state.check = function (tag, name, condition, detail) {
    if (condition) {
      console.log(`  ok   [${tag}] ${name}`);
      return true;
    }
    state.failures++;
    console.log(`  FAIL [${tag}] ${name}${detail ? ' :: ' + detail : ''}`);
    return false;
  };

  state.finish = function (label) {
    console.log('');
    if (state.failures === 0) {
      console.log(`${label}: ALL CHECKS PASSED`);
      process.exit(0);
    }
    console.log(`${label}: ${state.failures} CHECK(S) FAILED`);
    process.exit(1);
  };

  return state;
}

module.exports = { BASE_URL, LAUNCH, PAGES, TRACKER, isolate, reporter };
