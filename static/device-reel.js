// Makes a reel in the visitor's browser instead of on the server: draws each frame on a canvas
// (same layout as video.py), plays the recitation through Web Audio, and records both with
// MediaRecorder. Recording runs in real time, so a 40-second reel takes about 40 seconds.
// Uses the page's globals: $, api, setStatus, surah, from, to, showDeviceResult.
const DeviceReel = (() => {
  const W = 1080, H = 1920, INTRO = 1.5, MAX_SECONDS = 10 * 60;
  const GOLD = "rgb(212,175,95)", WHITE = "rgb(245,245,240)", SOFT = "rgb(200,215,205)", MUTED = "rgb(140,170,155)";
  const DIM = "rgb(150,175,165)", HL_BG = "rgb(92,74,28)", RULE = "rgb(90,130,110)";
  const AR_DIGITS = n => String(n).replace(/\d/g, d => "٠١٢٣٤٥٦٧٨٩"[d]);
  // the server's fonts, by the browser's names (other scripts use the device's own fonts)
  const FAMILY = { "NotoNastaliqUrdu.ttf": '"Noto Nastaliq Urdu"', "NotoNaskhArabic.ttf": "Amiri" };
  // translation text per font: size, smallest size, line height, highlight band (as video.TR_STYLE)
  const TR_STYLE = { "NotoNastaliqUrdu.ttf": [52, 28, 2.0, 0.15], "NotoNaskhArabic.ttf": [50, 28, 1.85, 0.2] };
  const TR_DEFAULT = [50, 26, 1.6, 0.0];

  const font = (family, size) => `${size}px ${family}`;
  const sansFamily = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';

  // ---- text layout (mirrors video.py: draw_block, draw_words, center) ----
  function graphemes(word) {
    if (window.Intl && Intl.Segmenter) return [...new Intl.Segmenter(undefined, { granularity: "grapheme" }).segment(word)].map(s => s.segment);
    return [...word];
  }
  function wrap(ctx, text, maxW) {
    const fits = t => ctx.measureText(t).width <= maxW, pieces = [];
    for (const word of text.split(/\s+/).filter(Boolean)) {
      if (fits(word)) { pieces.push([word, false]); continue; }
      let chunk = "", first = true;      // too wide for a line (e.g. Chinese): break between letters
      for (const ch of graphemes(word)) {
        if (chunk && !fits(chunk + ch)) { pieces.push([chunk, !first]); chunk = ""; first = false; }
        chunk += ch;
      }
      pieces.push([chunk, !first]);
    }
    const lines = []; let cur = "";
    for (const [word, glued] of pieces) {
      const t = (cur + (glued ? "" : " ") + word).trim();
      if (fits(t) || !cur) cur = t; else { lines.push(cur); cur = word; }
    }
    if (cur) lines.push(cur);
    return lines;
  }
  function drawBlock(ctx, text, family, y, maxH, size, minSize, color, lh, rtl, width = W) {
    let lines, lineH;
    for (;;) {
      ctx.font = font(family, size); ctx.direction = rtl ? "rtl" : "ltr";
      lines = wrap(ctx, text, width - 140); lineH = Math.round(size * lh);
      if (lines.length * lineH <= maxH || size <= minSize) break;
      size -= 4;
    }
    // Pillow puts the font's ascender line at y; a canvas draws from the baseline, so shift by the ascent
    ctx.fillStyle = color; ctx.textAlign = "center"; ctx.textBaseline = "alphabetic";
    for (const ln of lines) { ctx.fillText(ln, width / 2, y + ctx.measureText(ln).fontBoundingBoxAscent); y += lineH; }
    ctx.textAlign = "start";
    return y;
  }
  function center(ctx, text, size, y, color, width = W) {
    ctx.font = font("Amiri, serif", size); ctx.direction = "ltr"; ctx.fillStyle = color;
    ctx.textAlign = "center"; ctx.textBaseline = "alphabetic";
    ctx.fillText(text, width / 2, y + ctx.measureText(text).fontBoundingBoxAscent); ctx.textAlign = "start";
  }
  // Word layout computed once per ayah; drawWords then paints it with any word highlighted.
  function layoutWords(ctx, tokens, y, maxH, size, minSize, lh, family, rtl, band, urdu) {
    const maxW = W - 140;
    let lines, space, lineH;
    for (;;) {
      ctx.font = font(family, size); ctx.direction = rtl ? "rtl" : "ltr";
      space = ctx.measureText(" ").width;
      if (urdu) space = Math.max(space, size * 0.45);
      lines = []; let cur = [], curW = 0;
      for (const [text, idx] of tokens) {
        const m = ctx.measureText(text), ww = m.width;
        if (cur.length && curW + space + ww > maxW) { lines.push([cur, curW]); cur = []; curW = 0; }
        curW += (cur.length ? space : 0) + ww;
        cur.push({ text, idx, ww, up: m.actualBoundingBoxAscent, down: m.actualBoundingBoxDescent, asc: m.fontBoundingBoxAscent });
      }
      if (cur.length) lines.push([cur, curW]);
      lineH = Math.round(size * lh);
      if (lines.length * lineH <= maxH || size <= minSize) break;
      size -= 4;
    }
    const placed = [];
    for (const [words, lineW] of lines) {
      const asc = words[0].asc;                                  // text top at y, as Pillow places it
      let top = Math.min(...words.map(w => asc - w.up)) - 8, bottom = Math.max(...words.map(w => asc + w.down)) + 8;
      const top0 = size * band;
      top = Math.max(top, top0); bottom = Math.min(bottom, top0 + lineH);
      let x = rtl ? (W + lineW) / 2 : (W - lineW) / 2;
      for (const w of words) {
        if (rtl) x -= w.ww;
        placed.push({ ...w, x, y, top: y + top, bottom: y + bottom });
        x += rtl ? -space : w.ww + space;
      }
      y += lineH;
    }
    const pad = Math.min(12, space * 0.45);
    return { size, family, rtl, placed, end: y, pad };
  }
  function drawWords(ctx, lay, color, hl) {
    ctx.font = font(lay.family, lay.size); ctx.direction = "ltr"; ctx.textAlign = "start"; ctx.textBaseline = "alphabetic";
    for (const w of lay.placed) {
      const hit = hl != null && w.idx === hl;
      if (hit) { ctx.fillStyle = HL_BG; roundRect(ctx, w.x - lay.pad, w.top, w.ww + 2 * lay.pad, w.bottom - w.top, 14); }
      ctx.fillStyle = hit ? GOLD : color;
      ctx.direction = lay.rtl ? "rtl" : "ltr"; ctx.textAlign = lay.rtl ? "right" : "left";
      ctx.fillText(w.text, lay.rtl ? w.x + w.ww : w.x, w.y + w.asc);
    }
    ctx.textAlign = "start"; ctx.direction = "ltr";
  }
  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); ctx.fill();
  }

  // ---- one ayah's frame (mirrors video.make_frame), laid out once ----
  function layoutAyah(ctx, row, data, lang) {
    const tokens = row.words.map((w, i) => [w, i]);
    if (!row.bism) tokens.push(["۝" + AR_DIGITS(row.n), null]);
    const ar = layoutWords(ctx, tokens, 380, 640, 78, 34, 1.9, '"Amiri Quran", Amiri, serif', true, 0.55, false);
    let y = ar.end, sajdaY = null;
    if (row.sajda) { sajdaY = y; y += Math.round(40 * 2.2); }
    y = Math.max(y + 40, 1060);
    const [size, minSize, lh, band] = TR_STYLE[data.font] || TR_DEFAULT;
    const family = FAMILY[data.font] || sansFamily;
    const tr = data.spaced
      ? layoutWords(ctx, row.tr.split(/\s+/).filter(Boolean).map((w, i) => [w, i]), y + 10, H - y - 260, size, minSize, lh,
                    family, data.rtl, band, data.font === "NotoNastaliqUrdu.ttf")
      : null;
    return { ar, tr, trY: y, sajdaY, row, family, trStyle: [size, minSize, lh] };
  }
  function drawAyah(ctx, L, data, surahEn, state) {
    const row = L.row;
    center(ctx, `Surah ${surahEn}  •  ${row.bism ? "Bismillah" : `${data.surah}:${row.n}`}`, 56, 110, GOLD);
    drawBlock(ctx, data.ar, "Amiri, serif", 190, 140, 80, 50, GOLD, 1.5, true);
    ctx.fillStyle = GOLD; ctx.fillRect(240, 328, W - 480, 3);
    drawWords(ctx, L.ar, state.tr ? DIM : WHITE, state.tr ? null : state.hl);
    if (L.sajdaY != null) drawBlock(ctx, "آیتِ سجدہ", '"Noto Nastaliq Urdu"', L.sajdaY, 110, 40, 30, GOLD, 2.2, true);
    ctx.fillStyle = RULE; ctx.fillRect(400, L.trY - 21, W - 800, 2);
    const color = state.read ? (state.tr ? WHITE : DIM) : SOFT;
    if (L.tr) drawWords(ctx, L.tr, color, state.tr ? state.trHl : null);
    else drawBlock(ctx, row.tr, L.family, L.trY + 10, H - L.trY - 260, L.trStyle[0], L.trStyle[1], color, L.trStyle[2], data.rtl);
  }

  // ---- title card (mirrors video.card) ----
  function drawCard(ctx, info, data, w, h) {
    ctx.strokeStyle = GOLD; ctx.lineWidth = 4; ctx.strokeRect(26, 26, w - 52, h - 52);
    const withTranslation = (y, size) => {
      if (data.lang === "ur") return drawBlock(ctx, "قرآن پاک اردو ترجمہ کے ساتھ", '"Noto Nastaliq Urdu"', y, size * 3, size,
                                               Math.floor(size * 5 / 8), SOFT, 2.0, true, w);
      center(ctx, `With ${data.name} translation`, Math.floor(size * 7 / 8), y + Math.floor(size / 4), SOFT, w);
      if (data.native !== data.name) drawBlock(ctx, data.native, FAMILY[data.font] || sansFamily, y + Math.floor(size * 3 / 2),
                                               size * 2, Math.floor(size * 3 / 4), Math.floor(size / 2), MUTED, 1.6, data.rtl, w);
    };
    if (h > w) {
      center(ctx, `Surah ${data.surah}`, 60, 380, MUTED, w);
      drawBlock(ctx, data.ar, "Amiri, serif", 480, 330, 190, 90, GOLD, 1.6, true, w);
      center(ctx, `Surah ${data.en}`, 88, 860, WHITE, w);
      center(ctx, info.label, 66, 990, GOLD, w);
      withTranslation(1260, 64);
    } else {
      drawBlock(ctx, data.ar, "Amiri, serif", 50, 270, 170, 80, GOLD, 1.5, true, w);
      center(ctx, `Surah ${data.en}`, 72, 330, WHITE, w);
      center(ctx, info.label, 54, 435, GOLD, w);
      withTranslation(530, 48);
    }
  }
  function thumbnail(info, data) {
    const c = document.createElement("canvas"); c.width = 1280; c.height = 720;
    const ctx = c.getContext("2d"), g = ctx.createLinearGradient(0, 0, 0, 720);
    g.addColorStop(0, "rgb(11,61,46)"); g.addColorStop(1, "rgb(3,20,15)");
    ctx.fillStyle = g; ctx.fillRect(0, 0, 1280, 720);
    drawCard(ctx, info, data, 1280, 720);
    return new Promise(res => c.toBlob(res, "image/jpeg", 0.9));
  }

  // ---- timing (mirrors video.word_timeline / tr_timeline) ----
  function wordTimeline(segments, nwords, dur) {
    const out = []; let t = 0;
    for (const [pos, start, end] of [...segments].sort((a, b) => a[1] - b[1])) {
      if (pos < 1 || pos > nwords) continue;
      const s = Math.max(start / 1000, t), e = Math.min(end / 1000, dur);
      if (e <= s) continue;
      if (s > t) {
        const last = out.at(-1);
        if (last && last[1] != null && s - t < 0.35) last[0] += s - t; else out.push([s - t, null]);
      }
      out.push([e - s, pos - 1]); t = e;
    }
    if (dur > t) out.push([dur - t, null]);
    return out;
  }
  function voiced(buf) {               // speech parts: silence = under -35 dB for at least 0.25 s
    const data = buf.getChannelData(0), rate = buf.sampleRate, win = Math.round(rate * 0.01), limit = Math.pow(10, -35 / 20);
    const out = []; let speechFrom = null, quiet = 0;
    for (let i = 0; i < data.length; i += win) {
      let sum = 0; const end = Math.min(i + win, data.length);
      for (let k = i; k < end; k++) sum += data[k] * data[k];
      const loud = Math.sqrt(sum / (end - i)) >= limit, t = i / rate;
      if (loud) { if (speechFrom == null) speechFrom = t; quiet = 0; }
      else if (speechFrom != null && (quiet += 0.01) >= 0.25) { out.push([speechFrom, t - quiet + 0.01]); speechFrom = null; quiet = 0; }
    }
    if (speechFrom != null) out.push([speechFrom, buf.duration]);
    return out.filter(([a, b]) => b - a > 0.05).length ? out.filter(([a, b]) => b - a > 0.05) : [[0, buf.duration]];
  }
  function trTimeline(buf, words) {
    const weights = words.map(w => Math.max(1, w.replace(/[^\p{L}\p{N}_]/gu, "").length) + 1);
    const segs = voiced(buf), total = segs.reduce((a, [s, e]) => a + e - s, 0), sum = weights.reduce((a, b) => a + b, 0);
    const real = x => { for (const [s, e] of segs) { if (x <= e - s) return s + x; x -= e - s; } return segs.at(-1)[1]; };
    const out = []; let t = 0, acc = 0;
    weights.forEach((w, i) => {
      const s = real(acc / sum * total); acc += w; const e = real(acc / sum * total);
      if (s > t) out.push([s - t, i ? i - 1 : null]);
      out.push([e - s, i]); t = e;
    });
    if (buf.duration > t) out.push([buf.duration - t, words.length ? words.length - 1 : null]);
    return out.filter(([sec]) => sec > 0);
  }

  // ---- making the reel ----
  async function decode(ctx, url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error("Could not download the audio. Please try again.");
    return ctx.decodeAudioData(await r.arrayBuffer());
  }
  function pickType() {
    const types = ["video/mp4;codecs=avc1.640028,mp4a.40.2", "video/mp4;codecs=avc1,mp4a", "video/mp4",
                   "video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm"];
    return types.find(t => window.MediaRecorder && MediaRecorder.isTypeSupported(t));
  }
  function supported() {
    return !!(window.MediaRecorder && HTMLCanvasElement.prototype.captureStream && (window.AudioContext || window.webkitAudioContext) && pickType());
  }

  async function make({ surahNo, first, last, lang, read, bg: chosen, preview, log }) {
    const audio = new (window.AudioContext || window.webkitAudioContext)();   // created in the click: allowed to play
    try {
      log("Loading the surah…");
      const data = await api(`/api/surah/${surahNo}?lang=${encodeURIComponent(lang)}`);
      const ayat = data.ayat.slice(first - 1, last), full = first === 1 && last === data.ayat.length;
      const rows = (first === 1 && data.bismillah ? [{ ...data.bismillah, bism: true }] : []).concat(ayat);
      const rng = first === last ? `${first}` : `${first}-${last}`;
      const info = { label: full ? `Full Surah  •  ${data.ayat.length} Ayat` : (first === last ? `Ayah ${rng}` : `Ayat ${rng}`) };
      const style = data.styles.includes(chosen) ? chosen                               // chosen, or as backgrounds.pick
        : data.styles[(surahNo * 7919 + first * 131) % data.styles.length];
      const voice = read && !!rows[0].tr_audio_local;

      await Promise.all(['78px "Amiri Quran"', "80px Amiri", '52px "Noto Nastaliq Urdu"'].map(f => document.fonts.load(f)));
      const bg = document.createElement("video");
      bg.src = `/bg/${style}.mp4`; bg.muted = true; bg.loop = true; bg.playsInline = true; bg.crossOrigin = "anonymous";
      const bgReady = new Promise((res, rej) => { bg.oncanplay = res; bg.onerror = () => rej(new Error("Could not load the background.")); });

      let done = 0;
      const total = rows.length * (voice ? 2 : 1);
      const step = () => log(`Downloading audio ${++done}/${total}…`);
      const buffers = await Promise.all(rows.map(async r => {
        const ar = await decode(audio, r.audio); step();
        const tr = voice ? await decode(audio, r.tr_audio_local) : null; if (voice) step();
        return { ar, tr };
      }));
      await bgReady;

      // schedule: [start, end, layout, state]; the title card first
      const canvas = preview; canvas.width = W; canvas.height = H;
      const ctx = canvas.getContext("2d");
      const plan = [], sounds = [];
      let t = INTRO;
      rows.forEach((row, i) => {
        const L = layoutAyah(ctx, row, data, lang), b = buffers[i];
        sounds.push([t, b.ar]);
        for (const [sec, hl] of wordTimeline(row.segments || [], row.words.length, b.ar.duration)) {
          plan.push([t, t + sec, L, { hl, tr: false, read: voice }]); t += sec;
        }
        if (b.tr) {
          sounds.push([t, b.tr]);
          const tl = data.spaced ? trTimeline(b.tr, row.tr.split(/\s+/).filter(Boolean)) : [[b.tr.duration, null]];
          for (const [sec, hl] of tl) { plan.push([t, t + sec, L, { trHl: hl, tr: true, read: true }]); t += sec; }
        }
      });
      const length = t;
      if (length > MAX_SECONDS) throw new Error(`This selection is about ${Math.round(length / 60)} minutes long. ` +
        "Choose fewer ayat, or use Generate in cloud, which splits it into parts.");

      // record: the canvas (drawn every frame) + the recitation
      const dest = audio.createMediaStreamDestination();
      const stream = canvas.captureStream(30);
      dest.stream.getAudioTracks().forEach(tr => stream.addTrack(tr));
      const type = pickType(), chunks = [];
      const rec = new MediaRecorder(stream, { mimeType: type, videoBitsPerSecond: 3_500_000, audioBitsPerSecond: 160_000 });
      rec.ondataavailable = e => e.data.size && chunks.push(e.data);
      const stopped = new Promise(res => rec.onstop = res);
      await bg.play();
      rec.start(1000);
      const t0 = audio.currentTime + 0.3;
      for (const [at, buf] of sounds) {
        const src = audio.createBufferSource(); src.buffer = buf;
        src.connect(dest); src.connect(audio.destination);       // recorded, and heard while it records
        src.start(t0 + at);
      }
      let k = 0;
      await new Promise(resolve => {
        const frame = () => {
          const now = audio.currentTime - t0;
          ctx.shadowColor = "transparent";
          ctx.drawImage(bg, 0, 0, W, H);
          ctx.shadowColor = "rgba(0,0,0,0.9)"; ctx.shadowBlur = 16;   // soft halo under the text, as on the server
          if (now < INTRO) drawCard(ctx, info, data, W, H);
          else {
            while (k < plan.length - 1 && plan[k][1] <= now) k++;
            const [, , L, state] = plan[k];
            drawAyah(ctx, L, data, data.en, state);
          }
          log(`Recording on this device… ${Math.min(100, Math.round(Math.max(now, 0) / length * 100))}% (keep this tab open)`);
          if (now >= length + 0.15) return resolve();
          requestAnimationFrame(frame);
        };
        requestAnimationFrame(frame);
      });
      rec.stop(); await stopped; bg.pause();
      const ext = type.startsWith("video/mp4") ? "mp4" : "webm";
      const video = new Blob(chunks, { type: type.split(";")[0] });
      log("Writing the title and description…");
      const meta = await api(`/api/meta?surah=${surahNo}&from=${first}&to=${last}&lang=${encodeURIComponent(lang)}&read=${voice ? 1 : 0}`);
      return { video, ext, thumb: await thumbnail(info, data), meta, seconds: length };
    } finally {
      audio.close();
    }
  }
  return { make, supported };
})();
