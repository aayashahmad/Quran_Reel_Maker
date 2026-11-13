/* Noor: soft drops of gold light falling slowly over the page, each one gently twinkling.
   One fixed canvas over all content (pointer-events off), about 30 frames a second, paused when the tab is hidden;
   with "reduce motion" the light is drawn once and stays still. */
(function () {
  var c = document.createElement("canvas");
  c.setAttribute("aria-hidden", "true");
  // over the whole page, cards and sections too (clicks and text selection pass straight through it)
  c.style.cssText = "position:fixed;inset:0;width:100%;height:100%;z-index:2147483000;pointer-events:none";
  document.body.appendChild(c);
  var ctx = c.getContext("2d");
  if (!ctx) return;
  var still = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  var dpr = Math.min(window.devicePixelRatio || 1, 2), w = 0, h = 0, drops = [];

  // one soft gold glow, drawn once and reused for every drop
  var glow = document.createElement("canvas"), G = 64;
  glow.width = glow.height = G;
  var g = glow.getContext("2d"), grad = g.createRadialGradient(G / 2, G / 2, 0, G / 2, G / 2, G / 2);
  grad.addColorStop(0, "rgba(255,236,170,1)");
  grad.addColorStop(0.18, "rgba(240,213,147,.85)");
  grad.addColorStop(0.45, "rgba(212,175,95,.28)");
  grad.addColorStop(1, "rgba(212,175,95,0)");
  g.fillStyle = grad;
  g.fillRect(0, 0, G, G);

  function drop(top) {
    var big = Math.random() < 0.18;
    return {
      x: Math.random() * w, y: top ? -20 : Math.random() * h,
      r: big ? 2.2 + Math.random() * 1.6 : 0.8 + Math.random() * 1.3,      // core size (px)
      v: 6 + Math.random() * 16,                                            // falling speed (px/s)
      sway: 6 + Math.random() * 14, sp: 0.2 + Math.random() * 0.5, ph: Math.random() * 6.28,
      tw: 0.8 + Math.random() * 2.2, a: big ? 0.75 : 0.35 + Math.random() * 0.4, big: big
    };
  }
  function size() {
    w = innerWidth; h = innerHeight;
    c.width = Math.round(w * dpr); c.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    var n = Math.max(22, Math.min(80, Math.round(w * h / 20000)));
    while (drops.length < n) drops.push(drop(false));
    drops.length = n;
  }
  function draw(t) {
    ctx.clearRect(0, 0, w, h);
    ctx.globalCompositeOperation = "lighter";
    for (var i = 0; i < drops.length; i++) {
      var d = drops[i];
      var a = d.a * (0.45 + 0.55 * Math.abs(Math.sin(t * d.tw + d.ph)));    // the twinkle
      var x = d.x + Math.sin(t * d.sp + d.ph) * d.sway, s = d.r * 7;
      ctx.globalAlpha = a;
      ctx.drawImage(glow, x - s / 2, d.y - s / 2, s, s);
      if (d.big && a > 0.5) {                                                // a small four-point sparkle
        ctx.globalAlpha = (a - 0.5) * 1.6;
        ctx.strokeStyle = "rgba(255,236,170,1)";
        ctx.lineWidth = 0.8;
        ctx.beginPath();
        ctx.moveTo(x - d.r * 4, d.y); ctx.lineTo(x + d.r * 4, d.y);
        ctx.moveTo(x, d.y - d.r * 4); ctx.lineTo(x, d.y + d.r * 4);
        ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = "source-over";
  }
  var last = 0;
  function frame(ms) {
    requestAnimationFrame(frame);
    if (ms - last < 33) return;                                              // ~30 fps is plenty
    var dt = Math.min(0.1, (ms - last) / 1000);
    last = ms;
    for (var i = 0; i < drops.length; i++) {
      var d = drops[i];
      d.y += d.v * dt;
      if (d.y > h + 20) { drops[i] = drop(true); }
    }
    draw(ms / 1000);
  }
  size();
  addEventListener("resize", function () { size(); if (still) draw(1); });
  if (still) draw(1); else requestAnimationFrame(frame);
})();
