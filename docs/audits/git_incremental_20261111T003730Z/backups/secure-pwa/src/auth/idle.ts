export const IDLE_LOCK_MS = 5 * 60 * 1000;
const ACTIVITY_EVENTS = [
  "pointerdown",
  "keydown",
  "wheel",
  "touchstart",
  "visibilitychange",
] as const;

/**
 * Calls ``onIdle`` after ``timeoutMs`` without user activity. Returns a disposer.
 * Uses wall-clock comparison so a suspended tab (laptop lid closed) locks on resume.
 */
export function startIdleTimer(
  onIdle: () => void,
  timeoutMs: number = IDLE_LOCK_MS,
  target: Pick<Window, "addEventListener" | "removeEventListener"> = window,
): () => void {
  let last = Date.now();
  let fired = false;
  const touch = () => {
    if (!fired) last = Date.now();
  };
  const check = () => {
    if (!fired && Date.now() - last >= timeoutMs) {
      fired = true;
      onIdle();
    }
  };
  ACTIVITY_EVENTS.forEach((e) => target.addEventListener(e, touch, { passive: true }));
  const interval = setInterval(check, 1000);
  return () => {
    clearInterval(interval);
    ACTIVITY_EVENTS.forEach((e) => target.removeEventListener(e, touch));
  };
}
