// EXPLAIN `map` artifacts are NumPy float32 arrays at the model input resolution (200×200).
// Grad-CAM is a non-negative activation; LIME and SHAP are signed attributions toward the explained class.

export interface AttributionMap { width: number; height: number; values: Float32Array }

export function parseNpy(buffer: ArrayBuffer): AttributionMap {
  const bytes = new Uint8Array(buffer);
  if (String.fromCharCode(...bytes.slice(1, 6)) !== 'NUMPY' || bytes[0] !== 0x93) throw new Error('El mapa no es un archivo NumPy.');
  const major = bytes[6];
  const view = new DataView(buffer);
  const headerLength = major === 1 ? view.getUint16(8, true) : view.getUint32(8, true);
  const start = major === 1 ? 10 : 12;
  const header = Array.from(bytes.slice(start, start + headerLength), byte => String.fromCharCode(byte)).join('');
  const descr = /'descr':\s*'([^']+)'/.exec(header)?.[1];
  const fortran = /'fortran_order':\s*(True|False)/.exec(header)?.[1];
  const shape = /'shape':\s*\(([^)]*)\)/.exec(header)?.[1].split(',').map(item => item.trim()).filter(Boolean).map(Number);
  if (!descr || !shape || shape.length !== 2 || fortran !== 'False') throw new Error('Mapa NumPy no compatible: se espera una matriz 2D en orden C.');
  const [height, width] = shape;
  const offset = start + headerLength;
  const count = width * height;
  let values: Float32Array;
  if (descr === '<f4') values = new Float32Array(buffer.slice(offset, offset + count * 4));
  else if (descr === '<f8') values = Float32Array.from(new Float64Array(buffer.slice(offset, offset + count * 8)));
  else throw new Error(`Tipo NumPy no compatible: ${descr}.`);
  if (values.length !== count) throw new Error('El mapa NumPy está incompleto.');
  return { width, height, values };
}

// Perceptual blue → cyan → green → yellow → red ramp (turbo-like), t in [0, 1].
const ramp: [number, number, number][] = [[48, 18, 59], [40, 120, 230], [30, 200, 200], [120, 230, 80], [250, 200, 40], [220, 50, 20]];
export function activationColor(t: number): [number, number, number] {
  const x = Math.max(0, Math.min(1, t)) * (ramp.length - 1);
  const i = Math.min(ramp.length - 2, Math.floor(x));
  const f = x - i;
  return [0, 1, 2].map(c => Math.round(ramp[i][c] + (ramp[i + 1][c] - ramp[i][c]) * f)) as [number, number, number];
}

/**
 * RGBA pixels for one layer. Alpha follows the attribution magnitude, so neutral regions stay transparent and
 * the cell remains visible; the layer opacity slider scales it further.
 * Grad-CAM: activation ramp, normalized by its maximum. LIME/SHAP: red supports the explained class, blue opposes
 * it, normalized by the largest absolute value of that map (scales are not comparable across methods).
 */
export function attributionPixels(map: AttributionMap, signed: boolean): Uint8ClampedArray<ArrayBuffer> {
  const { values } = map;
  let scale = 0;
  for (const value of values) scale = Math.max(scale, signed ? Math.abs(value) : value);
  const pixels = new Uint8ClampedArray(new ArrayBuffer(values.length * 4));
  for (let i = 0; i < values.length; i++) {
    const value = scale > 0 ? values[i] / scale : 0;
    const magnitude = Math.min(1, Math.abs(value));
    const [r, g, b] = signed ? (value >= 0 ? [214, 39, 40] : [31, 119, 180]) : activationColor(Math.max(0, value));
    pixels[i * 4] = r; pixels[i * 4 + 1] = g; pixels[i * 4 + 2] = b;
    pixels[i * 4 + 3] = Math.round(255 * (signed ? magnitude : Math.max(0, value)));
  }
  return pixels;
}
