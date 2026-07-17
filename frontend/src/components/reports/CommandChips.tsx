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
    <div className="report-chip-list" aria-label="Parámetros principales del comando">
      {chips.map(({ param, value }) => (
        <span className="report-chip command-chip" key={param} title={`--${param} ${value}`}>
          <span>--{param}</span> {value}
        </span>
      ))}
    </div>
  );
}
