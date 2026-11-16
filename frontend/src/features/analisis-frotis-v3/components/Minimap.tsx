import type { MouseEvent } from 'react';

import type { Point, Size } from '../state/viewportMath';

/** Minimapa: imagen completa y región visible. Un clic centra la observación. */
export function Minimap({
  url,
  image,
  quad,
  onCenter,
}: {
  url: string;
  image: Size;
  quad: Point[];
  onCenter: (point: Point) => void;
}) {
  const center = (event: MouseEvent<SVGSVGElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    onCenter({
      x: ((event.clientX - bounds.left) / bounds.width) * image.width,
      y: ((event.clientY - bounds.top) / bounds.height) * image.height,
    });
  };
  return (
    <svg
      className="frotis-v3-minimap"
      viewBox={`0 0 ${image.width} ${image.height}`}
      role="img"
      aria-label="Minimapa del frotis con la región visible"
      onClick={center}
    >
      <image href={url} width={image.width} height={image.height} />
      <polygon points={quad.map((point) => `${point.x},${point.y}`).join(' ')} />
    </svg>
  );
}
