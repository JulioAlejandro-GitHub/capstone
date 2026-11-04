import { useState } from "react";
import type {
  ViewLayoutMode,
  ClinicalCase,
  CellItem,
  ImageAdjustments,
} from "../types/visor";
import { mockCases, initialCellsData } from "../data/mockData";
import { calculateDifferential, reclassifyCell } from "../utils/hematology";
export function useFrotisDemo() {
  const [layoutMode, setLayoutMode] = useState<ViewLayoutMode>("split");

  // Clinical Case
  const [activeCase, setActiveCase] = useState<ClinicalCase>(mockCases[0]);
  const [cells, setCells] = useState<CellItem[]>(initialCellsData);

  // Selected Category & Cell
  const [selectedCategory, setSelectedCategory] =
    useState<string>("Promyelocyte");
  const [selectedCellId, setSelectedCellId] = useState<number | null>(295);

  // Inspected Cell (for Modal)
  const [inspectedCell, setInspectedCell] = useState<CellItem | null>(null);

  // Modals & Drawers
  const [isNotesOpen, setIsNotesOpen] = useState(false);
  const [isExportOpen, setIsExportOpen] = useState(false);
  const [isStandaloneHtmlOpen, setIsStandaloneHtmlOpen] = useState(false);

  // Staining & Image Filter Adjustments
  const [imageAdjustments, setImageAdjustments] = useState<ImageAdjustments>({
    brightness: 100,
    contrast: 100,
    gamma: 1.0,
    saturation: 100,
    preset: 1,
  });

  // Cell Reclassification Handler
  const handleReclassify = (cellId: number, newCategory: string) => {
    // 1. Update cells collection
    const updatedCells = reclassifyCell(cells, cellId, newCategory);
    setCells(updatedCells);

    // 2. Update category counts in activeCase
    const oldCell = cells.find((c) => c.id === cellId);
    if (!oldCell) return;

    const oldCategory = oldCell.category;
    if (oldCategory === newCategory) return;

    const updatedCategories = activeCase.categories.map((cat) => {
      if (cat.name === oldCategory) {
        return { ...cat, count: Math.max(0, cat.count - 1), abnormalCount: Math.max(0, (cat.abnormalCount ?? 0) - (oldCell.abnormal ? 1 : 0)) };
      }
      if (cat.name === newCategory) {
        return { ...cat, count: cat.count + 1, abnormalCount: (cat.abnormalCount ?? 0) + (oldCell.abnormal ? 1 : 0) };
      }
      return cat;
    });

    // Recompute exact percentages
    const countsMap: Record<string, number> = {};
    updatedCategories.forEach((c) => {
      countsMap[c.name] = c.count;
    });

    const stats = calculateDifferential(countsMap);
    const finalCategories = updatedCategories.map((c) => ({
      ...c,
      percentage: stats.percentages[c.name] || 0,
      seen: c.count > 0,
    }));

    setActiveCase({
      ...activeCase,
      categories: finalCategories,
    });

    // If inspected in modal, update state
    if (inspectedCell && inspectedCell.id === cellId) {
      setInspectedCell({
        ...inspectedCell,
        category: newCategory,
        name: newCategory,
      });
    }
  };

  // Toggle cell flagged status
  const handleToggleFlag = (cellId: number) => {
    setCells((prev) =>
      prev.map((c) => (c.id === cellId ? { ...c, flagged: !c.flagged } : c)),
    );
    if (inspectedCell && inspectedCell.id === cellId) {
      setInspectedCell((prev) =>
        prev ? { ...prev, flagged: !prev.flagged } : null,
      );
    }
  };

  // Available categories list for dropdowns
  const availableCategoryNames = activeCase.categories.map((c) => c.name);

  // Selected cell object
  const currentCell = cells.find((c) => c.id === selectedCellId) || cells[0];

  // Selected category differential stats
  const activeCategoryStats = activeCase.categories.find(
    (c) => c.name === selectedCategory,
  );

  return {
    layoutMode,
    setLayoutMode,
    activeCase,
    setActiveCase,
    cells,
    setCells,
    selectedCategory,
    setSelectedCategory,
    selectedCellId,
    setSelectedCellId,
    inspectedCell,
    setInspectedCell,
    isNotesOpen,
    setIsNotesOpen,
    isExportOpen,
    setIsExportOpen,
    isStandaloneHtmlOpen,
    setIsStandaloneHtmlOpen,
    imageAdjustments,
    setImageAdjustments,
    handleReclassify,
    handleToggleFlag,
    availableCategoryNames,
    activeCategoryStats,
  };
}
