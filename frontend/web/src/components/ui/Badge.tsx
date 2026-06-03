import { cn } from "@/lib/utils";
import type { BadgeTone } from "@/lib/status-styles";

const tones: Record<BadgeTone, string> = {
  neutral: "border-muted bg-muted text-muted-foreground",
  info: "border-info bg-info text-info-foreground",
  success: "border-success bg-success text-success-foreground",
  warning: "border-warning bg-warning text-warning-foreground",
  danger: "border-danger bg-danger text-danger-foreground",
  accent: "border-accent-strong bg-accent-strong text-accent-strong-foreground",
};

export function Badge({
  tone = "neutral",
  className,
  children,
}: {
  tone?: BadgeTone;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <span className={cn("inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold", tones[tone], className)}>
      {children}
    </span>
  );
}
