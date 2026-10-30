import type { InputHTMLAttributes, TextareaHTMLAttributes } from "react";
const base = "w-full rounded-app border border-line bg-white px-3 py-2 text-sm placeholder:text-muted transition-colors focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20 disabled:bg-canvas-alt disabled:text-muted-strong";
interface InputProps extends InputHTMLAttributes<HTMLInputElement> { label: string; error?: string; hint?: string; }
export function Input({ label, error, hint, id, className = "", ...rest }: InputProps) {
  const uid = id ?? label;
  return (
    <div className="space-y-1">
      <label htmlFor={uid} className="block text-sm font-medium">{label}</label>
      <input id={uid} className={`${base} ${error ? "border-danger focus:ring-danger/20" : ""} ${className}`} aria-describedby={error ? `${uid}-err` : hint ? `${uid}-hint` : undefined} aria-invalid={!!error} {...rest} />
      {hint && !error && <p id={`${uid}-hint`} className="text-xs text-muted-strong">{hint}</p>}
      {error && <p id={`${uid}-err`} role="alert" className="text-xs text-danger">{error}</p>}
    </div>
  );
}
interface TextAreaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> { label: string; error?: string; }
export function Textarea({ label, error, id, className = "", ...rest }: TextAreaProps) {
  const uid = id ?? label;
  return (
    <div className="space-y-1">
      <label htmlFor={uid} className="block text-sm font-medium">{label}</label>
      <textarea id={uid} rows={3} className={`${base} resize-y ${error ? "border-danger" : ""} ${className}`} aria-invalid={!!error} {...rest} />
      {error && <p role="alert" className="text-xs text-danger">{error}</p>}
    </div>
  );
}
