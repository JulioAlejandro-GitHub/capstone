import type { WorkflowTab } from "./types/visor";
export const frotis2Base = "/frotis/analisis-2";
export const workflowRoutes: { path: string; tab: WorkflowTab }[] = [
  { path: "full-field-review", tab: "FULL FIELD REVIEW" },
  { path: "specimen-quality", tab: "SPECIMEN QUALITY" },
  { path: "analysis-area", tab: "ANALYSIS AREA" },
  { path: "review-cells", tab: "REVIEW CELLS" },
  { path: "report", tab: "REPORT" },
];
