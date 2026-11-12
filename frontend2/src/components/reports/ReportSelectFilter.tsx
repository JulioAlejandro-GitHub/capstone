export interface ReportFilterOption {
  label: string;
  value: string;
}

interface ReportSelectFilterProps {
  allLabel: string;
  disabled?: boolean;
  id: string;
  label: string;
  onChange: (value: string) => void;
  options: readonly ReportFilterOption[];
  value: string;
}

export function ReportSelectFilter({
  allLabel,
  disabled = false,
  id,
  label,
  onChange,
  options,
  value,
}: ReportSelectFilterProps) {
  return (
    <div className="grid min-w-0 gap-1.25">
      <label className="text-[11px] font-extrabold uppercase tracking-[0.04em] text-[#52617e]" htmlFor={id}>{label}</label>
      <select
        className="w-full min-h-[38px] rounded-lg border border-border-strong bg-surface px-2.5 py-1.75 pr-8 text-xs text-ink disabled:bg-[#f2f4f8] disabled:text-muted-2 disabled:cursor-not-allowed focus-visible:outline-3 focus-visible:outline-[rgba(49,92,170,0.24)] focus-visible:outline-offset-2"
        disabled={disabled}
        id={id}
        onChange={(event) => onChange(event.target.value)}
        value={value}
      >
        <option value="">{allLabel}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>{option.label}</option>
        ))}
      </select>
    </div>
  );
}
