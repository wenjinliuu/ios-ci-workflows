// End-to-end smoke test through the Cloudflare hostname, without logging secrets.
const assert = require('node:assert/strict');
const WebSocket = require('ws');
const origin = process.env.PREVIEW_URL;
const password = process.env.PREVIEW_PASSWORD;
assert.match(origin || '', /^https:\/\/[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}$/);
assert.ok(password);

async function main() {
  const loginPage = await fetch(origin, { signal: AbortSignal.timeout(15000) });
  assert.equal(loginPage.status, 200);
  assert.match(await loginPage.text(), /Preview password/);

  const login = await fetch(`${origin}/login`, {
    method: 'POST',
    redirect: 'manual',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ password }),
    signal: AbortSignal.timeout(15000),
  });
  assert.equal(login.status, 303);
  const cookie = login.headers.get('set-cookie')?.split(';')[0];
  assert.match(cookie || '', /^preview_session=[a-f0-9]{64}$/);
  const headers = { Cookie: cookie };
  const page = await fetch(origin, { headers, signal: AbortSignal.timeout(15000) });
  assert.equal(page.status, 200);
  assert.match(await page.text(), /iOS Agent Preview/);
  const blocked = await fetch(`${origin}/exec-ws`, { headers, signal: AbortSignal.timeout(15000) });
  assert.equal(blocked.status, 404);

  const abort = new AbortController();
  const timer = setTimeout(() => abort.abort(), 20000);
  try {
    const stream = await fetch(`${origin}/helper/stream.mjpeg?raw=1`, {
      headers,
      signal: abort.signal,
    });
    assert.equal(stream.status, 200);
    const reader = stream.body.getReader();
    let bytes = Buffer.alloc(0);
    while (!bytes.includes(Buffer.from([0xff, 0xd8])) && bytes.length < 32768) {
      const frame = await reader.read();
      assert.equal(frame.done, false, 'The video stream closed before a frame arrived');
      bytes = Buffer.concat([bytes, frame.value]);
    }
    assert.ok(bytes.includes(Buffer.from([0xff, 0xd8])), 'No JPEG frame reached Cloudflare');
    await reader.cancel();
  } finally {
    clearTimeout(timer);
    abort.abort();
  }

  await new Promise((resolve, reject) => {
    const ws = new WebSocket(origin.replace(/^https:/, 'wss:') + '/helper/ws', {
      headers: { Cookie: cookie, Origin: origin },
      handshakeTimeout: 15000,
    });
    ws.once('open', () => { ws.close(); resolve(); });
    ws.once('error', reject);
  });
  console.log('Cloudflare login, simulator JPEG stream, HID WebSocket and shell isolation verified');
}

main().catch(error => {
  console.error('Public preview check:', error.message);
  if (error.cause) console.error('Network cause:', error.cause.code || error.cause.message);
  process.exitCode = 1;
});
