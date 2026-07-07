import { Loader2 } from "lucide-react";
import type { ButtonHTMLAttributes } from "react";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  loading?: boolean;
  variant?: "primary" | "secondary";
  children: React.ReactNode;
}

export function LoadingButton({
  loading = false,
  variant = "primary",
  children,
  disabled,
  className = "",
  ...props
}: Props) {
  const base =
    variant === "primary" ? "refresh-btn" : "refresh-btn refresh-btn--secondary";
  return (
    <button
      type="button"
      className={`${base} ${className}`.trim()}
      disabled={disabled || loading}
      aria-busy={loading}
      {...props}
    >
      {loading ? (
        <>
          <Loader2 size={16} className="btn-spinner" aria-hidden />
          <span>Loading…</span>
        </>
      ) : (
        children
      )}
    </button>
  );
}
