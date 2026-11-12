const GENERIC_BODY = "New alert. Open RoadSentinel for details.";
const ALLOWED_PRIORITIES = new Set(["critical", "high", "medium", "info"]);

/**
 * Accept only the generic shape the server sends ("New alert, priority: X"); anything else
 * (a misconfigured or malicious sender) is replaced by fixed text. Never shows images or data.
 */
export function sanitizePush(data: unknown): { title: string; body: string; url: string } {
  const body = (data as { body?: unknown } | null)?.body;
  const match = typeof body === "string" ? /^New alert, priority: (\w+)$/.exec(body) : null;
  return {
    title: "RoadSentinel",
    body: match && ALLOWED_PRIORITIES.has(match[1]) ? (body as string) : GENERIC_BODY,
    url: "/alerts",
  };
}
