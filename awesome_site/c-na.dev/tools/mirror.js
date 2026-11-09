// https://www.c-na.dev/ 를 브라우저로 돌며 받은 응답을 전부 site/ 에 저장한다.
// Next.js 라서 /_next/image?url=... 처럼 쿼리로 구분되는 자원이 많다.
// 파일 이름만으로는 구분이 안 되므로 URL(경로+쿼리) → 파일 대응을 manifest.json 에 남기고 serve.js 가 그걸로 응답한다.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const ORIGIN = 'https://www.c-na.dev';
const ROOT = path.resolve(__dirname, '..');
const SITE = path.join(ROOT, 'site');
const SNAP = path.join(ROOT, 'snapshots');
const MANIFEST = path.join(SITE, 'manifest.json');

const manifest = fs.existsSync(MANIFEST) ? JSON.parse(fs.readFileSync(MANIFEST, 'utf8')) : {};

function fileFor(u) {
  const url = new URL(u);
  let p = decodeURIComponent(url.pathname);
  // /tank 페이지와 /tank/textures/... 자원이 함께 있으므로 확장자 없는 경로는 폴더 안 index.html 로 둔다
  if (p.endsWith('/')) p += 'index.html';
  else if (!path.posix.extname(p)) p += '/index.html';
  const host = url.origin === ORIGIN ? '' : '_ext/' + url.host;
  let rel = host + p;
  if (url.search) {
    const h = crypto.createHash('sha1').update(url.search).digest('hex').slice(0, 12);
    rel += '__q' + h;
  }
  return rel.replace(/^\/+/, '').replace(/[<>:"|*]/g, '_');
}

async function save(resp) {
  const req = resp.request();
  if (req.method() !== 'GET') return;
  const status = resp.status();
  if (status >= 300 && status < 400) return;
  let body;
  try { body = await resp.body(); } catch { return; }
  const u = new URL(resp.url());
  const isRsc = req.headers()['rsc'] === '1';
  const key = (u.origin === ORIGIN ? '' : u.origin) + u.pathname + u.search + (isRsc ? ' [rsc]' : '');
  let rel = fileFor(resp.url());
  if (isRsc) rel += '.rsc';
  const out = path.join(SITE, rel);
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, body);
  manifest[key] = { file: rel.replace(/\\/g, '/'), status, type: resp.headers()['content-type'] || '' };
}

async function autoScroll(page) {
  await page.evaluate(async () => {
    const step = Math.max(200, Math.floor(window.innerHeight * 0.6));
    for (let i = 0; i < 400; i++) {
      const before = window.scrollY;
      window.scrollBy(0, step);
      await new Promise(r => setTimeout(r, 180));
      if (window.scrollY === before && window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2) break;
    }
    await new Promise(r => setTimeout(r, 800));
    window.scrollTo(0, 0);
  });
}

(async () => {
  fs.mkdirSync(SITE, { recursive: true });
  fs.mkdirSync(SNAP, { recursive: true });
  const browser = await chromium.launch();
  // 인자로 경로를 주면 그 페이지만 더 받는다 (예: node mirror.js /explore). manifest 는 이어서 쓴다
  const queue = process.argv.length > 2 ? process.argv.slice(2) : ['/'];
  const seen = new Set(queue);
  const pending = new Set();

  for (const vp of [{ name: 'desktop', width: 1440, height: 900 }, { name: 'mobile', width: 390, height: 844, isMobile: true }]) {
    const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, isMobile: !!vp.isMobile, deviceScaleFactor: vp.isMobile ? 3 : 1 });
    ctx.on('response', r => { const p = save(r); pending.add(p); p.finally(() => pending.delete(p)); });
    const list = vp.name === 'desktop' ? queue : [...seen];
    for (let i = 0; i < list.length; i++) {
      const route = list[i];
      if (/\.(pdf|png|jpe?g|svg|webp|webmanifest|ico|xml|txt)$/i.test(route)) {
        if (vp.name === 'desktop') { const r = await ctx.request.get(ORIGIN + route); const out = path.join(SITE, fileFor(ORIGIN + route)); fs.mkdirSync(path.dirname(out), { recursive: true }); fs.writeFileSync(out, await r.body()); manifest[route] = { file: fileFor(ORIGIN + route), status: r.status(), type: r.headers()['content-type'] || '' }; console.log('asset', route); }
        continue;
      }
      const page = await ctx.newPage();
      try {
        await page.goto(ORIGIN + route, { waitUntil: 'networkidle', timeout: 60000 });
        await autoScroll(page);
        await page.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {});
        // /explore 는 3D 장면이라 모델·텍스처가 늦게 따라온다
        if (route.startsWith('/explore')) { await page.mouse.click(vp.width / 2, vp.height / 2).catch(() => {}); await page.waitForTimeout(15000); await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {}); }
        // 링크에 마우스를 올려 Next 의 미리받기(RSC)도 받아 둔다
        const links = await page.$$eval('a[href]', as => as.map(a => a.getAttribute('href')));
        for (const h of links) {
          if (!h) continue;
          let u; try { u = new URL(h, ORIGIN + route); } catch { continue; }
          if (u.origin !== ORIGIN) continue;
          const r = u.pathname;
          if (!seen.has(r)) { seen.add(r); queue.push(r); }
        }
        const name = (route === '/' ? 'index' : route.replace(/^\//, '').replace(/\//g, '__')) + '.' + vp.name;
        await page.screenshot({ path: path.join(SNAP, name + '.png'), fullPage: true }).catch(e => console.log('shot fail', route, String(e).slice(0, 100)));
        if (vp.name === 'desktop') fs.writeFileSync(path.join(SNAP, name + '.rendered.html'), await page.content());
        console.log(vp.name, route, 'links', links.length);
      } catch (e) {
        console.log('fail', vp.name, route, String(e).slice(0, 200));
      }
      await page.close();
    }
    await Promise.allSettled([...pending]);
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync(MANIFEST, JSON.stringify(manifest, null, 1));
  console.log('pages', [...seen].length, 'resources', Object.keys(manifest).length);
})();
