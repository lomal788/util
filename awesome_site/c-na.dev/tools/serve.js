// 저장한 사이트를 오프라인으로 연다: node tools/serve.js → http://localhost:8787
// Next.js 는 /_next/... 절대 경로와 쿼리 붙은 이미지 URL 을 쓰므로 file:// 로는 안 열리고, manifest.json 으로 URL 을 파일에 대응시켜 응답한다.
const http = require('http');
const fs = require('fs');
const path = require('path');

const SITE = path.resolve(__dirname, '..', 'site');
const manifest = JSON.parse(fs.readFileSync(path.join(SITE, 'manifest.json'), 'utf8'));
const PORT = Number(process.env.PORT || 8787);

const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.pdf': 'application/pdf', '.mp4': 'video/mp4', '.webm': 'video/webm', '.mp3': 'audio/mpeg', '.wasm': 'application/wasm' };

const crypto = require('crypto');
const ORIGIN = 'https://www.c-na.dev';
async function fill(u, res) {
  const remote = u.pathname.startsWith('/_ext/') ? 'https://' + u.pathname.slice(6) + u.search : ORIGIN + u.pathname + u.search;
  try {
    const r = await fetch(remote, { signal: AbortSignal.timeout(60000) });
    const buf = Buffer.from(await r.arrayBuffer());
    const type = r.headers.get('content-type') || '';
    if (!r.ok) { console.log('fill', r.status, remote); res.writeHead(r.status, { 'content-type': type }); return res.end(buf); }
    let rel = (u.pathname.startsWith('/_ext/') ? u.pathname.slice(1) : decodeURIComponent(u.pathname).slice(1)) || 'index.html';
    if (!path.extname(rel)) rel += '/index.html';
    if (u.search) rel += '__q' + crypto.createHash('sha1').update(u.search).digest('hex').slice(0, 12);
    rel = rel.replace(/[<>:"|*]/g, '_');
    fs.mkdirSync(path.dirname(path.join(SITE, rel)), { recursive: true });
    fs.writeFileSync(path.join(SITE, rel), buf);
    const key = u.pathname.startsWith('/_ext/') ? remote : u.pathname + u.search;
    manifest[key] = { file: rel, status: r.status, type };
    fs.writeFileSync(path.join(SITE, 'manifest.json'), JSON.stringify(manifest, null, 1));
    console.log('fill', r.status, key, buf.length);
    res.writeHead(200, { 'content-type': type });
    res.end(/javascript/.test(type) ? buf.toString('utf8').split('https://www.gstatic.com/').join('/_ext/www.gstatic.com/') : buf);
  } catch (e) { console.log('fill fail', remote, String(e).slice(0, 80)); res.writeHead(502); res.end(); }
}

http.createServer((req, res) => {
  const u = new URL(req.url, 'http://x');
  // POST 는 Vercel·Cloudflare 방문 통계뿐이라 받은 척만 한다
  if (req.method === 'POST') { res.writeHead(204); return res.end(); }
  const isRsc = req.headers['rsc'] === '1';
  const keys = isRsc ? [u.pathname + u.search + ' [rsc]'] : [u.pathname + u.search, u.pathname, u.pathname.replace(/\/$/, '') || '/'];
  // RSC 응답이 없으면 404 를 준다. Next 가 이때 일반 페이지 이동으로 바꿔 HTML 을 다시 받는다.
  let hit = null;
  if (u.pathname.startsWith('/_ext/')) keys.unshift('https://' + u.pathname.slice(6) + u.search, 'https://' + u.pathname.slice(6));
  for (const k of keys) if (manifest[k]) { hit = manifest[k]; break; }
  // 저장할 때 화면 폭에 맞는 크기만 받았으므로, 다른 폭을 요청하면 받아 둔 원본 이미지로 응답한다
  if (!hit && u.pathname === '/_next/image' && u.searchParams.get('url')) hit = manifest[u.searchParams.get('url')] || null;
  if (!hit && !isRsc) {
    const f = Object.keys(manifest).find(k => !k.endsWith('[rsc]') && k.split('?')[0] === u.pathname);
    if (f) hit = manifest[f];
  }
  // 채우기 모드(FILL=1): 코드가 경로를 이어 붙여 부르는 파일(/models/${name}.glb 등)은 미리 알 수 없으므로,
  // 없는 요청이 오면 원본 사이트에서 받아 저장하고 응답한다. RSC 요청은 원본도 상태마다 달라 채우지 않는다
  if (!hit && process.env.FILL && !isRsc) return fill(u, res);
  if (!hit) { res.writeHead(404); return res.end('not saved: ' + req.url); }
  const file = path.join(SITE, hit.file);
  if (!fs.existsSync(file)) { res.writeHead(404); return res.end('missing file'); }
  const type = hit.type || TYPES[path.extname(file)] || 'application/octet-stream';
  res.writeHead(200, { 'content-type': type });
  // /tank 의 3D 모델 해제기(Draco)는 gstatic 에서 직접 받으므로, 인터넷 없이도 되게 응답할 때만 로컬 사본 주소로 바꾼다 (저장 파일은 원본 그대로)
  if (/javascript/.test(type)) return res.end(fs.readFileSync(file, 'utf8').split('https://www.gstatic.com/').join('/_ext/www.gstatic.com/'));
  fs.createReadStream(file).pipe(res);
}).listen(PORT, () => console.log('http://localhost:' + PORT));
