import { extractCommandParam } from '../../utils/runReport';

const REPORT_COMMAND_PARAMS = [
  'model',
  'max-epochs',
  'optimizer',
  'checkpoint-monitor',
] as const;

interface CommandChipsProps {
  command: string | null | undefined;
  params?: readonly string[];
}

export function CommandChips({ command, params = REPORT_COMMAND_PARAMS }: CommandChipsProps) {
  const chips = params.flatMap((param) => {
    const value = extractCommandParam(command, param);
    return value ? [{ param, value }] : [];
  });

  if (chips.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-[5px]" aria-label="Parámetros principales del comando">
      {chips.map(({ param, value }) => (
        <span className="inline-flex max-w-full items-baseline gap-1 py-1 px-1.5 rounded-md border border-[#dce4f2] bg-[#f4f7fc] text-[#40506e] font-mono text-[10px] leading-[1.25] wrap-anywhere" key={param} title={`--${param} ${value}`}>
          <span className="text-accent-2 font-extrabold">--{param}</span> {value}
        </span>
      ))}
    </div>
  );
}
