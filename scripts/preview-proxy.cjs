// Browser-facing gateway: only video, HID input and bounded read/typing operations.
// serve-sim itself, including its shell-capable /exec-ws, remains on localhost.
const http = require('node:http');
const crypto = require('node:crypto');
const { execFile } = require('node:child_process');
const proxy = require('http-proxy').createProxyServer({ target: 'http://127.0.0.1:3200', ws: true, xfwd: true });
const password = process.env.PREVIEW_PASSWORD;
const udid = process.env.SIM_UDID;
const scheme = process.env.APP_SCHEME;
const serveSimBin = process.env.SERVE_SIM_BIN;
if (!password || password.length < 12 || !udid || !scheme || !serveSimBin) {
  throw new Error('Set PREVIEW_PASSWORD (12+ characters), SIM_UDID, APP_SCHEME and SERVE_SIM_BIN');
}
const session = crypto.randomBytes(32).toString('hex');
const login = '<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>Agent Preview</title><form method="POST" action="/login"><label>Preview password <input type="password" name="password" autocomplete="off"></label><button>Open simulator</button></form>';
const viewer = `<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Agent Preview</title>
<style>body{background:#111827;color:#f9fafb;font:15px system-ui;margin:0;padding:16px}main{max-width:1200px;margin:auto}header{display:flex;gap:12px;align-items:center;flex-wrap:wrap}button,input{font:inherit;padding:9px;border-radius:8px}button{cursor:pointer}#screen{display:block;margin:16px auto;max-width:100%;max-height:73vh;touch-action:none;background:black;border-radius:28px}#status{color:#a5b4fc}#text{max-width:340px}pre{white-space:pre-wrap;max-height:260px;overflow:auto;background:#1f2937;padding:12px;border-radius:8px}</style>
<main><header><strong>iOS Agent Preview</strong><span id="status">连接中…</span><button id="home">主屏幕</button><input id="text" placeholder="输入到模拟器当前焦点" maxlength="240"><button id="send">输入文字</button><button id="tree">UI Tree</button><button id="logs">日志</button><button id="shot">保存截图</button></header><img id="screen" alt="iOS Simulator 画面"><pre id="output" hidden></pre></main>
<script>
const screen=document.getElementById('screen'),status=document.getElementById('status'),output=document.getElementById('output');
let socket,oldUrl,active=false;
function send(tag,data){if(socket?.readyState!==WebSocket.OPEN)return;const b=new TextEncoder().encode(JSON.stringify(data));const out=new Uint8Array(b.length+1);out[0]=tag;out.set(b,1);socket.send(out)}
function connect(){socket=new WebSocket((location.protocol==='https:'?'wss://':'ws://')+location.host+'/helper/ws');socket.binaryType='arraybuffer';socket.onopen=()=>{status.textContent='画面连接成功 · 可点击或滑动'};socket.onclose=()=>{status.textContent='连接断开，正在重连';setTimeout(connect,2000)};socket.onerror=()=>{status.textContent='控制连接失败'}}connect();
function point(e){const r=screen.getBoundingClientRect();return{x:Math.max(0,Math.min(1,(e.clientX-r.left)/r.width)),y:Math.max(0,Math.min(1,(e.clientY-r.top)/r.height))}}
screen.onpointerdown=e=>{if(!screen.src)return;screen.setPointerCapture(e.pointerId);active=true;send(3,{type:'begin',...point(e)})};
screen.onpointermove=e=>{if(active)send(3,{type:'move',...point(e)})};screen.onpointerup=e=>{if(active)send(3,{type:'end',...point(e)});active=false};screen.onpointercancel=e=>{if(active)send(3,{type:'end',...point(e)});active=false};
document.getElementById('home').onclick=()=>send(4,{button:'home'});
async function request(path,options){output.hidden=false;output.textContent='加载中…';try{const r=await fetch(path,options);const value=await r.text();output.textContent=r.ok?value:'请求失败：'+value}catch(e){output.textContent=String(e)}}
document.getElementById('send').onclick=()=>{const text=document.getElementById('text').value;if(text)request('/type',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})})};
document.getElementById('tree').onclick=()=>request('/tree');document.getElementById('logs').onclick=()=>request('/logs');
document.getElementById('shot').onclick=()=>{if(!screen.src)return;const c=document.createElement('canvas');c.width=screen.naturalWidth;c.height=screen.naturalHeight;c.getContext('2d').drawImage(screen,0,0);const a=document.createElement('a');a.download='agent-preview.png';a.href=c.toDataURL('image/png');a.click()};
let pending=new Uint8Array(0);
async function stream(){try{const res=await fetch('/helper/stream.mjpeg?raw=1',{cache:'no-store'});if(!res.ok||!res.body)throw new Error('视频不可用');const reader=res.body.getReader();while(true){const {value,done}=await reader.read();if(done)break;const next=new Uint8Array(pending.length+value.length);next.set(pending);next.set(value,pending.length);pending=next;for(;;){let start=-1,end=-1;for(let i=0;i<pending.length-1;i++){if(pending[i]===255&&pending[i+1]===216){start=i;break}}if(start<0)break;for(let i=start+2;i<pending.length-1;i++){if(pending[i]===255&&pending[i+1]===217){end=i+2;break}}if(end<0){pending=pending.slice(start);break}const url=URL.createObjectURL(new Blob([pending.slice(start,end)],{type:'image/jpeg'}));screen.onload=()=>{if(oldUrl)URL.revokeObjectURL(oldUrl);oldUrl=url};screen.src=url;pending=pending.slice(end)}if(pending.length>8_000_000)pending=new Uint8Array(0)}}catch(e){status.textContent=String(e)}setTimeout(stream,1500)}stream();
</script></html>`;
function authenticated(req) {
  return (req.headers.cookie || '').split(';').some(x => x.trim() === `preview_session=${session}`);
}
function respond(res,code,body,type='text/plain; charset=utf-8') {
  res.writeHead(code,{'Cache-Control':'no-store','Content-Type':type,'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'});res.end(body);
}
function sameOrigin(req) {
  try { return !req.headers.origin || new URL(req.headers.origin).host === req.headers.host; }
  catch { return false; }
}
function run(res,bin,args,timeout=30000) {
  execFile(bin,args,{timeout,maxBuffer:4*1024*1024},(error,stdout,stderr)=> {
    if(error)respond(res,503,stderr || error.message);
    else respond(res,200,stdout);
  });
}
proxy.on('error',(_err,_req,res)=>{if(res&&!res.headersSent)res.writeHead(502);if(res&&!res.writableEnded)res.end('Preview upstream unavailable')});
http.createServer((req,res)=>{
  const url=new URL(req.url,'http://localhost');
  if(url.pathname==='/login'&&req.method==='POST'){
    let body='';req.on('data',part=>{body+=part;if(body.length>4096)req.destroy()});
    req.on('end',()=>{const supplied=new URLSearchParams(body).get('password')||'';
      const a=crypto.createHash('sha256').update(supplied).digest(),b=crypto.createHash('sha256').update(password).digest();
      if(!crypto.timingSafeEqual(a,b))return respond(res,403,'Invalid password');
      res.writeHead(303,{'Cache-Control':'no-store','Set-Cookie':`preview_session=${session}; HttpOnly; Secure; SameSite=Strict; Path=/`,Location:'/'});res.end()});return;
  }
  if(!authenticated(req))return respond(res,200,login,'text/html; charset=utf-8');
  if(url.pathname==='/'&&req.method==='GET')return respond(res,200,viewer,'text/html; charset=utf-8');
  if(url.pathname==='/helper/stream.mjpeg'&&req.method==='GET'&&url.searchParams.get('raw')==='1')return proxy.web(req,res);
  if(!sameOrigin(req))return respond(res,403,'Cross-origin request blocked');
  if(url.pathname==='/type'&&req.method==='POST'){
    let body='';req.on('data',part=>{body+=part;if(body.length>2048)req.destroy()});
    req.on('end',()=>{let text;try{text=JSON.parse(body).text}catch{return respond(res,400,'Invalid input')}
      if(typeof text!=='string'||text.length<1||text.length>240)return respond(res,400,'Text must contain 1-240 characters');
      run(res,serveSimBin,['type',text,'-d',udid],20000)});return;
  }
  if(url.pathname==='/tree'&&req.method==='GET')return run(res,'npx',['--yes','xcodebuildmcp@2.7.0','ui-automation','snapshot-ui','--simulator-id',udid,'--output','json'],45000);
  if(url.pathname==='/logs'&&req.method==='GET')return run(res,'xcrun',['simctl','spawn',udid,'log','show','--last','2m','--style','compact','--predicate',`process == '${scheme}'`],25000);
  respond(res,404,'Not found');
}).on('upgrade',(req,socket,head)=>{
  let path;try{path=new URL(req.url,'http://localhost').pathname}catch{socket.destroy();return}
  if(!authenticated(req)||!sameOrigin(req)||path!=='/helper/ws') {socket.write('HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n');socket.destroy();return}
  proxy.ws(req,socket,head);
}).listen(3210,'127.0.0.1');
