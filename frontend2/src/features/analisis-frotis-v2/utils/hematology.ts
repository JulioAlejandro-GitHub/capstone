import type { CellItem } from "../types/visor";
export type { CellItem } from "../types/visor";

export interface DifferentialStats {
  totalCount: number;
  percentages: Record<string, number>;
  totalAbnormalCount: number;
  abnormalPercentage: number;
}

/**
 * Calculates differential leukocyte counts and percentage breakdowns.
 */
export function calculateDifferential(
  cellCounts: Record<string, number>,
  abnormalCounts: Record<string, number> = {},
): DifferentialStats {
  let totalCount = 0;
  let totalAbnormal = 0;

  for (const count of Object.values(cellCounts)) {
    totalCount += count;
  }

  for (const count of Object.values(abnormalCounts)) {
    totalAbnormal += count;
  }

  const percentages: Record<string, number> = {};
  for (const [name, count] of Object.entries(cellCounts)) {
    percentages[name] =
      totalCount > 0 ? Number(((count / totalCount) * 100).toFixed(1)) : 0;
  }

  const abnormalPercentage =
    totalCount > 0
      ? Number(((totalAbnormal / totalCount) * 100).toFixed(1))
      : 0;

  return {
    totalCount,
    percentages,
    totalAbnormalCount: totalAbnormal,
    abnormalPercentage,
  };
}

/**
 * Reclassifies a cell to a new category, updating category statistics.
 */
export function reclassifyCell(
  cells: CellItem[],
  cellId: number,
  newCategory: string,
): CellItem[] {
  return cells.map((cell) => {
    if (cell.id === cellId) {
      return {
        ...cell,
        category: newCategory,
        name: newCategory,
      };
    }
    return cell;
  });
}

/**
 * Computes realistic microscopic scale bar size and label given a zoom factor.
 */
export function calculateScaleBar(zoomLevel: number): {
  widthPx: number;
  label: string;
} {
  // At zoom 1x, 100px represents 1 mm (1000 µm)
  // At zoom 20x, 100px represents 50 µm
  // At zoom 100x, 100px represents 10 µm
  if (zoomLevel <= 1.5) {
    return { widthPx: Math.round(120 * zoomLevel), label: "1 mm" };
  } else if (zoomLevel <= 5) {
    return { widthPx: Math.round(100 * (zoomLevel / 3)), label: "200 µm" };
  } else if (zoomLevel <= 15) {
    return { widthPx: Math.round(90 * (zoomLevel / 10)), label: "100 µm" };
  } else if (zoomLevel <= 40) {
    return { widthPx: Math.round(110 * (zoomLevel / 25)), label: "50 µm" };
  } else {
    return { widthPx: Math.round(100 * (zoomLevel / 70)), label: "10 µm" };
  }
}

/**
 * Filter cells based on active category, search string, or flagged status.
 */
export function filterCells(
  cells: CellItem[],
  categoryFilter: string,
  searchQuery: string = "",
  flaggedOnly: boolean = false,
): CellItem[] {
  return cells.filter((c) => {
    const matchesCategory =
      categoryFilter === "All" ||
      c.category.toLowerCase() === categoryFilter.toLowerCase();
    const matchesSearch =
      !searchQuery ||
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.id.toString().includes(searchQuery);
    const matchesFlag = !flaggedOnly || !!c.flagged;
    return matchesCategory && matchesSearch && matchesFlag;
  });
}
