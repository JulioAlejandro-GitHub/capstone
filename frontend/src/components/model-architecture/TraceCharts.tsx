import type { CurveEvidence } from '../../types/scientificReport';
import { number } from './traceSteps';

/** Probability on a 0–1 track with the decision threshold: how far a cell fell from the other side. */
export function ScoreBar({ score, threshold, tone }: { score: number; threshold: number | null; tone: string }) {
  const clamp = (value: number) => Math.min(100, Math.max(0, value * 100));
  return <div className="mx-score" data-tone={tone} role="img"
    aria-label={`Probabilidad ${number(score, 3)}${threshold == null ? '' : `, umbral ${number(threshold, 3)}`}`}>
    <div className="mx-score-track"><span className="mx-score-fill" style={{ width: `${clamp(score)}%` }} />
      {threshold != null && <span className="mx-score-threshold" style={{ left: `${clamp(threshold)}%` }} />}</div>
    <div className="mx-score-scale" aria-hidden="true"><span>0</span>{threshold != null && <span style={{ left: `${clamp(threshold)}%` }}>umbral {number(threshold, 2)}</span>}<span>1</span></div>
  </div>;
}

type Series = { label: string; values: (number | null)[]; tone: 'current' | 'compare' };

/** Share of active values at every step, for one or two cells: where the signal of a cell fades or survives. */
export function StepProfile({ labels, series, index, onPick }: { labels: string[]; series: Series[]; index: number; onPick: (index: number) => void }) {
  const width = 640, height = 168, left = 40, right = 12, top = 12, bottom = 34;
  const x = (step: number) => left + (labels.length > 1 ? step * (width - left - right) / (labels.length - 1) : 0);
  const y = (value: number) => top + (1 - value) * (height - top - bottom);
  return <figure className="mx-profile">
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Valores activos por paso">
      {[0, 0.5, 1].map(tick => <g key={tick}><line className="mx-grid" x1={left} x2={width - right} y1={y(tick)} y2={y(tick)} />
        <text className="mx-axis" x={left - 6} y={y(tick) + 4} textAnchor="end">{tick * 100} %</text></g>)}
      <rect className="mx-profile-focus" x={x(index) - 14} y={top - 4} width="28" height={height - top - bottom + 8} rx="4" />
      {labels.map((label, step) => <text key={label + step} className="mx-axis" x={x(step)} y={height - 12} textAnchor="middle">{label}</text>)}
      {series.map(item => {
        const points = item.values.map((value, step) => value == null ? null : `${x(step)},${y(value)}`).filter(Boolean).join(' ');
        return <g key={item.label} data-tone={item.tone} className="mx-profile-series"><polyline points={points} />
          {item.values.map((value, step) => value == null ? null : <circle key={step} cx={x(step)} cy={y(value)} r={step === index ? 5 : 3.5} />)}</g>;
      })}
      {labels.map((label, step) => <rect key={`hit-${label}-${step}`} className="mx-hit" x={x(step) - 16} y={0} width="32" height={height} onClick={() => onPick(step)}>
        <title>{label}</title></rect>)}
    </svg>
    <figcaption>{series.map(item => <span key={item.label} data-tone={item.tone}>{item.label}</span>)}</figcaption>
  </figure>;
}

/** Distribution of a dense vector: a ReLU layer piles values at zero and spreads the few active ones. */
export function VectorHistogram({ histogram }: { histogram: { counts: number[]; edges: number[] } }) {
  const width = 520, height = 150, bottom = 26, peak = Math.max(1, ...histogram.counts), bar = width / histogram.counts.length;
  return <figure className="mx-histogram">
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Distribución de valores del vector">
      {histogram.counts.map((count, index) => {
        const h = count ? Math.max(2, (height - bottom - 6) * count / peak) : 0;
        return <rect key={index} x={index * bar + 1} y={height - bottom - h} width={bar - 2} height={h} rx="1.5"><title>{`${number(histogram.edges[index], 2)} – ${number(histogram.edges[index + 1], 2)}: ${count}`}</title></rect>;
      })}
      <text className="mx-axis" x="0" y={height - 8}>{number(histogram.edges[0], 2)}</text>
      <text className="mx-axis" x={width} y={height - 8} textAnchor="end">{number(histogram.edges.at(-1), 2)}</text>
    </svg>
    <figcaption>Cantidad de neuronas por rango de valor</figcaption>
  </figure>;
}

/** Loss of the TRAIN by epoch, with the epoch whose checkpoint processed the cell. */
export function MiniCurves({ curve }: { curve: CurveEvidence }) {
  const width = 360, height = 140, left = 8, right = 8, top = 10, bottom = 22;
  const keys = ['loss', 'val_loss'] as const;
  const values = curve.epochs.flatMap(epoch => keys.map(key => epoch.values[key]).filter((value): value is number => value != null));
  if (!curve.epochs.length || !values.length) return <p className="scc-meta">El TRAIN no registró curvas de pérdida.</p>;
  const first = curve.epochs[0].epoch, last = curve.epochs.at(-1)!.epoch, low = Math.min(...values), high = Math.max(...values);
  const x = (epoch: number) => left + (last > first ? (epoch - first) / (last - first) : 0.5) * (width - left - right);
  const y = (value: number) => top + (high > low ? 1 - (value - low) / (high - low) : 0.5) * (height - top - bottom);
  const selected = curve.checkpoint.selected_epoch;
  return <figure className="mx-curves">
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Pérdida TRAIN y VAL por época">
      {selected != null && <g className="mx-curves-checkpoint"><line x1={x(selected)} x2={x(selected)} y1={top} y2={height - bottom} />
        <text x={x(selected)} y={height - 6} textAnchor="middle">checkpoint · época {selected}</text></g>}
      {keys.map(key => <polyline key={key} data-series={key} points={curve.epochs.filter(epoch => epoch.values[key] != null).map(epoch => `${x(epoch.epoch)},${y(epoch.values[key])}`).join(' ')} />)}
    </svg>
    <figcaption><span data-series="loss">TRAIN</span><span data-series="val_loss">VAL</span> · pérdida por época</figcaption>
  </figure>;
}
