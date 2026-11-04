(() => {
  const SVG_NS = "http://www.w3.org/2000/svg";
  const DURATION = 10;
  const $ = (id) => document.getElementById(id);
  const el = (tag, attrs, parent) => {
    const node = document.createElementNS(SVG_NS, tag);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
    if (parent) parent.appendChild(node);
    return node;
  };

  const HEAD = { cx: 540, cy: 1010, rx: 400, ry: 340, baseY: 1350 };
  const BODY = { cx: 540, cy: 1760, rx: 430, ry: 360, baseY: 2120 };
  const EYE_L = { x: 385, y: 975 };
  const EYE_R = { x: 695, y: 975 };
  const MOUTH = { x: 540, y: 1210 };
  const ARM_L = { x: 250, y: 1530 };
  const ARM_R = { x: 830, y: 1530 };
  const LINES_CENTER = { x: 540, y: 1000 };

  const frac = (v) => v - Math.floor(v);
  const clamp01 = (v) => Math.min(1, Math.max(0, v));
  const noise = (t, seed) =>
    Math.sin(t * 13.7 + seed) * 0.5 + Math.sin(t * 29.3 + seed * 2.1) * 0.3 + Math.sin(t * 47.1 + seed * 3.7) * 0.2;
  const tf = (cx, cy, { sx = 1, sy = 1, rot = 0, tx = 0, ty = 0 } = {}) =>
    `translate(${cx + tx} ${cy + ty}) rotate(${rot}) scale(${sx} ${sy}) translate(${-cx} ${-cy})`;
  const at = (x, y, { sx = 1, sy = 1, rot = 0 } = {}) => `translate(${x} ${y}) rotate(${rot}) scale(${sx} ${sy})`;

  // Closed Catmull-Rom spline through a wobbling ellipse, so outlines never sit still.
  function blobPath(c, t, amp, seed, bottomFlatten) {
    const n = 40;
    const pts = [];
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2;
      const wobble = 1 + amp * (Math.sin(3 * a + t * 5.3 + seed) * 0.6 + Math.sin(5 * a - t * 7.1 + seed * 1.7) * 0.4);
      const ky = Math.sin(a) > 0 ? bottomFlatten : 1;
      pts.push([c.cx + Math.cos(a) * c.rx * wobble, c.cy + Math.sin(a) * c.ry * ky * wobble]);
    }
    let d = `M ${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`;
    for (let i = 0; i < n; i++) {
      const p0 = pts[(i - 1 + n) % n], p1 = pts[i], p2 = pts[(i + 1) % n], p3 = pts[(i + 2) % n];
      const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
      const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
      d += ` C ${c1[0].toFixed(1)} ${c1[1].toFixed(1)} ${c2[0].toFixed(1)} ${c2[1].toFixed(1)} ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`;
    }
    return d + " Z";
  }

  // ---------- build static pieces ----------
  const speedLines = $("speed-lines");
  for (let i = 0; i < 30; i++) {
    const a = (i / 30) * Math.PI * 2;
    const w0 = 0.006, w1 = 0.045 + (i % 3) * 0.012;
    const r0 = 330 + (i % 4) * 60, r1 = 1700;
    const p = [
      [Math.cos(a - w0) * r0, Math.sin(a - w0) * r0],
      [Math.cos(a - w1) * r1, Math.sin(a - w1) * r1],
      [Math.cos(a + w1) * r1, Math.sin(a + w1) * r1],
      [Math.cos(a + w0) * r0, Math.sin(a + w0) * r0],
    ];
    el("polygon", { points: p.map((q) => q.join(",")).join(" "), fill: "#fff" }, speedLines);
  }

  for (const eye of document.querySelectorAll("#eyes .veins")) {
    for (let i = 0; i < 6; i++) {
      const a = (i / 6) * Math.PI * 2 + 0.4;
      let x = Math.cos(a) * 100, y = Math.sin(a) * 100;
      let d = `M ${x.toFixed(1)} ${y.toFixed(1)}`;
      for (let k = 1; k <= 4; k++) {
        const r = 100 - k * 13;
        const jitter = (k % 2 ? 1 : -1) * 0.18;
        x = Math.cos(a + jitter) * r;
        y = Math.sin(a + jitter) * r;
        d += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
      }
      el("path", { d }, eye);
    }
  }

  // 7-segment digital clock
  const SEG_W = 130, SEG_H = 230, SEG_T = 26;
  const segPolys = (() => {
    const t = SEG_T, w = SEG_W, h = SEG_H, m = h / 2, hz = (x0, y0, len) =>
      `${x0},${y0} ${x0 + t / 2},${y0 - t / 2} ${x0 + len - t / 2},${y0 - t / 2} ${x0 + len},${y0} ${x0 + len - t / 2},${y0 + t / 2} ${x0 + t / 2},${y0 + t / 2}`;
    const vt = (x0, y0, len) =>
      `${x0},${y0} ${x0 + t / 2},${y0 + t / 2} ${x0 + t / 2},${y0 + len - t / 2} ${x0},${y0 + len} ${x0 - t / 2},${y0 + len - t / 2} ${x0 - t / 2},${y0 + t / 2}`;
    const g = 4;
    return {
      a: hz(t / 2 + g, t / 2, w - t - 2 * g),
      b: vt(w - t / 2, t / 2 + g, m - t / 2 - 2 * g),
      c: vt(w - t / 2, m + g, m - t / 2 - 2 * g),
      d: hz(t / 2 + g, h - t / 2, w - t - 2 * g),
      e: vt(t / 2, m + g, m - t / 2 - 2 * g),
      f: vt(t / 2, t / 2 + g, m - t / 2 - 2 * g),
      g: hz(t / 2 + g, m, w - t - 2 * g),
    };
  })();
  const DIGIT_SEGS = ["abcdef", "bc", "abdeg", "abcdg", "bcfg", "acdfg", "acdefg", "abc", "abcdefg", "abcdfg"];
  const clockDigits = $("clock-digits");
  const digitNodes = [175, 345, 605, 775].map((x) => {
    const g = el("g", { transform: `translate(${x} 165)` }, clockDigits);
    const segs = {};
    for (const [k, pts] of Object.entries(segPolys)) segs[k] = el("polygon", { points: pts }, g);
    return segs;
  });
  const colon = [el("circle", { cx: 540, cy: 235, r: 17 }, clockDigits), el("circle", { cx: 540, cy: 325, r: 17 }, clockDigits)];

  const SWEAT_ORIGINS = [
    [175, 820, -1], [905, 820, 1], [250, 700, -0.7], [830, 690, 0.7], [140, 980, -1.2], [945, 980, 1.2], [540, 640, 0.15], [420, 650, -0.35],
  ];
  const sweatNodes = SWEAT_ORIGINS.map(() => {
    const g = el("g", {}, $("sweat"));
    el("path", {
      d: "M 0 -42 C 18 -12 32 4 32 22 A 32 32 0 1 1 -32 22 C -32 4 -18 -12 0 -42 Z",
      fill: "#8fdcff", stroke: "#111", "stroke-width": 6, "stroke-linejoin": "round",
    }, g);
    el("ellipse", { cx: -10, cy: 18, rx: 7, ry: 11, fill: "#fff" }, g);
    return g;
  });

  const ANGER_SPOTS = [{ x: 830, y: 735, s: 1 }, { x: 245, y: 760, s: 0.7 }];
  const angerNodes = ANGER_SPOTS.map(() => {
    const g = el("g", {}, $("anger-marks"));
    for (let q = 0; q < 4; q++) {
      el("path", {
        d: "M 14 -58 Q 14 -14 58 -14", fill: "none", stroke: "#e8132b", "stroke-width": 20, "stroke-linecap": "round",
        transform: `rotate(${q * 90})`,
      }, g);
    }
    return g;
  });

  const zzzNodes = [0, 1, 2].map(() => {
    const t = el("text", { "font-size": 90, fill: "#cfe0ff", stroke: "#111", "stroke-width": 10, "paint-order": "stroke", "text-anchor": "middle" }, $("zzz"));
    t.textContent = "Z";
    return t;
  });

  // ---------- state animated by the GSAP timeline ----------
  const hex = (h) => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
  const S = {
    bgR: 27, bgG: 36, bgB: 80,
    slowAmp: 0.035, fastAmp: 0, sqX: 1, sqY: 1,
    eyeOpen: 0, veins: 0, tremble: 0, pupilScale: 1, lookX: 0, lookY: 0, brow: 0,
    sweat: 0, anger: 0, zzz: 1, soul: 0, alarm: 0, run: 0,
    flap: 0.06, armBase: -18, zoom: 1, shake: 0, mouthOpen: 0.35, scream: 0,
    lines: 0.08, lineRot: 0, clockPulse: 1,
  };
  const arm = { v: -45 };

  const tl = gsap.timeline({ paused: true });
  const bgTo = (color, time, dur = 0.15) => {
    const [r, g, b] = hex(color);
    tl.to(S, { bgR: r, bgG: g, bgB: b, duration: dur, ease: "power2.out" }, time);
  };
  const squash = (time, sx, sy, hold = 0.07) => {
    tl.to(S, { sqX: sx, sqY: sy, duration: hold, ease: "power2.out" }, time);
    tl.to(S, { sqX: 1, sqY: 1, duration: 0.8, ease: "elastic.out(1.2, 0.28)" }, time + hold);
  };

  // Arms flap -45° <-> +45° every 0.08s for the whole clip; S.flap scales how much of it is visible.
  tl.fromTo(arm, { v: -45 }, { v: 45, duration: 0.08, ease: "sine.inOut", repeat: Math.round(DURATION / 0.08) - 1, yoyo: true }, 0);
  tl.to(S, { lineRot: 40, duration: 1.8, ease: "none" }, 0);

  // 1.8s — alarm rings, soul slips out
  tl.to(S, { alarm: 1, shake: 1, duration: 0.05 }, 1.8);
  tl.to(S, { zzz: 0, duration: 0.2 }, 1.8);
  tl.to(S, { soul: 1, duration: 2.0, ease: "sine.inOut" }, 1.85);
  tl.to(S, { eyeOpen: 0.3, pupilScale: 0.8, brow: 1, duration: 0.3, ease: "back.out(3)" }, 1.8);
  tl.to(S, { mouthOpen: 1.1, duration: 0.3, ease: "back.out(2)" }, 1.8);
  tl.to(S, { flap: 0.55, armBase: 0, zoom: 1.08, lines: 0.35, fastAmp: 0.03, slowAmp: 0.01, duration: 0.3 }, 1.8);
  tl.to(S, { lineRot: 140, duration: 2.2, ease: "none" }, 1.8);
  bgTo("#3b1d6e", 1.8, 0.1);
  squash(1.8, 1.2, 0.8);
  squash(2.9, 1.1, 0.9);

  // 4.0s — realises it's Monday 08:48: soul snaps back, eyes bulge, extreme close-up
  tl.to(S, { alarm: 0, duration: 0.1 }, 4.0);
  tl.to(S, { soul: 0, duration: 0.22, ease: "power3.in" }, 4.0);
  tl.to(S, { eyeOpen: 1.25, duration: 0.28, ease: "back.out(3)" }, 4.0);
  tl.to(S, { veins: 1, pupilScale: 0.42, tremble: 1, sweat: 1, lookY: -22, brow: 2, duration: 0.25 }, 4.0);
  tl.to(S, { zoom: 1.32, shake: 0.6, lines: 0.5, mouthOpen: 1.6, flap: 0.3, duration: 0.18, ease: "power3.out" }, 4.0);
  tl.to(S, { clockPulse: 1.12, duration: 0.1, yoyo: true, repeat: 3 }, 4.0);
  tl.to(S, { lineRot: 260, duration: 1.6, ease: "none" }, 4.0);
  bgTo("#ff2f5b", 4.0, 0.08);
  squash(4.0, 0.85, 1.22, 0.1);

  // 5.6s — full panic run
  tl.to(S, { zoom: 1.06, duration: 0.3, ease: "power2.out" }, 5.6);
  tl.to(S, { run: 1, flap: 1, anger: 1, scream: 1, mouthOpen: 1.2, lines: 0.55, fastAmp: 0.05, lookY: 0, brow: 3, shake: 0.35, duration: 0.2 }, 5.6);
  tl.to(S, { lineRot: 1150, duration: 3.4, ease: "none" }, 5.6);
  bgTo("#ff8a00", 5.6, 0.12);
  tl.to(S, { zoom: 1.16, duration: 0.08, yoyo: true, repeat: 1, ease: "power2.out" }, 7.2);
  bgTo("#ff4a1c", 7.2, 0.1);
  tl.to(S, { zoom: 1.16, duration: 0.08, yoyo: true, repeat: 1, ease: "power2.out" }, 8.2);
  bgTo("#ff8a00", 8.2, 0.1);
  squash(7.2, 1.15, 0.86);
  squash(8.2, 1.15, 0.86);

  // 9.0s — 09:00, late confirmed: melts and the soul leaves for good
  tl.to(S, { run: 0.15, flap: 0.35, anger: 0.3, scream: 0, mouthOpen: 0.9, lines: 0.25, sweat: 0.6, tremble: 0.5, veins: 0.6, duration: 0.25 }, 9.0);
  tl.to(S, { eyeOpen: 0.55, pupilScale: 0.25, lookY: 12, duration: 0.3, ease: "back.out(2)" }, 9.0);
  tl.to(S, { soul: 1, duration: 1.0, ease: "sine.out" }, 9.0);
  tl.to(S, { zoom: 1.18, duration: 1.0, ease: "power1.out" }, 9.0);
  tl.to(S, { sqX: 1.16, sqY: 0.83, duration: 0.35, ease: "power2.out" }, 9.0);
  tl.to(S, { clockPulse: 1.15, duration: 0.12, yoyo: true, repeat: 5 }, 9.0);
  tl.to(S, { lineRot: 1240, duration: 1.0, ease: "power1.out" }, 9.0);
  bgTo("#1d0712", 9.0, 0.12);
  tl.set({}, {}, DURATION);

  // ---------- story beats derived directly from time ----------
  function clockAt(t) {
    if (t < 1.8) return "0847";
    if (t < 5.6) return "0848";
    if (t < 9.0) return `08${49 + Math.min(10, Math.floor(((t - 5.6) / 3.4) * 11))}`;
    return "0900";
  }
  function statusAt(t) {
    if (t < 1.8) return "Zzz... 쿨쿨";
    if (t < 4.0) return "따르르르릉!!!";
    if (t < 5.6) return "월...요일...?!";
    if (t < 9.0) return "지각이다아아악!!!";
    return "지각 확정...";
  }
  function clockColorAt(t) {
    if (t < 1.8) return "#59f3ff";
    if (t >= 9.0) return frac(t * 4) < 0.5 ? "#ff2b2b" : "#ffffff";
    return "#ff2b2b";
  }

  const nodes = {
    bg: $("bg"), flash: $("flash"), speedLines, status: $("status"), clock: $("clock"),
    camera: $("camera"), character: $("character"), body: $("body"), bodyShape: $("body-shape"),
    head: $("head"), headShape: $("head-shape"), eyeL: $("eye-l"), eyeR: $("eye-r"),
    pupilL: $("pupil-l"), pupilR: $("pupil-r"), browL: $("brow-l"), browR: $("brow-r"),
    mouthShape: $("mouth-shape"), soul: $("soul"), soulGhost: $("soul-ghost"), soulTail: $("soul-tail"),
    armL: $("left-arm"), armR: $("right-arm"), blushL: $("blush-l"), blushR: $("blush-r"),
    scleras: document.querySelectorAll("#eyes .sclera"), closed: document.querySelectorAll("#eyes .eye-closed"),
    veins: document.querySelectorAll("#eyes .veins"),
  };

  function render(t) {
    // background + speed lines
    const flashOn = S.alarm * (frac(t * 8) < 0.5 ? 0.85 : 0);
    nodes.bg.setAttribute("fill", `rgb(${S.bgR | 0},${S.bgG | 0},${S.bgB | 0})`);
    nodes.flash.setAttribute("opacity", flashOn.toFixed(3));
    nodes.flash.setAttribute("fill", frac(t * 4) < 0.5 ? "#ffe14d" : "#ff3b3b");
    nodes.speedLines.setAttribute("opacity", (S.lines * (0.85 + 0.15 * Math.sin(t * 31))).toFixed(3));
    nodes.speedLines.setAttribute("transform",
      `translate(${LINES_CENTER.x} ${LINES_CENTER.y}) rotate(${t * 18 + S.lineRot}) scale(${1 + 0.04 * Math.sin(t * 9)})`);

    // clock
    const digits = clockAt(t);
    const lit = clockColorAt(t);
    digits.split("").forEach((ch, i) => {
      const on = DIGIT_SEGS[+ch];
      for (const [k, poly] of Object.entries(digitNodes[i])) poly.setAttribute("fill", on.includes(k) ? lit : "#2a2a2a");
    });
    const colonOn = frac(t * 2) < 0.5 || S.alarm > 0.5;
    colon.forEach((c) => c.setAttribute("fill", colonOn ? lit : "#2a2a2a"));
    const ring = S.alarm + S.run * 0.25 + (t >= 9 ? 0.4 : 0);
    nodes.clock.setAttribute("transform", tf(540, 280, {
      sx: S.clockPulse, sy: S.clockPulse, rot: noise(t * 1.3, 7) * 4 * ring,
      tx: noise(t * 1.7, 1) * 14 * ring, ty: noise(t * 1.9, 2) * 8 * ring + Math.sin(t * 2.2) * 4,
    }));

    nodes.status.textContent = statusAt(t);
    const statusBeat = 1 + 0.06 * Math.abs(Math.sin(t * 9)) + 0.05 * S.alarm * Math.abs(noise(t, 4));
    nodes.status.setAttribute("transform", tf(540, 530, {
      sx: statusBeat, sy: statusBeat, rot: Math.sin(t * 5) * 3 + noise(t, 5) * 4 * (S.alarm + S.run),
    }));

    // camera: close-up push-ins + hand-held shake
    const shake = S.shake + S.run * 0.4;
    nodes.camera.setAttribute("transform", tf(540, 1150, {
      sx: S.zoom, sy: S.zoom, rot: noise(t, 11) * 2.2 * shake + Math.sin(t * 20) * 1.5 * S.run,
      tx: noise(t, 12) * 22 * shake + Math.sin(t * 10) * 18 * S.run, ty: noise(t, 13) * 18 * shake + Math.sin(t * 1.1) * 6,
    }));

    // running bob
    const step = Math.abs(Math.sin(t * Math.PI * 5));
    nodes.character.setAttribute("transform", `translate(0 ${(-step * 50 * S.run).toFixed(1)})`);

    // idle jelly breathing: head and body squash in opposite phase
    const breath = Math.sin(t * 2.6) * S.slowAmp + Math.sin(t * 17) * S.fastAmp;
    const land = (1 - step) * 0.06 * S.run;
    nodes.head.setAttribute("transform", tf(HEAD.cx, HEAD.baseY, {
      sx: S.sqX * (1 + breath + land), sy: S.sqY * (1 - breath - land),
      rot: Math.sin(t * 1.7) * 2 + Math.sin(t * 10) * 4 * S.run + noise(t, 21) * 2.5 * S.tremble,
    }));
    nodes.headShape.setAttribute("d", blobPath(HEAD, t, 0.012 + 0.012 * S.tremble + 0.01 * S.run, 0, 0.9));
    nodes.body.setAttribute("transform", tf(BODY.cx, BODY.baseY, {
      sx: 1 - breath * 0.7 + land * 0.5, sy: 1 + breath * 0.7 - land * 0.5, rot: Math.sin(t * 10 + 0.6) * 2.5 * S.run,
    }));
    nodes.bodyShape.setAttribute("d", blobPath(BODY, t, 0.01 + 0.01 * S.run, 2.1, 1));

    // arms: gentle sway when calm, frantic ±45° flapping when panicking
    const calmSway = Math.sin(t * 2.6 + 1) * 10 + Math.sin(t * 7.3) * 3;
    const armRot = arm.v * S.flap + calmSway * (1 - S.flap) + S.armBase;
    nodes.armL.setAttribute("transform", at(ARM_L.x, ARM_L.y, { rot: armRot }));
    nodes.armR.setAttribute("transform", at(ARM_R.x, ARM_R.y, { rot: -armRot + Math.sin(t * 3.1) * 4 * (1 - S.flap) }));

    // eyes: open amount squashes the sclera; eyeballs wobble separately from pupils
    const open = Math.max(0.02, S.eyeOpen);
    const eyeWob = (seed) => 1 + 0.03 * Math.sin(t * 6 + seed) + 0.05 * S.tremble * noise(t * 1.5, seed);
    [[nodes.eyeL, EYE_L, 1], [nodes.eyeR, EYE_R, 2]].forEach(([node, p, seed]) => {
      const w = eyeWob(seed);
      node.setAttribute("transform", at(p.x, p.y + Math.sin(t * 2.6) * 3, { sx: w * (open > 1 ? open : 1), sy: open * w }));
    });
    const closedOpacity = clamp01(1 - S.eyeOpen * 4).toFixed(3);
    nodes.closed.forEach((c) => {
      c.setAttribute("opacity", closedOpacity);
      c.setAttribute("transform", `scale(1 ${1 / open})`);
    });
    nodes.scleras.forEach((s) => s.setAttribute("opacity", clamp01(S.eyeOpen * 5).toFixed(3)));
    nodes.veins.forEach((v, i) => v.setAttribute("opacity", (S.veins * (0.75 + 0.25 * Math.sin(t * 12 + i))).toFixed(3)));

    const pupilVisible = clamp01(S.eyeOpen * 5);
    [[nodes.pupilL, EYE_L, 31], [nodes.pupilR, EYE_R, 37]].forEach(([node, p, seed]) => {
      const jx = noise(t * 2.2, seed) * 18 * S.tremble + Math.sin(t * 1.3 + seed) * 7 + S.lookX;
      const jy = noise(t * 2.4, seed + 3) * 18 * S.tremble + Math.cos(t * 1.1 + seed) * 5 + S.lookY;
      const s = S.pupilScale * (1 + 0.08 * Math.sin(t * 4 + seed));
      const maxOff = 105 * Math.min(1, open) - 42 * s - 6;
      const len = Math.hypot(jx, jy);
      const k = len > maxOff ? maxOff / len : 1;
      node.setAttribute("transform", at(p.x + jx * k, p.y + Math.sin(t * 2.6) * 3 + jy * k * Math.min(1, open), {
        sx: s * (open > 1 ? open : 1), sy: s * Math.min(1, open) * (open > 1 ? open : 1),
      }));
      node.setAttribute("opacity", pupilVisible.toFixed(3));
    });

    // brows: 0 relaxed, 1 raised, 2 shocked high, 3 panicked slant
    const browLift = [0, -35, -70, -40][Math.min(3, Math.round(S.brow))];
    const browTilt = S.brow >= 2.5 ? 18 : 0;
    const browBob = Math.sin(t * 6) * 5 + noise(t, 41) * 6 * S.tremble;
    nodes.browL.setAttribute("transform", at(EYE_L.x + 5, 840 + browLift * Math.min(1, open) + browBob - (S.eyeOpen > 1 ? 25 : 0), { rot: -browTilt }));
    nodes.browR.setAttribute("transform", at(EYE_R.x - 5, 840 + browLift * Math.min(1, open) + browBob - (S.eyeOpen > 1 ? 25 : 0), { rot: browTilt }));

    const blush = (0.55 + 0.15 * Math.sin(t * 3)).toFixed(3);
    nodes.blushL.setAttribute("opacity", blush);
    nodes.blushR.setAttribute("opacity", blush);

    // mouth size changes every frame
    const talk = 1 + 0.15 * Math.sin(t * 9) + 0.08 * Math.sin(t * 23);
    const yell = S.scream * 0.55 * Math.abs(Math.sin(t * 19));
    const mx = (0.45 + 0.55 * S.mouthOpen) * talk + yell * 0.4;
    const my = (0.3 + 0.8 * S.mouthOpen) * talk + yell;
    nodes.mouthShape.setAttribute("transform", at(MOUTH.x + noise(t, 51) * 6 * S.tremble, MOUTH.y + 10 * S.mouthOpen, { sx: mx, sy: my }));

    // soul: drifts up out of the mouth, wobbling side to side
    const p = S.soul;
    if (p > 0.002) {
      const sx = MOUTH.x + Math.sin(t * 5.5) * 70 * p + Math.sin(t * 2.1) * 20 * p;
      const sy = MOUTH.y - p * 640;
      const scale = 0.2 + 0.9 * p;
      nodes.soul.setAttribute("opacity", Math.min(0.95, p * 6).toFixed(3));
      nodes.soulGhost.setAttribute("transform", at(sx, sy, { sx: scale * (1 + 0.06 * Math.sin(t * 8)), sy: scale * (1 - 0.06 * Math.sin(t * 8)), rot: Math.sin(t * 5.5 + 1) * 12 }));
      const tailEndY = sy + 95 * scale;
      const cx = MOUTH.x + Math.sin(t * 7 + 2) * 90 * p;
      nodes.soulTail.setAttribute("d", `M ${MOUTH.x} ${MOUTH.y} Q ${cx.toFixed(1)} ${((MOUTH.y + tailEndY) / 2).toFixed(1)} ${sx.toFixed(1)} ${tailEndY.toFixed(1)}`);
      nodes.soulTail.setAttribute("stroke-width", (10 + 26 * p).toFixed(1));
    } else {
      nodes.soul.setAttribute("opacity", "0");
    }

    // sweat drops pop off the face
    sweatNodes.forEach((node, i) => {
      const [ox, oy, dir] = SWEAT_ORIGINS[i];
      const ph = frac(t * 1.7 + i * 0.37);
      const x = ox + dir * 260 * ph;
      const y = oy - 220 * ph + 520 * ph * ph;
      const s = (0.55 + 0.45 * Math.sin(Math.PI * Math.min(1, ph * 1.4))) * (1 + 0.1 * Math.sin(t * 20 + i));
      node.setAttribute("transform", at(x, y, { sx: s, sy: s, rot: dir * 25 * ph }));
      node.setAttribute("opacity", (S.sweat * clamp01(1.25 - ph * 1.25)).toFixed(3));
    });

    // anger marks throb and bounce
    angerNodes.forEach((node, i) => {
      const spot = ANGER_SPOTS[i];
      const amt = i === 0 ? S.anger : S.anger * S.run;
      const pulse = 1 + 0.3 * Math.abs(Math.sin(t * 13 + i * 1.3));
      const bounce = -Math.abs(Math.sin(t * 7 + i)) * 30;
      node.setAttribute("transform", at(spot.x + noise(t, 61 + i) * 8, spot.y + bounce, { sx: spot.s * pulse * amt, sy: spot.s * pulse * amt, rot: Math.sin(t * 6 + i) * 15 }));
      node.setAttribute("opacity", clamp01(amt * 3).toFixed(3));
    });

    // Zzz float up while asleep
    zzzNodes.forEach((node, i) => {
      const ph = frac(t * 0.6 + i / 3);
      node.setAttribute("x", (820 + ph * 120 + Math.sin(t * 3 + i) * 20).toFixed(1));
      node.setAttribute("y", (760 - ph * 260).toFixed(1));
      node.setAttribute("font-size", (50 + ph * 60).toFixed(1));
      node.setAttribute("opacity", (S.zzz * Math.sin(Math.PI * ph)).toFixed(3));
    });
  }

  tl.eventCallback("onUpdate", () => render(tl.time()));

  window.renderAt = (t) => {
    tl.seek(t, false);
    render(t);
  };
  window.DURATION = DURATION;

  if (new URLSearchParams(location.search).has("render")) {
    document.body.classList.add("render");
    window.renderAt(0);
  } else {
    tl.repeat(-1).play(0);
  }
})();
