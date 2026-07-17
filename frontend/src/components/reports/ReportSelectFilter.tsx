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
    <div className="report-filter-group">
      <label className="report-filter-label" htmlFor={id}>{label}</label>
      <select
        className="report-filter-select"
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
