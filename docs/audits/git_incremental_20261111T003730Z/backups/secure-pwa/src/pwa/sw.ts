/// <reference lib="webworker" />
/**
 * Service worker. Security rules:
 *  - precache ONLY the static, build-time app shell (hashed JS/CSS, HTML, icons, offline page);
 *  - never cache /api/* (requests go straight to the network, responses are no-store anyway);
 *  - push notifications display generic text only; details are fetched after login.
 */
import { cleanupOutdatedCaches, precacheAndRoute } from "workbox-precaching";

import { sanitizePush } from "./pushPayload";

declare const self: ServiceWorkerGlobalScope & {
  __WB_MANIFEST: Array<{ url: string; revision: string | null }>;
};

const OFFLINE_URL = "/offline.html";

precacheAndRoute(self.__WB_MANIFEST);
cleanupOutdatedCaches();

self.addEventListener("install", () => {
  void self.skipWaiting();
});
self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin || url.pathname.startsWith("/api/")) {
    return; // network only, untouched
  }
  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request).catch(async () => (await caches.match(OFFLINE_URL)) ?? Response.error()),
    );
  }
});

// Logout: drop any non-precache cache (there should be none; defence in depth).
self.addEventListener("message", (event) => {
  if ((event.data as { type?: string } | null)?.type === "CLEAR_RUNTIME_CACHES") {
    event.waitUntil(
      caches
        .keys()
        .then((keys) =>
          Promise.all(
            keys.filter((k) => !k.startsWith("workbox-precache")).map((k) => caches.delete(k)),
          ),
        ),
    );
  }
});

function parsePushData(event: PushEvent): unknown {
  try {
    return event.data?.json();
  } catch {
    return null;
  }
}

self.addEventListener("push", (event) => {
  const n = sanitizePush(parsePushData(event));
  event.waitUntil(
    self.registration.showNotification(n.title, {
      body: n.body,
      tag: "rs-alert",
      icon: "/icons/icon-192.png",
      data: { url: n.url },
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(self.clients.openWindow("/alerts"));
});
