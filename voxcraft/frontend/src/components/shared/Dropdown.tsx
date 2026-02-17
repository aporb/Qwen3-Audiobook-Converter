import { clsx } from "clsx";
import type { SelectHTMLAttributes } from "react";

interface DropdownOption {
  value: string;
  label: string;
}

interface DropdownProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, "onChange"> {
  options: DropdownOption[] | readonly DropdownOption[];
  value: string;
  onChange: (value: string) => void;
  label?: string;
}

export function Dropdown({
  options,
  value,
  onChange,
  label,
  className,
  ...props
}: DropdownProps) {
  return (
    <div className={clsx("flex flex-col gap-1", className)}>
      {label && (
        <label className="text-xs text-text-secondary font-medium">
          {label}
        </label>
      )}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="bg-surface border border-glass-border rounded-lg px-3 py-2 text-sm text-text-primary appearance-none cursor-pointer hover:border-white/30 transition-colors"
        {...props}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}
