import { useState } from "react";
import { Sun, Moon, Monitor } from "lucide-react";

type Pref = "system" | "light" | "dark";
const ORDER: Pref[] = ["system", "light", "dark"];
const LABEL: Record<Pref, string> = { system: "Temă: sistem", light: "Temă: luminoasă", dark: "Temă: întunecată" };

function read(): Pref {
  try {
    const v = localStorage.getItem("rs-theme");
    return v === "light" || v === "dark" ? v : "system";
  } catch {
    return "system";
  }
}

function apply(p: Pref) {
  const el = document.documentElement;
  if (p === "system") el.removeAttribute("data-theme");
  else el.setAttribute("data-theme", p);
  try {
    if (p === "system") localStorage.removeItem("rs-theme");
    else localStorage.setItem("rs-theme", p);
  } catch {
    /* storage blocked: preference lasts for this session only */
  }
}

export function ThemeToggle() {
  const [pref, setPref] = useState<Pref>(read);
  const Icon = pref === "light" ? Sun : pref === "dark" ? Moon : Monitor;
  return (
    <button
      type="button"
      aria-label={`${LABEL[pref]} (apasă pentru a schimba)`}
      title={LABEL[pref]}
      onClick={() => {
        const next = ORDER[(ORDER.indexOf(pref) + 1) % ORDER.length];
        apply(next);
        setPref(next);
      }}
      className="inline-flex items-center justify-center w-9 h-9 rounded-md text-text-secondary hover:text-text-primary hover:bg-elevation cursor-pointer"
    >
      <Icon size={18} aria-hidden="true" />
    </button>
  );
}
