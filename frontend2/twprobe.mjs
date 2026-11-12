import postcss from 'postcss';
import tailwind from '@tailwindcss/postcss';

const candidates = [
  'wrap-anywhere', 'overflow-wrap-anywhere', 'whitespace-pre-wrap', 'tabular-nums', 'sticky',
  'border-b-3', 'border-b-0', 'border-t-3', 'border-l-4', 'border-b-transparent', 'border-b-current',
  'border-b-accent-2', 'border-t-ok', 'max-w-full', 'min-w-max', 'max-h-[70vh]', 'overflow-auto', 'overflow-x-auto',
  'grid', 'gap-2', 'rounded-pill', 'rounded-lg', 'rounded-md', 'rounded-sm', 'bg-surface', 'bg-subtle', 'bg-hover',
  'border-border', 'border-border-subtle', 'border-border-strong', 'text-fg', 'text-fg-muted', 'text-fg-strong',
  'text-value', 'bg-ok', 'text-ok', 'bg-warn', 'text-warn', 'bg-danger', 'text-danger', 'bg-blocked', 'text-blocked',
  'bg-neutral-soft', 'text-neutral-fg', 'bg-accent-soft', 'text-accent', 'text-accent-2', 'border-accent-2',
  'font-mono', 'text-xs', 'text-sm', 'text-lg', 'font-semibold', 'uppercase', 'tracking-[.03em]',
  'focus-visible:outline-3', 'focus-visible:outline-accent-2', 'focus-visible:outline-offset-2',
  'hover:bg-hover', 'cursor-pointer', 'cursor-help', 'inline-flex', 'items-center', 'justify-between',
  'flex-wrap', 'flex-col', 'text-right', 'text-start', 'items-start', 'line-height-[1.5]', 'leading-[1.5]',
  'border-inline-start-4', 'border-inline-start-accent', 'min-h-[38px]', 'min-h-[34px]', 'p-3', 'px-4', 'py-3',
  'grid-cols-[repeat(auto-fit,minmax(190px,1fr))]', 'w-2', 'h-2', 'rounded-full', 'bg-current', 'overflow-hidden',
  'display-none', 'hidden', 'position-relative', 'relative', 'overflow-wrap-anywhere', 'max-width-[640px]',
  'outline-[3px]', 'outline-[color:var(--color-accent-2)]', 'box-shadow-modal', 'shadow-modal', 'shadow-card',
  'font-inherit', 'border-0', 'text-[15px]', 'text-[13px]', 'text-[12px]', 'min-width-[460px]', 'border-bottom-width-3',
  'border-b-[3px]', 'border-left-[4px]', 'text-wrap-anywhere', 'overflow-clip', 'sr-only', 'dvh', 'h-[100dvh]',
  'grid-auto-flow', 'col-span-full', 'border-y-0', 'border-left-0', 'text-transform-none', 'letter-spacing-normal',
  'font-weight-normal', 'text-transform-uppercase', 'border-bottom-3', 'border-bottom-transparent',
];

const probe = `<div class="${candidates.join(' ')}"></div>`;
await import('node:fs').then(fs => fs.writeFileSync('./twprobe.html', probe));
const result = await postcss([tailwind({ sources: ['./twprobe.html'] })]).process('@import "tailwindcss";', { from: 'twprobe.css' });
const out = result.css;
for (const c of candidates) {
  const esc = c.replace(/([():\/,[\]])/g, '\\$1');
  console.log((out.includes('.' + esc) ? 'OK   ' : 'MISS ') + c);
}
