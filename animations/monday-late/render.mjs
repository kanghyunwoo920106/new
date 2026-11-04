// Usage:
//   node render.mjs                      -> out/monday-late.mp4 (10s, 60fps, 1080x1920, with sound)
//   node render.mjs --stills 0.5,3,4.3   -> out/still-<t>.png for quick checks
import { spawn } from "node:child_process";
import { mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import puppeteer from "puppeteer-core";

const here = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.join(here, "out");
mkdirSync(outDir, { recursive: true });

const FPS = 60;
const args = process.argv.slice(2);
const stillsArg = args.includes("--stills") ? args[args.indexOf("--stills") + 1] : null;
const chrome = process.env.CHROME_PATH || "/usr/local/bin/google-chrome";

// Alarm beeps (1.8-4.0s), shock sting (4.0s), footsteps (5.6-9.0s), deflating "pwoo" (9.0-10s).
const AUDIO_EXPR = [
  "0.22*sin(2*PI*1320*t)*gte(t,1.8)*lt(t,4)*lt(mod(t,0.125),0.07)",
  "0.35*sin(2*PI*(900*(t-4)-1400*(t-4)*(t-4)))*gte(t,4)*lt(t,4.3)*exp(-6*(t-4))",
  "0.5*sin(2*PI*70*mod(t-5.6,0.2))*exp(-35*mod(t-5.6,0.2))*gte(t,5.6)*lt(t,9)",
  "0.25*sin(2*PI*(520*(t-9)-180*(t-9)*(t-9)))*gte(t,9)*exp(-1.2*(t-9))",
].join("+");

const browser = await puppeteer.launch({
  executablePath: chrome,
  headless: true,
  args: ["--no-sandbox", "--allow-file-access-from-files", "--force-color-profile=srgb"],
});
const page = await browser.newPage();
await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(path.join(here, "index.html")).href + "?render=1", { waitUntil: "load" });
await page.evaluate(() => document.fonts.ready);
const stage = await page.$("#stage");

if (stillsArg) {
  for (const t of stillsArg.split(",").map(Number)) {
    await page.evaluate((tt) => window.renderAt(tt), t);
    await stage.screenshot({ path: path.join(outDir, `still-${t}.png`) });
  }
  await browser.close();
  process.exit(0);
}

const duration = await page.evaluate(() => window.DURATION);
const total = Math.round(duration * FPS);
const outFile = path.join(outDir, "monday-late.mp4");
const ff = spawn("ffmpeg", [
  "-y", "-loglevel", "error",
  "-f", "image2pipe", "-framerate", String(FPS), "-c:v", "png", "-i", "-",
  "-f", "lavfi", "-i", `aevalsrc='${AUDIO_EXPR}':s=44100:d=${duration}`,
  "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "18",
  "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", outFile,
], { stdio: ["pipe", "inherit", "inherit"] });

for (let i = 0; i < total; i++) {
  await page.evaluate((tt) => window.renderAt(tt), i / FPS);
  const png = await stage.screenshot({ type: "png" });
  if (!ff.stdin.write(png)) await new Promise((r) => ff.stdin.once("drain", r));
  if (i % 60 === 0) process.stdout.write(`frame ${i}/${total}\n`);
}
ff.stdin.end();
await new Promise((res, rej) => ff.on("close", (code) => (code === 0 ? res() : rej(new Error(`ffmpeg exited ${code}`)))));
await browser.close();
console.log(`wrote ${outFile}`);
