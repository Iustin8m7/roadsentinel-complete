/**
 * Wipe everything this origin may have stored on the device. Runs on logout, session expiry
 * and revocation, so a shared or lost device keeps no operational data.
 */
export async function clearClientState(): Promise<void> {
  const tasks: Promise<unknown>[] = [];

  // Cache Storage: includes any runtime cache; the app shell is re-fetched on next load.
  if ("caches" in globalThis) {
    tasks.push(caches.keys().then((keys) => Promise.all(keys.map((k) => caches.delete(k)))));
  }

  // IndexedDB: every database of this origin.
  if ("indexedDB" in globalThis && typeof indexedDB.databases === "function") {
    tasks.push(
      indexedDB.databases().then((dbs) =>
        Promise.all(
          dbs
            .map((db) => db.name)
            .filter((name): name is string => !!name)
            .map(
              (name) =>
                new Promise<void>((resolve) => {
                  const req = indexedDB.deleteDatabase(name);
                  req.onsuccess = req.onerror = req.onblocked = () => resolve();
                }),
            ),
        ),
      ),
    );
  }

  // Push: stop notifications for this user on this device.
  if ("serviceWorker" in navigator) {
    tasks.push(
      navigator.serviceWorker.getRegistration().then(async (reg) => {
        const sub = await reg?.pushManager?.getSubscription();
        await sub?.unsubscribe();
        reg?.active?.postMessage({ type: "CLEAR_RUNTIME_CACHES" });
      }),
    );
  }

  await Promise.allSettled(tasks);
  // Web Storage is not used for auth, but clear it defensively (e.g. UI preferences).
  try {
    globalThis.localStorage?.clear();
    globalThis.sessionStorage?.clear();
  } catch {
    /* storage disabled */
  }
}
