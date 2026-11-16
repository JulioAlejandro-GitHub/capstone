/**
 * Geometría del visor de v3. Módulo puro.
 *
 * El estado guarda el punto de la imagen que se observa (`cx`, `cy`, en píxeles
 * de la imagen original), no un desplazamiento de pantalla: así el centro de
 * observación se conserva cuando cambia el tamaño del viewport.
 * `scale` es zoom digital (píxeles de pantalla por píxel de imagen); no
 * representa aumento óptico.
 */
export type Size = { width: number; height: number };
export type Point = { x: number; y: number };
export type ViewportState = { cx: number; cy: number; scale: number; rotation: number };

const radians = (degrees: number) => (degrees * Math.PI) / 180;
const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

export const normalizeRotation = (degrees: number) => ((degrees % 360) + 360) % 360;

/** Escala con la que la imagen completa, rotada, cabe en el viewport. */
export function fitScale(image: Size, stage: Size, rotation = 0): number {
  if (!image.width || !image.height || !stage.width || !stage.height) return 1;
  const cos = Math.abs(Math.cos(radians(rotation)));
  const sin = Math.abs(Math.sin(radians(rotation)));
  const boundsWidth = image.width * cos + image.height * sin;
  const boundsHeight = image.width * sin + image.height * cos;
  return Math.min(stage.width / boundsWidth, stage.height / boundsHeight);
}

export function fitViewport(image: Size, stage: Size, rotation = 0): ViewportState {
  return {
    cx: image.width / 2,
    cy: image.height / 2,
    scale: fitScale(image, stage, rotation),
    rotation: normalizeRotation(rotation),
  };
}

export function scaleLimits(image: Size, stage: Size, rotation = 0) {
  const fit = fitScale(image, stage, rotation);
  return { min: Math.min(fit, 1) * 0.5, max: Math.max(8, fit * 4) };
}

export function imageToScreen(point: Point, viewport: ViewportState, stage: Size): Point {
  const angle = radians(viewport.rotation);
  const dx = (point.x - viewport.cx) * viewport.scale;
  const dy = (point.y - viewport.cy) * viewport.scale;
  return {
    x: stage.width / 2 + dx * Math.cos(angle) - dy * Math.sin(angle),
    y: stage.height / 2 + dx * Math.sin(angle) + dy * Math.cos(angle),
  };
}

export function screenToImage(point: Point, viewport: ViewportState, stage: Size): Point {
  const angle = radians(-viewport.rotation);
  const dx = point.x - stage.width / 2;
  const dy = point.y - stage.height / 2;
  return {
    x: viewport.cx + (dx * Math.cos(angle) - dy * Math.sin(angle)) / viewport.scale,
    y: viewport.cy + (dx * Math.sin(angle) + dy * Math.cos(angle)) / viewport.scale,
  };
}

const withCenter = (viewport: ViewportState, center: Point, image: Size): ViewportState => ({
  ...viewport,
  cx: clamp(center.x, 0, image.width),
  cy: clamp(center.y, 0, image.height),
});

/** Zoom que mantiene fijo el punto de la imagen situado bajo `anchor` (coordenadas de pantalla). */
export function zoomAt(
  viewport: ViewportState,
  factor: number,
  anchor: Point,
  image: Size,
  stage: Size,
): ViewportState {
  const limits = scaleLimits(image, stage, viewport.rotation);
  const scale = clamp(viewport.scale * factor, limits.min, limits.max);
  const fixed = screenToImage(anchor, viewport, stage);
  const moved = screenToImage(anchor, { ...viewport, scale }, stage);
  return withCenter(
    { ...viewport, scale },
    { x: viewport.cx + fixed.x - moved.x, y: viewport.cy + fixed.y - moved.y },
    image,
  );
}

export function setScale(viewport: ViewportState, scale: number, image: Size, stage: Size) {
  return zoomAt(viewport, scale / viewport.scale, { x: stage.width / 2, y: stage.height / 2 }, image, stage);
}

/** Desplaza la observación `dx`,`dy` píxeles de pantalla (arrastre). */
export function panBy(viewport: ViewportState, dx: number, dy: number, image: Size): ViewportState {
  const angle = radians(-viewport.rotation);
  return withCenter(viewport, {
    x: viewport.cx - (dx * Math.cos(angle) - dy * Math.sin(angle)) / viewport.scale,
    y: viewport.cy - (dx * Math.sin(angle) + dy * Math.cos(angle)) / viewport.scale,
  }, image);
}

export function rotateBy(viewport: ViewportState, delta: number): ViewportState {
  return { ...viewport, rotation: normalizeRotation(viewport.rotation + delta) };
}

export function centerOn(viewport: ViewportState, point: Point, image: Size): ViewportState {
  return withCenter(viewport, point, image);
}

/** Región de interés: la centra y, si hace falta, acerca hasta que sea legible. */
export function focusRegion(
  viewport: ViewportState,
  region: { x: number; y: number; width: number; height: number },
  image: Size,
  stage: Size,
  minScreenSize = 96,
): ViewportState {
  const limits = scaleLimits(image, stage, viewport.rotation);
  const needed = minScreenSize / Math.max(region.width, region.height, 1);
  const scale = clamp(Math.max(viewport.scale, needed), limits.min, limits.max);
  return withCenter(
    { ...viewport, scale },
    { x: region.x + region.width / 2, y: region.y + region.height / 2 },
    image,
  );
}

/** Esquinas, en coordenadas de imagen, del área visible (para el minimapa). */
export function visibleQuad(viewport: ViewportState, stage: Size): Point[] {
  return [
    { x: 0, y: 0 },
    { x: stage.width, y: 0 },
    { x: stage.width, y: stage.height },
    { x: 0, y: stage.height },
  ].map((corner) => screenToImage(corner, viewport, stage));
}
