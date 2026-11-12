import type { ReactNode } from "react";

interface BadgePanelProps {
  title?: string;
  icon?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  contentClassName?: string;
  ribbonVariant?: "gold" | "red" | "navy";
}

export function BadgePanel({
  title,
  icon,
  action,
  children,
  className = "",
  contentClassName = "",
}: BadgePanelProps) {
  return (
    <section className={`card flex flex-col overflow-hidden ${className}`}>
      {title && (
        <div className="flex items-center justify-between px-4 py-3 bg-elevation/60 border-b border-border-subtle">
          <div className="flex items-center gap-2">
            {icon && <span className="text-accent">{icon}</span>}
            <h3 className="font-display text-lg font-semibold text-text-primary">
              {title}
            </h3>
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      <div
        className={`p-4 flex-1 min-h-0 ${contentClassName}`}
        {...(contentClassName.includes("overflow") ? { tabIndex: 0, role: "region", "aria-label": title ?? "Conținut" } : {})}
      >
        {children}
      </div>
    </section>
  );
}
