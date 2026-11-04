// Run with PLAYWRIGHT_MODULE=/absolute/path/to/@playwright/test node tests/browser/frotis-v2.cjs
const { chromium, expect } = require(
  process.env.PLAYWRIGHT_MODULE || "@playwright/test",
);
(async () => {
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.CHROME_PATH
      ? { executablePath: process.env.CHROME_PATH }
      : {}),
  });
  const page = await browser.newPage({
    viewport: { width: 1600, height: 1000 },
  });
  page.setDefaultTimeout(8000);
  const errors = [];
  const requests = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    if (request.url().includes("/api/")) requests.push(request.url());
  });
  // Exercise the real authentication guard with a mocked session, never a real backend.
  await page.addInitScript(() =>
    localStorage.setItem("capstone.access_token", "demo-test"),
  );
  await page.route("**/api/**", (route) =>
    route.fulfill({
      json: route.request().url().includes("/auth/me")
        ? { id: "test", username: "demo", roles: [], permissions: [] }
        : {
            items: [
              {
                key: "malaria",
                label: "Malaria",
                domain: "Parasitos",
                enabled: true,
              },
            ],
          },
    }),
  );
  try {
    await page.goto(
      `${process.env.FRONTEND_URL || "http://127.0.0.1:5173"}/frotis/analisis-2`,
    );
    await expect(page).toHaveURL(/\/review-cells\?/);
    await expect(
      page
        .getByRole("link", { name: "Análisis de frotis 2", exact: true })
        .first(),
    ).toBeVisible();
    await expect(page.locator(".af2 > header").getByText("Visor", { exact: true })).toBeVisible();
    console.log("redirect and Visor naming checked");
    const initialRequests = requests.length;
    for (const [tab, path] of [
      ["FULL FIELD REVIEW", "full-field-review"],
      ["SPECIMEN QUALITY", "specimen-quality"],
      ["ANALYSIS AREA", "analysis-area"],
      ["REVIEW CELLS", "review-cells"],
      ["REPORT", "report"],
    ]) {
      await page.getByRole("button", { name: tab, exact: true }).click();
      await expect(page).toHaveURL(new RegExp(`/${path}\\?`));
      await page.reload();
      await expect(
        page.getByRole("button", { name: tab, exact: true }),
      ).toHaveAttribute("aria-current", "page");
    }
    await page
      .getByRole("button", { name: "REVIEW CELLS", exact: true })
      .click();
    const interactionRequests = requests.length;
    await page.getByTitle("Abrir o cambiar caso clínico").click();
    const cases = page.locator("button").filter({ hasText: /CASE / });
    await cases.last().click();
    await page.getByRole("button", { name: /STATUS:/ }).click();
    await page.getByRole("button", { name: "Flagged", exact: true }).click();
    await expect(page.getByRole("button", { name: /STATUS:/ })).toContainText(
      "Flagged",
    );
    await page.getByTitle("Perfil de tinción 2", { exact: true }).click();
    await page
      .getByTitle(
        "Opciones de visualización de la imagen (Brillo, Contraste, Saturación, Gamma)",
      )
      .click();
    await expect(page.getByText("brightness", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "RESET", exact: true }).click();
    await page
      .getByTitle(
        "Opciones de visualización de la imagen (Brillo, Contraste, Saturación, Gamma)",
      )
      .click();
    for (const title of [
      "Solo Galería de Células",
      "Solo Vista de Frotis Completo",
      "Vista Dividida (Galería + Frotis)",
    ])
      await page.getByTitle(title, { exact: true }).click();
    console.log("presets and layout checked");
    // Restore the initial category/case before inspecting a populated gallery.
    await page.getByTitle("Abrir o cambiar caso clínico").click();
    await cases.first().click();
    // Category selection determines the gallery independently of reclassification.
    await page
      .locator(".af2")
      .getByText("Promyelocyte", { exact: true })
      .first()
      .click();
    await page
      .getByTitle("Cambiar tipo de célula")
      .first()
      .locator("..")
      .dblclick();
    await expect(
      page.getByText("Inspección Morfológica de Alta Resolución"),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Marcar para revisión", exact: true })
      .click();
    await expect(
      page.getByRole("button", { name: "Marcada para revisión", exact: true }),
    ).toBeVisible();
    await page.locator(".af2 .fixed select").selectOption("Blast");
    await page
      .locator(".af2 .fixed")
      .getByRole("button", { name: "Cerrar", exact: true })
      .first()
      .click();
    await page.getByText("Click here to add comment", { exact: true }).click();
    await page
      .getByPlaceholder("Añadir comentario clínico o hallazgo...")
      .fill("Nota temporal de prueba");
    await page.locator('.af2 form button[type="submit"]').click();
    await expect(page.getByText("Nota temporal de prueba")).toBeVisible();
    await page
      .locator(".af2 .fixed")
      .getByRole("button", { name: "Cerrar", exact: true })
      .first()
      .click();
    console.log("notes and detail checked");
    await page.getByTitle("Compartir / Exportar reporte o datos").click();
    await expect(page.getByText(/Exportar Datos del Caso/)).toBeVisible();
    const download = page.waitForEvent("download");
    await page
      .getByText("Recuento Diferencial en CSV (Excel)", { exact: true })
      .click();
    await download;
    await page
      .locator(".af2 .fixed")
      .getByRole("button", { name: "Cerrar", exact: true })
      .first()
      .click();
    await page
      .getByTitle(
        "Ver o descargar versión HTML autocontenida de un único archivo",
      )
      .click();
    await expect(
      page.getByText("Archivo HTML Autocontenido (Requerimiento de Maqueta)"),
    ).toBeVisible();
    await page
      .locator(".af2 .fixed")
      .getByRole("button", { name: "Cerrar", exact: true })
      .first()
      .click();
    expect(requests.length).toBe(interactionRequests);
    const before = requests.length;
    await page.getByRole("button", { name: "REPORT", exact: true }).click();
    await expect(
      page.getByText("INFORME DE MORFOLOGÍA HEMATOLÓGICA DIGITAL"),
    ).toBeVisible();
    page.once("dialog", dialog => dialog.accept());
    await page.getByRole("button", { name: "Firmar y Validar Informe" }).click();
    await expect(page.getByText("Informe Firmado Digitalmente")).toBeVisible();
    await expect(page.getByRole("button", { name: /STATUS:/ })).toContainText("Signed-off");
    expect(requests.length).toBe(before);
    for (const asset of [
      "visor-standalone.html",
      "assets/aistudio/visor_full_d875328e.png",
      "assets/aistudio/visor_analisis_d923d6e9.html",
    ]) {
      const response = await page.request.get(
        new URL(`/analisis-frotis-v2/${asset}`, page.url()).href,
      );
      expect(response.status()).toBe(200);
    }
    await page
      .getByRole("button", { name: "REVIEW CELLS", exact: true })
      .click();
    await page.screenshot({
      path: process.env.SCREENSHOT_PATH || "/tmp/frotis-v2.png",
      fullPage: true,
    });
    expect(errors).toEqual([]);
    const anonymous = await browser.newPage();
    await anonymous.route("**/api/**", route => route.fulfill({ json: { items: [] } }));
    await anonymous.goto(`${process.env.FRONTEND_URL || "http://127.0.0.1:5173"}/frotis/analisis-2/report`);
    await expect(anonymous).toHaveURL(/\/login/);
    await anonymous.close();
    const resources = await browser.newPage();
    for (const [oldPath, newPath] of [
      ["visor-standalone.html", "visor-standalone.html"],
      ["assets/aistudio/scopio_analisis_d923d6e9.html", "assets/aistudio/visor_analisis_d923d6e9.html"],
    ]) {
      await resources.goto(new URL(`/analisis-frotis-v2/${oldPath}?demo=1#reference`, page.url()).href);
      await expect(resources).toHaveURL(new URL(`/analisis-frotis-v2/${newPath}?demo=1#reference`, page.url()).href);
      await resources.reload();
      await expect(resources).toHaveURL(new URL(`/analisis-frotis-v2/${newPath}?demo=1#reference`, page.url()).href);
    }
    await resources.close();
    console.log(
      "PASS: five routes and reload, case/status/presets/layout, detail/reclassification/flag, notes, CSV/HTML modals, assets, no runtime errors.",
    );
    console.log(
      `Existing shell requests observed: ${initialRequests}; route reloads repeat existing auth/catalog requests.`,
    );
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
