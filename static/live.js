// Counts people on the site right now (admin dashboard "Active now"): while this tab is visible it sends a tiny
// ping every 30 seconds with a random id made up for this tab only. No cookies, nothing stored on this device.
(() => {
  const sid = Array.from(crypto.getRandomValues(new Uint8Array(12)), b => (b % 36).toString(36)).join("");
  const p = location.pathname;
  const where = p === "/" ? "home" : p.startsWith("/surah") ? "surah" : p.startsWith("/ask") ? "ask" : "other";
  const body = leave => JSON.stringify({ sid, where, act: window.QRM_ACT || "", leave });
  const send = () => { if (!document.hidden) fetch("/api/ping", { method: "POST", headers: { "Content-Type": "application/json" }, body: body(false), keepalive: true }).catch(() => {}); };
  send();
  setInterval(send, 30000);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) navigator.sendBeacon?.("/api/ping", new Blob([body(true)], { type: "application/json" }));
    else send();
  });
  window.QRM_PING = send;          // the page calls it when what the visitor is doing changes
})();
