// FILL=1 로 띄운 serve.js 에 WebGL 켠 브라우저로 붙어 /explore 3D 장면이 부르는 파일을 채운다.
// 물건을 눌러 확대·게임 화면 전환을 일으켜, 눌렀을 때만 불리는 모델·텍스처·소리도 받게 한다.
const { chromium } = require('playwright');
const BASE = 'http://localhost:' + (process.env.PORT || 8787);

(async () => {
  const b = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'] });
  for (const vp of [{ width: 1440, height: 900 }, { width: 390, height: 844, isMobile: true }]) {
    const ctx = await b.newContext({ viewport: { width: vp.width, height: vp.height }, isMobile: !!vp.isMobile });
    const p = await ctx.newPage();
    const bad = new Set();
    p.on('response', r => { if (r.status() >= 400 && r.request().method() === 'GET' && !/_rsc=/.test(r.url())) bad.add(r.status() + ' ' + r.url()); });
    p.on('pageerror', e => bad.add('ERR ' + String(e).slice(0, 150)));
    await p.goto(BASE + '/explore', { waitUntil: 'networkidle', timeout: 120000 });
    console.log('webgl', await p.evaluate(() => !!document.createElement('canvas').getContext('webgl2')));
    await p.waitForTimeout(20000);
    // 화면을 격자로 눌러 물건마다 상호작용을 일으킨다. 눌러서 다른 화면으로 가면 /explore 로 돌아온다
    for (let y = 0.2; y <= 0.9; y += 0.14) {
      for (let x = 0.1; x <= 0.9; x += 0.16) {
        await p.mouse.click(vp.width * x, vp.height * y).catch(() => {});
        await p.waitForTimeout(1500);
        if (!p.url().includes('/explore')) { await p.goto(BASE + '/explore', { waitUntil: 'networkidle' }).catch(() => {}); await p.waitForTimeout(8000); }
        await p.keyboard.press('Escape').catch(() => {});
      }
    }
    await p.waitForLoadState('networkidle').catch(() => {});
    console.log(vp.width, 'still failing', bad.size, [...bad].slice(0, 20));
    await ctx.close();
  }
  await b.close();
})();
