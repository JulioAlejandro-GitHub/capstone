// Visual regression: capture before edits, then compare with the same Chrome version.
// PLAYWRIGHT_MODULE, CHROME_PATH, FRONTEND_URL, DESIGN_EVIDENCE_DIR are configurable.
// node tests/browser/frotis-v2-design.cjs capture|compare
const fs = require('node:fs');
const path = require('node:path');
const { chromium, expect } = require(process.env.PLAYWRIGHT_MODULE || '@playwright/test');
const mode = process.argv[2] || 'compare';
const output = process.env.DESIGN_EVIDENCE_DIR || '/tmp/frotis-v2-design';
const base = process.env.FRONTEND_URL || 'http://127.0.0.1:5173';

async function checkTokens(page) {
  const root = page.locator('.frotis-v2');
  const preset = page.getByTitle('Perfil de tinción 1', { exact: true });
  await expect(preset).toHaveCSS('background-color', 'rgb(77, 88, 164)');
  await root.evaluate(element => {
    for (const [name, value] of Object.entries({ primary: 'rgb(1, 2, 3)',
      'header-height': '112px', 'sidebar-width': '320px', 'radius-button': '8px',
      'surface': 'rgb(250, 240, 220)' })) element.style.setProperty(`--frotis-v2-${name}`, value);
  });
  await expect(preset).toHaveCSS('background-color', 'rgb(1, 2, 3)');
  await expect(preset).toHaveCSS('border-radius', '8px');
  await expect(root.locator('.frotis-header-row')).toHaveCSS('min-height', '112px');
  await expect(root.locator('aside')).toHaveCSS('width', '320px');
  await expect(root.locator('aside')).toHaveCSS('background-color', 'rgb(250, 240, 220)');
  await expect(root.locator('header')).toHaveCSS('background-color', 'rgb(250, 240, 220)');
  await page.getByTitle('Abrir o cambiar caso clínico').focus();
  await page.keyboard.press('Enter');
  await expect(page.getByText('Casos Hematológicos Disponibles')).toBeVisible();
  await expect(page.getByText('Casos Hematológicos Disponibles').locator('..'))
    .toHaveCSS('background-color', 'rgb(250, 240, 220)');
  await page.getByTitle('Abrir o cambiar caso clínico').press('Enter');
  await page.getByTitle('Compartir / Exportar reporte o datos').click();
  const modal = root.locator('.fixed');
  await expect(modal).toBeVisible();
  expect(await modal.evaluate(element => !!element.closest('.frotis-v2'))).toBe(true);
  await expect(modal.locator(':scope > div')).toHaveCSS('background-color', 'rgb(250, 240, 220)');
  await modal.getByRole('button', { name: 'Cerrar', exact: true }).first().click();
  await page.getByRole('button', { name: 'REPORT', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Exportar PDF', exact: true }))
    .toHaveCSS('background-color', 'rgb(1, 2, 3)');
  await root.evaluate(element => element.removeAttribute('style'));
  console.log('PASS: live primary, header, sidebar, button radius, surface inheritance in menus/modals, keyboard activation.');
}

(async () => {
  const browser = await chromium.launch({ headless: true,
    ...(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {}) });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, reducedMotion: 'reduce' });
  const errors = [];
  const results = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => localStorage.setItem('capstone.access_token', 'demo-test'));
  await page.route('**/api/**', route => route.fulfill({ json:
    route.request().url().includes('/auth/me')
      ? { id: 'test', username: 'demo', roles: [], permissions: [] }
      : { items: [{ key: 'malaria', label: 'Malaria', domain: 'Parasitos', enabled: true }] }
  }));
  fs.mkdirSync(path.join(output, mode === 'capture' ? 'before' : 'after'), { recursive: true });
  async function snapshot(name) {
    await page.mouse.move(1599, 999);
    await page.evaluate(() => document.fonts.ready);
    const file = path.join(output, mode === 'capture' ? 'before' : 'after', `${name}.png`);
    await page.screenshot({ path: file, fullPage: true, animations: 'disabled' });
    if (mode === 'compare') {
      const { PNG } = require(process.env.PNGJS_MODULE || 'pngjs');
      const { default: pixelmatch } = await import(process.env.PIXELMATCH_MODULE || 'pixelmatch');
      const before = PNG.sync.read(fs.readFileSync(path.join(output, 'before', `${name}.png`)));
      const after = PNG.sync.read(fs.readFileSync(file));
      expect([after.width, after.height]).toEqual([before.width, before.height]);
      const diff = new PNG({ width: after.width, height: after.height });
      const pixels = pixelmatch(before.data, after.data, diff.data, after.width, after.height,
        { threshold: 0.1, includeAA: false });
      let rawPixels = 0;
      let maxChannelDelta = 0;
      for (let i = 0; i < before.data.length; i += 4) {
        let changed = false;
        for (let channel = 0; channel < 4; channel++) {
          const delta = Math.abs(before.data[i + channel] - after.data[i + channel]);
          changed ||= delta > 0;
          maxChannelDelta = Math.max(maxChannelDelta, delta);
        }
        if (changed) rawPixels++;
      }
      if (pixels) fs.writeFileSync(path.join(output, 'after', `${name}-diff.png`), PNG.sync.write(diff));
      results.push({ name, pixels, rawPixels, maxChannelDelta, total: after.width * after.height });
    }
  }
  async function navigate(route) {
    await page.goto(`${base}${route}`);
    await page.waitForLoadState('networkidle');
  }
  try {
    for (const tab of ['full-field-review', 'specimen-quality', 'analysis-area', 'review-cells', 'report']) {
      await navigate(`/frotis/analisis-2/${tab}`);
      await expect(page.locator('.af2 > header')).toBeVisible();
      await snapshot(tab);
    }
    await navigate('/frotis/analisis-2/review-cells');
    await page.getByTitle('Abrir o cambiar caso clínico').click();
    await snapshot('case-menu');
    await page.getByTitle('Abrir o cambiar caso clínico').click();
    await page.getByTitle('Opciones de visualización de la imagen (Brillo, Contraste, Saturación, Gamma)').click();
    await snapshot('image-popover');
    await page.getByTitle('Opciones de visualización de la imagen (Brillo, Contraste, Saturación, Gamma)').click();
    await page.getByTitle('Cambiar tipo de célula').first().locator('..').dblclick();
    await snapshot('cell-detail');
    await page.locator('.af2 .fixed').getByRole('button', { name: 'Cerrar', exact: true }).first().click();
    await page.getByText('Click here to add comment', { exact: true }).click();
    await snapshot('notes');
    await page.locator('.af2 .fixed').getByRole('button', { name: 'Cerrar', exact: true }).first().click();
    await page.getByTitle('Compartir / Exportar reporte o datos').click();
    await snapshot('export');
    await page.locator('.af2 .fixed').getByRole('button', { name: 'Cerrar', exact: true }).first().click();
    await page.getByTitle('Ver o descargar versión HTML autocontenida de un único archivo').click();
    await snapshot('html-modal');
    // The application's eagerly imported module CSS is present on these other routes too.
    for (const [name, route] of [['history', '/frotis/historial'], ['workflow', '/frotis/analizar'], ['model-summary', '/modelo-ia/resumen']]) {
      await navigate(route);
      await snapshot(name);
    }
    if (mode === 'compare') {
      await navigate('/frotis/analisis-2/review-cells');
      await checkTokens(page);
      const responsive = [];
      for (const width of [390, 768, 1280]) {
        await page.setViewportSize({ width, height: 900 });
        for (const tab of ['full-field-review', 'specimen-quality', 'analysis-area', 'review-cells', 'report']) {
          await navigate(`/frotis/analisis-2/${tab}`);
          const size = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth,
            document: document.documentElement.scrollWidth }));
          expect(size.document).toBeLessThanOrEqual(size.viewport);
          responsive.push({ width, tab, ...size });
        }
      }
      fs.writeFileSync(path.join(output, 'comparison.json'), JSON.stringify({
        date: '2026-11-04', browser: await browser.version(), viewport: '1600x1000',
        session: 'mocked; no real backend', pixelmatch: { threshold: 0.1, includeAA: false },
        results, responsive, tokenChecks: 'passed', errors,
      }, null, 2) + '\n');
      console.log(JSON.stringify(results));
      expect(results.filter(result => result.pixels > 0)).toEqual([]);
    }
    expect(errors).toEqual([]);
    console.log(`PASS: ${mode}, 14 visual states, mocked session.`);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
