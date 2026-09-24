// Public tunnel terminates here; serve-sim stays bound to localhost.
const http = require('node:http');
const crypto = require('node:crypto');
const proxy = require('http-proxy').createProxyServer({target: 'http://127.0.0.1:3200', ws: true, xfwd: true});
const password = process.env.PREVIEW_PASSWORD;
if (!password || password.length < 12) throw new Error('AGENT_PREVIEW_PASSWORD must be at least 12 characters');
const session = crypto.randomBytes(32).toString('hex');
const cookies = new Set([`preview_session=${session}`]);
const login = `<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>Agent Preview</title><form method="POST" action="/login"><label>Preview password <input type="password" name="password" autocomplete="off"></label><button>Open simulator</button></form>`;
function authenticated(req) {
  const candidate = (req.headers.cookie || '').split(';').map(x=>x.trim()).find(x=>x.startsWith('preview_session='));
  return !!candidate && cookies.has(candidate);
}
function allowed(req) {
  const path = new URL(req.url, 'http://localhost').pathname;
  // The simulator viewer needs streams and input sockets. Never proxy host command
  // execution, DevTools or unrelated developer endpoints into the public tunnel.
  return !/(^|\/)(exec(?:-ws)?|devtools|terminal|shell)(\/|$)/i.test(path);
}
proxy.on('error', (_err, _req, res) => {
  if (res && !res.headersSent) res.writeHead(502);
  if (res && !res.writableEnded) res.end('Preview upstream unavailable');
});
http.createServer((req, res) => {
  res.setHeader('Cache-Control','no-store');
  if (req.url === '/login' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => { body += chunk; if(body.length > 4096) req.destroy(); });
    req.on('end', () => {
      const supplied = new URLSearchParams(body).get('password') || '';
      const a = crypto.createHash('sha256').update(supplied).digest();
      const b = crypto.createHash('sha256').update(password).digest();
      if (!crypto.timingSafeEqual(a,b)) {res.writeHead(403); res.end('Invalid password'); return;}
      res.writeHead(303, {'Set-Cookie':`preview_session=${session}; HttpOnly; Secure; SameSite=Lax; Path=/`,Location:'/'});
      res.end();
    });
    return;
  }
  if (!authenticated(req)) {res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'}); res.end(login); return;}
  if (!allowed(req)) {res.writeHead(403); res.end('Blocked endpoint'); return;}
  proxy.web(req,res);
}).on('upgrade',(req,socket,head)=>{
  if (!authenticated(req) || !allowed(req)) {socket.write('HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n');socket.destroy();return;}
  const origin = req.headers.origin;
  if (origin && new URL(origin).host !== req.headers.host) {socket.destroy();return;}
  proxy.ws(req,socket,head);
}).listen(3210,'127.0.0.1');
