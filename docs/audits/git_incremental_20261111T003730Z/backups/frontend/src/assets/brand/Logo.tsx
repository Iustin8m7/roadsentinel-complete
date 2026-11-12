import type { SVGProps } from "react";
import { useId } from "react";

interface LogoProps extends SVGProps<SVGSVGElement> {
  size?: number;
  variant?: "full" | "mark";
}

/** Mark: a road node inside a sentinel ring (road graph + scan arc). Wordmark in the display face. */
export function Logo({ size = 32, className = "", variant = "mark", ...props }: LogoProps) {
  const gid = useId();
  const mark = (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" className={className} aria-hidden="true" {...props}>
      <defs>
        <linearGradient id={gid} x1="6" y1="4" x2="42" y2="44" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="var(--action)" />
          <stop offset="1" stopColor="var(--accent-2)" />
        </linearGradient>
      </defs>
      <rect x="3" y="3" width="42" height="42" rx="13" fill="var(--bg-elevation)" stroke={`url(#${gid})`} strokeWidth="2" />
      <path d="M12 36 22 24l6 3 8-13" stroke={`url(#${gid})`} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="12" cy="36" r="2.6" fill="var(--text-muted)" />
      <circle cx="22" cy="24" r="2.6" fill="var(--text-primary)" />
      <circle cx="36" cy="14" r="4.2" fill={`url(#${gid})`} />
      <circle cx="36" cy="14" r="7.5" stroke="var(--action)" strokeWidth="1" opacity="0.5" />
    </svg>
  );
  if (variant === "mark") return <span className="inline-flex items-center justify-center">{mark}</span>;
  return (
    <span className="inline-flex items-center gap-3">
      {mark}
      <span className="flex flex-col">
        <span className="font-display font-bold text-xl leading-none text-text-primary">
          Road<span className="text-gradient">Sentinel</span>
        </span>
        <span className="font-mono text-xs text-text-muted tracking-widest leading-tight mt-1">MONITORIZARE RUTIERĂ</span>
      </span>
    </span>
  );
}

export default Logo;
