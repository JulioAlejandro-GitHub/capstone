// CSS is checked in: no Tailwind plugin or reset is added to the host application.
// npm install --prefix /tmp/frotis-css @tailwindcss/cli@4.3.3 tailwindcss@4.3.3 postcss@8
// FROTIS_CSS_TOOLS=/tmp/frotis-css/node_modules node scripts/generate-frotis-css.cjs
const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");
const { execFileSync } = require("node:child_process");
const tools = process.env.FROTIS_CSS_TOOLS;
if (!tools)
  throw new Error(
    "Set FROTIS_CSS_TOOLS to the temporary node_modules containing the pinned Tailwind CLI and postcss.",
  );
const postcss = require(path.join(tools, "postcss"));
const frontend = path.resolve(__dirname, "..");
const moduleDir = path.join(frontend, "src/features/analisis-frotis-v2");
const standalone = path.join(
  frontend,
  "public/analisis-frotis-v2/visor-standalone.html",
);
const temp = fs.mkdtempSync(path.join(os.tmpdir(), "frotis-css-"));
try {
  fs.writeFileSync(
    path.join(temp, "input.css"),
    `@import ${JSON.stringify(path.join(tools, "tailwindcss/index.css"))};\n@source ${JSON.stringify(moduleDir)};\n@source ${JSON.stringify(standalone)};\n`,
  );
  execFileSync(process.execPath, [
    path.join(tools, "@tailwindcss/cli/dist/index.mjs"),
    "-i",
    path.join(temp, "input.css"),
    "-o",
    path.join(temp, "output.css"),
  ]);
  const raw = fs.readFileSync(path.join(temp, "output.css"), "utf8");
  const root = postcss.parse(raw);
  // Flatten layers so host unlayered element rules cannot override the mockup utilities.
  root.walkAtRules("layer", (rule) => {
    if (rule.nodes) rule.replaceWith(...rule.nodes);
    else rule.remove();
  });
  root.walkRules((rule) => {
    if (rule.parent.type === "atrule" && /keyframes/.test(rule.parent.name))
      return;
    rule.selector = rule.selectors
      .map((selector) =>
        /:root|:host/.test(selector) ? ".af2" : `.af2 ${selector}`,
      )
      .join(", ");
  });
  fs.writeFileSync(
    path.join(moduleDir, "styles/module.css"),
    root.toString().replaceAll("--tw-", "--af2-tw-"),
  );
  let html = fs.readFileSync(standalone, "utf8");
  html = html.replace(/<style>\/\*! tailwindcss[\s\S]*?<\/style>/g, "");
  html = html.replace("</head>", `<style>${raw}</style></head>`);
  fs.writeFileSync(standalone, html);
} finally {
  fs.rmSync(temp, { recursive: true, force: true });
}
