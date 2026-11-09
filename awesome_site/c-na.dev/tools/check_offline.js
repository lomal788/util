// 저장본 검증: serve.js 로 띄운 localhost 만 허용하고 나머지 요청은 막은 채 각 페이지를 열어 빠진 요청을 모은다.
const { chromium } = require('playwright');
const m = require('../site/manifest.json');
const pages = ['/', '/works/giftbede', '/works/iconly-pro', '/works/campaign-lark', '/works/solsta', '/works/maileroo', '/works/wassieverse-canvas', '/works/laelaps', '/tank', '/space-invader', '/tetris', '/pac-man', '/snake', '/explore'];
(async () => {
  const b = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const ctx = await b.newContext({ viewport: process.env.MOBILE ? { width: 390, height: 844 } : { width: 1440, height: 900 }, isMobile: !!process.env.MOBILE });
  const miss = {}; const blocked = {};
  await ctx.route('**/*', r => { const u = new URL(r.request().url()); if (u.hostname === 'localhost') return r.continue(); blocked[u.href] = 1; return r.abort(); });
  ctx.on('response', r => { if (r.status() >= 400 && r.request().method() === 'GET') miss[r.url()] = r.status(); });
  ctx.on('requestfailed', r => { const u = new URL(r.url()); if (u.hostname === 'localhost') miss[r.url()] = r.failure()?.errorText; });
  for (const p of pages) {
    const pg = await ctx.newPage(); const errs = [];
    pg.on('pageerror', e => errs.push(String(e).slice(0, 120)));
    await pg.goto('http://localhost:8787' + p, { waitUntil: 'networkidle' });
    await pg.evaluate(async () => { for (let i = 0; i < 60; i++) { window.scrollBy(0, 600); await new Promise(r => setTimeout(r, 100)); } });
    await pg.waitForTimeout(p === '/explore' ? 15000 : 1500);
    const h = await pg.evaluate(() => [document.title, document.body.innerText.length, document.images.length, [...document.images].filter(i => i.complete && i.naturalWidth === 0).length]);
    console.log(p, JSON.stringify(h), errs.length ? 'ERR ' + [...new Set(errs)].join(' | ') : '');
    await pg.close();
  }
  console.log('missing', Object.keys(miss).length, Object.entries(miss).slice(0, 30));
  console.log('blocked external', Object.keys(blocked).length, Object.keys(blocked).slice(0, 20));
  await b.close();
})();
