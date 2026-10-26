const { chromium } = require('playwright');
(async () => {
  const proxy = process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY, bypass: '127.0.0.1,localhost' } : undefined;
  const browser = await chromium.launch({ proxy, args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] });
  const errs = [];
  for (const [name, w, h, scheme] of [['desk_light', 1280, 900, 'light'], ['phone_dark', 400, 860, 'dark']]) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, colorScheme: scheme, ignoreHTTPSErrors: true });
    const page = await ctx.newPage();
    page.on('console', m => { if (m.type() === 'error') errs.push(`${name}: ${m.text()}`); });
    page.on('pageerror', e => errs.push(`${name}: pageerror ${e.message}`));
    await page.goto('http://127.0.0.1:8765/wrapped.html', { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(2500);
    const sw = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    if (sw > 0) errs.push(`${name}: horizontal overflow ${sw}px`);
    await page.screenshot({ path: `${process.argv[2]}/shot_${name}.png`, fullPage: name === 'desk_light' });
    await ctx.close();
  }
  console.log(JSON.stringify(errs, null, 1));
  await browser.close();
})();
