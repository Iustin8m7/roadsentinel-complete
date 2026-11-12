import { registerSW } from "virtual:pwa-register";

/** Register the service worker (production builds only; no inline script needed). */
export function registerServiceWorker(): void {
  if (!("serviceWorker" in navigator) || import.meta.env.DEV) return;
  registerSW({ immediate: true });
}
