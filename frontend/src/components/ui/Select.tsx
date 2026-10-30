import type { SelectHTMLAttributes } from "react";
const base = "w-full rounded-app border border-line bg-white px-3 py-2 text-sm focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20 disabled:bg-canvas-alt";
interface Props extends SelectHTMLAttributes<HTMLSelectElement> { label: string; error?: string; options: { value: string; label: string }[]; placeholder?: string; }
export function Select({ label, error, options, placeholder, id, ...rest }: Props) {
  const uid = id ?? label;
  return (
    <div className="space-y-1">
      <label htmlFor={uid} className="block text-sm font-medium">{label}</label>
      <select id={uid} className={`${base} ${error ? "border-danger" : ""}`} aria-invalid={!!error} {...rest}>
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
      {error && <p role="alert" className="text-xs text-danger">{error}</p>}
    </div>
  );
}
