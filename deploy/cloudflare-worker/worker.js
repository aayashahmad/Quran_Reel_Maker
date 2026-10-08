// Sits in front of quranreelmaker.xyz. When neither computer is reachable (the ~1 minute while the
// site moves between the laptop and the backup server), Cloudflare would show its own error page;
// this shows a friendly "switching servers" page instead, which reloads itself until the site is back.
const DOWN = new Set([502, 503, 504, 520, 521, 522, 523, 524, 530]);

export default {
  async fetch(request) {
    let response;
    try {
      response = await fetch(request);
    } catch (e) {
      return switching(request);
    }
    // our own server's errors carry X-Served-By; only Cloudflare's "can't reach it" pages are replaced
    if (DOWN.has(response.status) && !response.headers.has("X-Served-By")) return switching(request);
    return response;
  },
};

function switching(request) {
  const headers = { "Retry-After": "60", "Cache-Control": "no-store", "X-Robots-Tag": "noindex" };
  if (new URL(request.url).pathname.startsWith("/api/")) {
    return Response.json({ error: "We're switching servers right now. Please try again in 1–2 minutes." },
                         { status: 503, headers });
  }
  return new Response(PAGE, { status: 503, headers: { ...headers, "Content-Type": "text/html; charset=utf-8" } });
}

const PAGE = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Switching servers · Quran Reel Maker</title>
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
  <p>We're switching servers right now.<br>Please visit again in 1–2 minutes.</p>
  <p class="ur">ہم سرور تبدیل کر رہے ہیں، براہِ کرم 1–2 منٹ بعد دوبارہ آئیں۔</p>
  <div class="spin" aria-hidden="true"></div>
  <p class="count" id="c" role="status">Trying again in 20 seconds…</p>
</main>
<script>
  let n = 20;
  setInterval(() => { n -= 1; if (n <= 0) location.reload(); else document.getElementById("c").textContent = "Trying again in " + n + " seconds…"; }, 1000);
</script>
</body></html>`;
