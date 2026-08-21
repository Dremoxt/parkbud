'use strict';

/**
 * A static file server for the repository root.
 *
 * The suites start this in-process rather than relying on a server launched by
 * a separate CI step: a background process that inherits a workflow step's
 * stdout keeps the runner waiting on that log stream, so the step never
 * finishes. Owning the server here removes that failure mode, and makes a
 * local run a single command.
 */
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..', '..');

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.webmanifest': 'application/manifest+json; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
  '.xml': 'application/xml; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.ico': 'image/x-icon',
};

function resolve(urlPath) {
  // Decode, drop the query, and refuse anything that escapes the root.
  let rel;
  try {
    rel = decodeURIComponent(urlPath.split('?')[0]);
  } catch {
    return null;
  }

  let target = path.join(ROOT, rel);
  if (!target.startsWith(ROOT)) return null;

  if (rel.endsWith('/')) target = path.join(target, 'index.html');

  try {
    if (fs.statSync(target).isDirectory()) target = path.join(target, 'index.html');
  } catch {
    return null;
  }

  return fs.existsSync(target) ? target : null;
}

/** Starts on an ephemeral port and resolves with { url, close }. */
function start() {
  return new Promise((resolve_, reject) => {
    const server = http.createServer((req, res) => {
      const file = resolve(req.url);

      if (!file) {
        const notFound = path.join(ROOT, '404.html');
        const body = fs.existsSync(notFound) ? fs.readFileSync(notFound) : 'Not found';
        res.writeHead(404, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(body);
        return;
      }

      res.writeHead(200, {
        'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream',
        'Cache-Control': 'no-store',
      });
      fs.createReadStream(file).pipe(res);
    });

    server.on('error', reject);

    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address();
      resolve_({
        url: `http://127.0.0.1:${port}`,
        close: () => new Promise(done => server.close(done)),
      });
    });
  });
}

module.exports = { start, ROOT };
