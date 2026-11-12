import assert from "node:assert/strict";
import { readFileSync, readdirSync, existsSync } from "node:fs";
import test from "node:test";
import ts from "typescript";
const root = new URL("../src/features/analisis-frotis-v2/", import.meta.url);
const read = (path) => readFileSync(new URL(path, root), "utf8");
const load = async (path) =>
  import(
    `data:text/javascript;base64,${Buffer.from(ts.transpileModule(read(path), { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText).toString("base64")}`
  );
const math = await load("utils/hematology.ts");
const { workflowRoutes } = await load("routes.ts");
test("five unique URL paths have separate pages and reuse the full field visual", () => {
  assert.equal(new Set(workflowRoutes.map((route) => route.path)).size, 5);
  for (const page of [
    "ReviewCellsPage",
    "FullFieldReviewPage",
    "SpecimenQualityPage",
    "AnalysisAreaPage",
    "ReportPage",
  ])
    assert.ok(existsSync(new URL(`pages/${page}.tsx`, root)));
  assert.match(
    read("pages/FullFieldReviewPage.tsx"),
    /isAnalysisArea=\{false\}/,
  );
  assert.match(read("pages/AnalysisAreaPage.tsx"), /isAnalysisArea=\{true\}/);
});
test("reclassification preserves source data, identity and unrelated cells", () => {
  const cells = [
    { id: 1, name: "Blast", category: "Blast", x: 10, y: 20 },
    { id: 2, category: "Monocyte", name: "Monocyte" },
  ];
  const changed = math.reclassifyCell(cells, 1, "Promyelocyte");
  assert.equal(changed[0].category, "Promyelocyte");
  assert.equal(changed[0].id, 1);
  assert.equal(changed[0].x, 10);
  assert.equal(cells[0].category, "Blast");
  assert.deepEqual(changed[1], cells[1]);
  const stats = math.calculateDifferential({
    Blast: 110,
    Promyelocyte: 343,
    Other: 47,
  });
  assert.equal(stats.totalCount, 500);
  assert.equal(stats.percentages.Promyelocyte, 68.6);
});
test("module has no backend transport, inference, credentials or essential remote resources", () => {
  const walk = (dir) =>
    readdirSync(dir, { withFileTypes: true }).flatMap((entry) =>
      entry.isDirectory()
        ? walk(new URL(`${entry.name}/`, dir))
        : [new URL(entry.name, dir)],
    );
  for (const file of walk(root).filter((file) =>
    /\.(ts|tsx)$/.test(file.pathname),
  )) {
    const source = readFileSync(file, "utf8");
    assert.doesNotMatch(
      source,
      /services\/api|@google\/genai|XMLHttpRequest|axios|WebSocket|GEMINI_API_KEY/,
    );
    assert.doesNotMatch(source, /(?:src|href)=["']https?:/);
    for (const match of source.matchAll(/fetch\(['"]([^'"]+)/g))
      assert.equal(match[1], "/analisis-frotis-v2/visor-standalone.html");
  }
  for (const resource of [
    "visor-standalone.html",
    "assets/aistudio/visor_full_d875328e.png",
    "assets/aistudio/visor_analisis_d923d6e9.html",
  ])
    assert.ok(
      existsSync(
        new URL(`../public/analisis-frotis-v2/${resource}`, import.meta.url),
      ),
    );
});
