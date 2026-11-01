import type { ArchitectureBlock, ArchitectureFamily, ArchitectureShape } from '../../types/modelArchitecture';

export const architectureViews = {
  mapas: 'Mapas apilados', 'bloques-3d': 'Bloques 3D', bloques: 'Bloques', grafo: 'Grafo denso', conexiones: 'Conexiones',
  flujo: 'Flujo', vit: 'Bloques ViT', tabla: 'Tabla',
} as const;
export type ArchitectureView = keyof typeof architectureViews;

// The first view of each family is its default; every view draws the same response.
const familyViews: Record<ArchitectureFamily, ArchitectureView[]> = {
  custom_cnn: ['mapas', 'bloques', 'tabla'],
  vgg16: ['bloques-3d', 'mapas', 'tabla'],
  densenet121: ['grafo', 'conexiones', 'tabla'],
  biomedclip: ['flujo', 'vit', 'tabla'],
  generic: ['tabla'],
};
export const viewsFor = (family: ArchitectureFamily) => familyViews[family];
export const resolveView = (family: ArchitectureFamily, requested: string | null): ArchitectureView => {
  const views = viewsFor(family);
  return views.find(view => view === requested) ?? views[0];
};

export const phaseLabels: Record<string, string> = { base: 'Fase base', fine_tuning: 'Ajuste fino' };
export const isTrained = (block: ArchitectureBlock, phase: string) => block.trainable_phases.includes(phase);
export const shapeText = (shape: ArchitectureShape) => shape?.slice(1).join(' × ') ?? 'Sin evidencia';
export const countText = (value: number | null | undefined) => value == null ? 'Sin evidencia' : value.toLocaleString('es-CL');
export const isSpatial = (shape: ArchitectureShape) => (shape?.length ?? 0) === 4;

// 200 to 6 px cannot share a linear scale: size is logarithmic and the label always carries the real value.
export const spatialSize = (shape: ArchitectureShape) => 44 + 15 * Math.log2(Math.max(2, shape?.[1] ?? 2));
export const depthSize = (shape: ArchitectureShape) => 10 + 3.2 * Math.log2(Math.max(2, shape?.at(-1) ?? 2));
