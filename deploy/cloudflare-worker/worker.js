// Sits in front of quranreelmaker.xyz. The laptop serves the site through a Cloudflare tunnel; when it can't be
// reached (off, asleep, no internet), the same request goes to the free backup server on Render (BACKUP_URL),
// with the visitor's address passed on under a shared secret (PROXY_SECRET, a Worker secret) so its speed
// limits still apply per visitor. If neither answers, a friendly page reloads itself until the site is back.
// A timer pings the backup every 10 minutes so Render's free server doesn't fall asleep.
// Public pages (home, surahs, Ask topics...) are kept in Cloudflare's cache near each visitor, so they open at
// once anywhere: a copy is served immediately and, when older than FRESH seconds, refreshed in the background.
const DOWN = new Set([502, 503, 504, 520, 521, 522, 523, 524, 530]);
const ours = r => r.headers.has("X-Served-By");      // our own server answered (even with an error)

const FRESH = 120, KEEP = 86400;
const PAGES = ["/", "/surah", "/ask", "/privacy", "/terms", "/llms.txt", "/sitemap.xml", "/robots.txt"];
const cacheable = (req, url) => req.method === "GET" && (PAGES.includes(url.pathname) || /^\/(surah|ask)\/[\w-]+$/.test(url.pathname))
  && !(req.headers.get("Cookie") || "").includes("qrm_admin");

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (!cacheable(request, url)) return origin(request, env);
    const key = new Request(url.origin + url.pathname + url.search), cache = caches.default;
    const hit = await cache.match(key);
    const refresh = async () => {
      const r = await origin(new Request(key, { headers: { "User-Agent": request.headers.get("User-Agent") || "" } }), env);
      if (r.status === 200 && ours(r) && !r.headers.has("Set-Cookie")) {
        const copy = new Response(r.clone().body, r);
        copy.headers.set("Cache-Control", `public, max-age=${KEEP}`); copy.headers.set("X-Cached-At", String(Date.now()));
        await cache.put(key, copy);
      }
      return r;
    };
    if (hit) {
      if (Date.now() - Number(hit.headers.get("X-Cached-At") || 0) > FRESH * 1000) ctx.waitUntil(refresh().catch(() => {}));
      const out = new Response(hit.body, hit);
      out.headers.set("Cache-Control", "public, max-age=60"); out.headers.set("X-Edge-Cache", "HIT");
      return out;
    }
    const r = await refresh();
    const out = new Response(r.body, r); out.headers.set("X-Edge-Cache", "MISS");
    return out;
  },
  async scheduled(event, env, ctx) {
    if (env.BACKUP_URL) ctx.waitUntil(fetch(new URL("/robots.txt", env.BACKUP_URL)).catch(() => {}));
  },
};

async function origin(request, env) {
  {
    const spare = env.BACKUP_URL && !["GET", "HEAD"].includes(request.method) ? request.clone() : request;
    try {
      const response = await fetch(request);
      // Cloudflare's own "can't reach it" pages lack X-Served-By; our server's errors are passed on
      if (!(DOWN.has(response.status) && !ours(response))) return response;
    } catch (e) { /* laptop unreachable */ }
    if (env.BACKUP_URL) {
      try {
        const url = new URL(request.url), target = new URL(url.pathname + url.search, env.BACKUP_URL);
        const headers = new Headers(spare.headers);
        headers.set("X-Visitor-IP", request.headers.get("CF-Connecting-IP") || "");
        if (env.PROXY_SECRET) headers.set("X-Proxy-Secret", env.PROXY_SECRET);
        const r = await fetch(target, { method: spare.method, headers, redirect: "manual",
                                        body: ["GET", "HEAD"].includes(spare.method) ? undefined : spare.body });
        if (ours(r)) return r;
      } catch (e) { /* backup unreachable too */ }
    }
    return switching(request);
  }
}

// robots.txt must never fail (Google slows or stops crawling when it can't be read): a built-in copy
const ROBOTS = "User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /files/\nDisallow: /bg/\nDisallow: /admin\n\n" +
               "Sitemap: https://quranreelmaker.xyz/sitemap.xml\n";

function switching(request) {
  if (new URL(request.url).pathname === "/robots.txt")
    return new Response(ROBOTS, { headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "public, max-age=3600" } });
  const headers = { "Retry-After": "60", "Cache-Control": "no-store", "X-Robots-Tag": "noindex" };
  if (new URL(request.url).pathname.startsWith("/api/")) {
    return Response.json({ error: "Quran Reel Maker is offline for a moment. Please try again in a few minutes." },
                         { status: 503, headers });
  }
  return new Response(PAGE, { status: 503, headers: { ...headers, "Content-Type": "text/html; charset=utf-8" } });
}

const PAGE = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Back soon · Quran Reel Maker</title>
<style>
  body { margin: 0; min-height: 100vh; display: grid; place-items: center; padding: 24px 16px; box-sizing: border-box;
         background: radial-gradient(circle at 50% 20%, #0b3d2e, #05211a 70%); color: #f3efe2;
         font: 16px/1.6 system-ui, -apple-system, sans-serif; text-align: center; }
  main { width: 100%; max-width: 440px; box-sizing: border-box; border: 1px solid rgba(212,175,95,.4); border-radius: 18px; padding: 32px 24px; background: rgba(11,51,40,.85); }
  .ar { font-size: 30px; color: #f0d593; margin: 0 0 6px; font-family: serif; }
  h1 { font: 700 26px Georgia, serif; color: #d4af5f; margin: 6px 0 12px; }
  p { margin: 8px 0; color: #b3c7bc; }
  .ur { font-size: 19px; direction: rtl; }
  .count { margin-top: 18px; color: #f0d593; font-weight: 600; }
  .spin { width: 34px; height: 34px; margin: 18px auto 0; border: 3px solid rgba(212,175,95,.25); border-top-color: #d4af5f;
          border-radius: 50%; animation: s 1s linear infinite; }
  @keyframes s { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) { .spin { animation: none; } }
</style></head>
<body><main>
  <p class="ar">بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ</p>
  <h1>Quran Reel Maker</h1>
  <p>The site is offline for a moment.<br>Please visit again in a few minutes.</p>
  <p class="ur">ویب سائٹ تھوڑی دیر کے لیے بند ہے، براہِ کرم چند منٹ بعد دوبارہ آئیں۔</p>
  <div class="spin" aria-hidden="true"></div>
  <p class="count" id="c" role="status">Trying again in 20 seconds…</p>
</main>
<script>
  let n = 20;
  setInterval(() => { n -= 1; if (n <= 0) location.reload(); else document.getElementById("c").textContent = "Trying again in " + n + " seconds…"; }, 1000);
</script>
</body></html>`;
