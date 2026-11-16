/**
 * Layout Manager de instrumentos flotantes. Módulo puro.
 *
 * Calcula posiciones seguras dentro del stage en lugar de apilar con z-index:
 * los paneles fijos de la vista activa (`reserved`) tienen prioridad y los
 * instrumentos móviles se desplazan, se reparten el alto o pasan a franja.
 */
export type FloatingRequest = {
  id: string;
  side: 'left' | 'right';
  anchor?: 'top' | 'bottom';
  width: number;
  /** Alto natural medido del contenido. */
  height: number;
};

export type FloatingPlacement = {
  id: string;
  x: number;
  y: number;
  width: number;
  /** Alto máximo asignado; el contenido hace scroll si lo supera. */
  maxHeight: number;
  mode: 'floating' | 'sheet';
};

export type FloatingLayoutInput = {
  stage: { width: number; height: number };
  /** Zonas ocupadas por paneles fijos de la vista activa (inspector, etc.). */
  reserved?: { top?: number; right?: number; bottom?: number; left?: number };
  panels: FloatingRequest[];
  margin?: number;
  gap?: number;
  /** Por debajo de este ancho útil los instrumentos pasan a franjas de ancho completo. */
  compactBelow?: number;
};

const MIN_PANEL_HEIGHT = 72;

function stackColumn(
  panels: FloatingRequest[],
  x: (panel: FloatingRequest) => number,
  width: (panel: FloatingRequest) => number,
  top: number,
  available: number,
  gap: number,
  mode: FloatingPlacement['mode'],
): FloatingPlacement[] {
  if (!panels.length) return [];
  const gaps = gap * (panels.length - 1);
  const natural = panels.reduce((total, panel) => total + panel.height, 0);
  const room = Math.max(0, available - gaps);
  // Si no caben a su alto natural, se reparte el alto disponible sin superponer:
  // los paneles pequeños conservan su alto y el resto comparte lo que queda.
  const heights = panels.map((panel) => panel.height);
  if (natural > room) {
    const pending = new Set(panels.map((_, index) => index));
    let remaining = room;
    for (;;) {
      const share = remaining / pending.size;
      const fitting = [...pending].filter((index) => panels[index].height <= share);
      if (!fitting.length) {
        pending.forEach((index) => { heights[index] = Math.max(MIN_PANEL_HEIGHT, share); });
        break;
      }
      fitting.forEach((index) => {
        pending.delete(index);
        remaining -= panels[index].height;
      });
      if (!pending.size) break;
    }
  }
  const topOnes = panels.map((panel, index) => ({ panel, index })).filter(({ panel }) => panel.anchor !== 'bottom');
  const bottomOnes = panels.map((panel, index) => ({ panel, index })).filter(({ panel }) => panel.anchor === 'bottom');
  const placements: FloatingPlacement[] = [];
  let cursor = top;
  for (const { panel, index } of topOnes) {
    placements.push({ id: panel.id, x: x(panel), y: cursor, width: width(panel), maxHeight: heights[index], mode });
    cursor += heights[index] + gap;
  }
  let floor = top + available;
  for (const { panel, index } of [...bottomOnes].reverse()) {
    const y = Math.max(cursor, floor - heights[index]);
    placements.push({ id: panel.id, x: x(panel), y, width: width(panel), maxHeight: heights[index], mode });
    floor = y - gap;
  }
  return placements;
}

export function computeFloatingLayout(input: FloatingLayoutInput): FloatingPlacement[] {
  const { stage, panels } = input;
  const margin = input.margin ?? 12;
  const gap = input.gap ?? 8;
  const reserved = { top: 0, right: 0, bottom: 0, left: 0, ...input.reserved };
  const left = reserved.left + margin;
  const right = stage.width - reserved.right - margin;
  const top = reserved.top + margin;
  const safeWidth = Math.max(0, right - left);
  const safeHeight = Math.max(0, stage.height - reserved.bottom - margin - top);
  if (!panels.length) return [];

  if (safeWidth < (input.compactBelow ?? 420)) {
    return stackColumn(
      panels.map((panel) => ({ ...panel, anchor: 'top' as const })),
      () => left,
      () => safeWidth,
      top,
      safeHeight,
      gap,
      'sheet',
    );
  }

  let leftColumn = panels.filter((panel) => panel.side === 'left');
  let rightColumn = panels.filter((panel) => panel.side === 'right');
  const widest = (column: FloatingRequest[]) => column.reduce((value, panel) => Math.max(value, panel.width), 0);
  // Sin sitio para dos columnas, los instrumentos de la derecha se integran en la izquierda.
  if (leftColumn.length && rightColumn.length && widest(leftColumn) + widest(rightColumn) + gap > safeWidth) {
    leftColumn = [...leftColumn, ...rightColumn];
    rightColumn = [];
  }
  const fit = (panel: FloatingRequest) => Math.min(panel.width, safeWidth);
  return [
    ...stackColumn(leftColumn, () => left, fit, top, safeHeight, gap, 'floating'),
    ...stackColumn(rightColumn, (panel) => right - fit(panel), fit, top, safeHeight, gap, 'floating'),
  ];
}

export const placementsOverlap = (first: FloatingPlacement, second: FloatingPlacement) => (
  first.x < second.x + second.width
  && second.x < first.x + first.width
  && first.y < second.y + second.maxHeight
  && second.y < first.y + first.maxHeight
);
