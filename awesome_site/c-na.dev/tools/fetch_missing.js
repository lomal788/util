// mirror.js 뒤에 돌린다. 저장한 HTML·RSC·JS·CSS 안에 문자열로만 있는 같은 사이트 자원(원본 이미지, 효과음, 텍스처 등)을
// 직접 받아 site/ 와 manifest.json 에 더한다. 클릭·게임 진행 때만 불리는 자원은 크롤링으로는 안 받아지기 때문이다.
const fs = require('fs');
const path = require('path');

const ORIGIN = 'https://www.c-na.dev';
const SITE = path.resolve(__dirname, '..', 'site');
const MANIFEST = path.join(SITE, 'manifest.json');
const manifest = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));

const EXT = 'png|jpe?g|webp|avif|svg|gif|ico|mp3|wav|ogg|flac|m4a|aac|mp4|webm|glb|gltf|bin|json|ktx2|hdr|exr|woff2?|ttf|otf|wasm|pdf|txt|webmanifest|xml|csv';
const re = new RegExp(`["'\`(](/(?!/)[A-Za-z0-9_\\-/.%]+\\.(?:${EXT}))(?=["'\`)?#])`, 'g');
const extRe = /https:\/\/www\.gstatic\.com\/draco\/versioned\/decoders\/[0-9.]+\//g;
const DRACO = ['draco_wasm_wrapper.js', 'draco_decoder.wasm', 'draco_decoder.js'];

const scanned = new Set();
let have, refs, ext;
function scan() {
  have = new Set(Object.keys(manifest).map(k => k.replace(' [rsc]', '').split('?')[0]));
  refs = refs || new Set();
  ext = ext || new Set();
  for (const v of Object.values(manifest)) {
    const f = path.join(SITE, v.file);
    if (scanned.has(f)) continue;
    scanned.add(f);
    if (!/html|javascript|css|json|x-component|text|xml/.test(v.type) && !f.endsWith('.rsc')) continue;
    const s = fs.readFileSync(f, 'utf8');
    for (const x of s.matchAll(re)) refs.add(x[1]);
    for (const x of s.matchAll(/url=(%2F[^&"\s\\]+)/g)) refs.add(decodeURIComponent(x[1]));
    // 필요할 때만 불러오는 JS 조각은 앞에 / 없이 "static/chunks/xxx.js" 로 적혀 있다
    for (const x of s.matchAll(/static\/(?:chunks|media|css)\/[A-Za-z0-9_.~\-\/]+?\.(?:js|css|woff2?|png|svg|webp|jpg|wasm)/g)) refs.add('/_next/' + x[0]);
    for (const x of s.matchAll(extRe)) for (const d of DRACO) ext.add(x[0] + d);
  }
}

function fileFor(u) {
  const url = new URL(u);
  const host = url.origin === ORIGIN ? '' : '_ext/' + url.host;
  return (host + decodeURIComponent(url.pathname)).replace(/^\/+/, '').replace(/[<>:"|*]/g, '_');
}

(async () => {
  let ok = 0, bad = [], total = 0;
  const tried = new Set();
  // 새로 받은 조각이 또 다른 조각·자원을 부를 수 있으므로 더 없을 때까지 반복한다
  for (let round = 0; round < 10; round++) {
  scan();
  const todo = [...[...refs].filter(r => !have.has(r)).map(r => ORIGIN + r), ...[...ext].filter(u => !have.has(u))].filter(u => !tried.has(u));
  if (!todo.length) break;
  total += todo.length;
  for (const u of todo) {
    tried.add(u);
    try {
      const r = await fetch(u, { headers: { 'user-agent': 'Mozilla/5.0 (site archive for personal use)' }, signal: AbortSignal.timeout(60000) });
      if (!r.ok) { bad.push(r.status + ' ' + u); continue; }
      const buf = Buffer.from(await r.arrayBuffer());
      const rel = fileFor(u);
      const out = path.join(SITE, rel);
      fs.mkdirSync(path.dirname(out), { recursive: true });
      fs.writeFileSync(out, buf);
      const key = u.startsWith(ORIGIN) ? u.slice(ORIGIN.length) : u;
      manifest[key] = { file: rel, status: r.status, type: r.headers.get('content-type') || '' };
      ok++;
    } catch (e) { bad.push('ERR ' + u + ' ' + String(e).slice(0, 80)); }
  }
  fs.writeFileSync(MANIFEST, JSON.stringify(manifest, null, 1));
  console.log('round', round, 'todo', todo.length);
  }
  console.log('refs', refs.size, 'todo', total, 'saved', ok, 'failed', bad.length);
  for (const b of bad) console.log('  ', b);
})();
