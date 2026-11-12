export type WorkflowTab =
  | "FULL FIELD REVIEW"
  | "SPECIMEN QUALITY"
  | "ANALYSIS AREA"
  | "REVIEW CELLS"
  | "REPORT";

export type ViewLayoutMode = "split" | "grid" | "slide";

export type CaseStatus = "Reviewing" | "Flagged" | "Approved" | "Signed-off";

export type RulerMode = "NONE" | "LINE" | "CROSS" | "CIRCLE";

export interface PatientInfo {
  id: string;
  mrn: string;
  name: string;
  age: number;
  gender: "Male" | "Female" | "Other";
  sampleType: string;
  collectionDate: string;
  orderingPhysician: string;
  clinicalIndication: string;
  wbcCount: number; // x10^9/L
  rbcCount: number;
  plateletCount: number;
  hemoglobin: number;
}

export interface CellItem {
  id: number;
  category: string;
  name: string;
  confidence: number;
  abnormal: boolean;
  flagged?: boolean;
  x: number; // percentage on virtual slide (0 - 100)
  y: number; // percentage on virtual slide (0 - 100)
  imageUrl?: string;
  notes?: string;
  diameterUm?: number;
  chromatinPattern?: string;
  granules?: string;
}

export interface DifferentialCategory {
  name: string;
  count: number;
  percentage: number;
  seen: boolean;
  referenceRange?: string;
  abnormalCount?: number;
}

export interface ImageAdjustments {
  brightness: number; // 50 to 150 (default 100)
  contrast: number; // 50 to 150 (default 100)
  gamma: number; // 0.5 to 2.0 (default 1.0)
  saturation: number; // 50 to 150 (default 100)
  preset: 1 | 2 | 3 | "custom";
}

export interface ClinicalCase {
  id: string;
  displayId: string;
  patient: PatientInfo;
  status: CaseStatus;
  createdDate: string;
  scanSizeCm2: number;
  totalNucleatedCells: number;
  categories: DifferentialCategory[];
  additionalCategories: DifferentialCategory[];
  slideImage: string;
}
