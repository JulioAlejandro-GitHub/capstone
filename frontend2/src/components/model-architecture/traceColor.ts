// Cividis: perceptually uniform and readable with colour-vision deficiencies; dark = low activation, yellow = high.
const STOPS = ['#00224e', '#123570', '#3b496c', '#575d6d', '#707173', '#8a8678', '#a69d75', '#c4b56c', '#fee838']
  .map(hex => [1, 3, 5].map(offset => parseInt(hex.slice(offset, offset + 2), 16)));

export const CIVIDIS_GRADIENT = `linear-gradient(90deg, ${STOPS.map(([r, g, b], index) => `rgb(${r} ${g} ${b}) ${(index / (STOPS.length - 1)) * 100}%`).join(', ')})`;

export function cividis(value: number): [number, number, number] {
  const t = Math.min(1, Math.max(0, Number.isFinite(value) ? value : 0)) * (STOPS.length - 1);
  const low = Math.floor(t), high = Math.min(STOPS.length - 1, low + 1), mix = t - low;
  return [0, 1, 2].map(channel => Math.round(STOPS[low][channel] + (STOPS[high][channel] - STOPS[low][channel]) * mix)) as [number, number, number];
}

export type MapScale = 'layer' | 'channel';

const images = new Map<string, Promise<HTMLImageElement>>();
function load(png: string) {
  let image = images.get(png);
  if (!image) {
    image = new Promise((resolve, reject) => {
      const element = new Image();
      element.onload = () => resolve(element);
      element.onerror = reject;
      element.src = `data:image/png;base64,${png}`;
    });
    if (images.size > 400) images.clear();
    images.set(png, image);
  }
  return image;
}

/**
 * Paints one stored channel. The PNG keeps 0–255 inside the channel's own [min, max]; with that range the raw value is
 * rebuilt and redrawn either on its own scale or on the layer's, so channels can be compared honestly.
 */
export async function paintMap(canvas: HTMLCanvasElement, png: string, range: { min?: number; max?: number }, layer: { min: number; max: number }, scale: MapScale) {
  const image = await load(png);
  canvas.width = image.naturalWidth; canvas.height = image.naturalHeight;
  const context = canvas.getContext('2d', { willReadFrequently: true });
  if (!context) return;
  context.drawImage(image, 0, 0);
  const pixels = context.getImageData(0, 0, canvas.width, canvas.height);
  const shared = scale === 'layer' && range.min != null && range.max != null && layer.max > layer.min;
  for (let index = 0; index < pixels.data.length; index += 4) {
    const gray = pixels.data[index] / 255;
    const value = shared ? (range.min! + gray * (range.max! - range.min!) - layer.min) / (layer.max - layer.min) : gray;
    const [r, g, b] = cividis(value);
    pixels.data[index] = r; pixels.data[index + 1] = g; pixels.data[index + 2] = b; pixels.data[index + 3] = 255;
  }
  context.putImageData(pixels, 0, 0);
}
