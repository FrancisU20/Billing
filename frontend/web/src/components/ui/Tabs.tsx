import { cn } from "@/lib/utils";

export interface TabItem<T extends string> {
  id: T;
  label: string;
}

export function Tabs<T extends string>({
  items,
  active,
  onChange,
}: {
  items: TabItem<T>[];
  active: T;
  onChange: (tab: T) => void;
}) {
  return (
    <div className="flex gap-2 border-b border-border/80">
      {items.map((item) => (
        <button
          key={item.id}
          onClick={() => onChange(item.id)}
          className={cn(
            "border-b-2 px-4 py-3 text-sm font-semibold transition-colors",
            active === item.id
              ? "border-brand text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          )}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
