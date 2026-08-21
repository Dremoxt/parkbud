'use strict';

const { start } = require('./server');

// Chromium ships in some images at a known path; otherwise Playwright finds its own.
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
 * Serve the site, run the suite against it, then shut down and exit with the
 * right status. BASE_URL overrides the built-in server for a run against
 * something already serving the files.
 */
async function run(label, suite) {
  const external = process.env.BASE_URL;
  const server = external ? null : await start();
  const baseUrl = external || server.url;

  const state = { failures: 0, baseUrl };

  state.check = function (tag, name, condition, detail) {
    if (condition) {
      console.log(`  ok   [${tag}] ${name}`);
      return true;
    }
    state.failures++;
    console.log(`  FAIL [${tag}] ${name}${detail ? ' :: ' + detail : ''}`);
    return false;
  };

  /**
   * Cut a browser context off from the internet.
   *
   * Requests still fire their events, so "nothing was requested before consent"
   * stays a real assertion, but no outcome depends on Google or Contentsquare
   * being reachable from the runner.
   */
  state.isolate = async function (context) {
    await context.route('**/*', route => {
      const url = route.request().url();
      return url.startsWith(baseUrl) ? route.continue() : route.abort();
    });
  };

  let failed = false;
  try {
    await suite(state);
  } catch (error) {
    failed = true;
    console.log(`\n${label}: suite threw before finishing`);
    console.error(error);
  } finally {
    if (server) await server.close();
  }

  console.log('');
  if (!failed && state.failures === 0) {
    console.log(`${label}: ALL CHECKS PASSED`);
    process.exit(0);
  }
  console.log(`${label}: ${state.failures} CHECK(S) FAILED${failed ? ' (suite aborted)' : ''}`);
  process.exit(1);
}

module.exports = { LAUNCH, PAGES, TRACKER, run };
