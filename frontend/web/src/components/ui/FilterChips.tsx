import { cn } from "@/lib/utils";

export interface FilterChip<T extends string> {
  value: T;
  label: string;
}

export function FilterChips<T extends string>({
  items,
  value,
  onChange,
}: {
  items: FilterChip<T>[];
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <div className="flex gap-2">
      {items.map((item) => (
        <button
          key={item.value}
          onClick={() => onChange(item.value)}
          className={cn(
            "rounded-full border px-3 py-1 text-xs font-semibold transition-colors",
            value === item.value
              ? "border-primary bg-primary text-primary-foreground"
              : "border-border bg-card text-muted-foreground shadow-control hover:border-brand/50 hover:bg-accent"
          )}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
