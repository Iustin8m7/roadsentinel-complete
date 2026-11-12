// The strictest policy the apps need: same as deploy/Caddyfile and deploy/railway-web/Caddyfile.
// The walks serve every build with it, so any inline style/script, CDN, external font/tile or
// third-party request shows up as a console error / foreign-host failure.
export const CSP = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob: https://a.tile.openstreetmap.org https://b.tile.openstreetmap.org https://c.tile.openstreetmap.org; media-src 'self' blob:; connect-src 'self'; font-src 'self'; manifest-src 'self'; worker-src 'self'; frame-src https://webcamromania.ro; frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'"
