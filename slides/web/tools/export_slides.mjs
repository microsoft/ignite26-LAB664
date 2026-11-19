// Authoring only: render lossless slide images using an installed Chromium browser.
import { spawn } from "node:child_process";
import { mkdtemp, readFile, mkdir, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { setTimeout as delay } from "node:timers/promises";

const [browserPath, previewUrl = "http://127.0.0.1:8766/"] = process.argv.slice(2);
if (!browserPath) throw new Error("Usage: node export_slides.mjs <installed-browser-path> [local-preview-url]");
const baseUrl = new URL(previewUrl);
if (!["127.0.0.1", "localhost"].includes(baseUrl.hostname)) {
  throw new Error("Slide export requires a local preview URL.");
}
const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const profile = await mkdtemp(path.join(tmpdir(), "ignite-slide-export-"));
let socket;
let stderr = "";
let launchError;
const browser = spawn(browserPath, [
  "--headless=new", "--remote-debugging-port=0", `--user-data-dir=${profile}`,
  "--no-first-run", "--no-default-browser-check", "about:blank",
], { stdio: ["ignore", "ignore", "pipe"] });
browser.stderr.on("data", chunk => { stderr = (stderr + chunk).slice(-4000); });
browser.on("error", error => { launchError = error; });

try {
  let port;
  const deadline = Date.now() + 15000;
  while (!port && Date.now() < deadline) {
    if (launchError) throw launchError;
    if (browser.exitCode !== null) throw new Error(`Browser exited: ${stderr}`);
    try {
      port = (await readFile(path.join(profile, "DevToolsActivePort"), "utf8")).split("\n")[0];
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
      await delay(100);
    }
  }
  if (!port) throw new Error(`Browser debugging endpoint did not become ready: ${stderr}`);
  const targetResponse = await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: "PUT" });
  if (!targetResponse.ok) throw new Error(`Cannot create browser target: HTTP ${targetResponse.status}`);
  const target = await targetResponse.json();
  socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, { once: true });
    socket.addEventListener("error", reject, { once: true });
  });
  let nextId = 0;
  const pending = new Map();
  socket.addEventListener("message", event => {
    const message = JSON.parse(event.data);
    const entry = pending.get(message.id);
    if (!entry) return;
    clearTimeout(entry.timer);
    pending.delete(message.id);
    if (message.error) entry.reject(new Error(JSON.stringify(message.error)));
    else entry.resolve(message.result);
  });
  const call = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++nextId;
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`Browser command timed out: ${method}`));
    }, 30000);
    pending.set(id, { resolve, reject, timer });
    socket.send(JSON.stringify({ id, method, params }));
  });
  await call("Page.enable");
  await call("Emulation.setDeviceMetricsOverride", {
    width: 1920, height: 1080, deviceScaleFactor: 1.5, mobile: false,
  });
  for (const slug of ["lab664", "brk245"]) {
    const content = JSON.parse(await readFile(path.join(site, slug, "reading.json"), "utf8"));
    const slides = content.sections.flatMap(section => section.slides);
    const destination = path.join(site, slug, "assets", "slides");
    await mkdir(destination, { recursive: true });
    for (const number of slides) {
      const url = new URL(`${slug}/presentation.html?thumb=${number}`, baseUrl);
      const navigated = await call("Page.navigate", { url: url.href });
      if (navigated.errorText) throw new Error(navigated.errorText);
      let ready = false;
      const slideDeadline = Date.now() + 15000;
      while (!ready && Date.now() < slideDeadline) {
        const status = await call("Runtime.evaluate", {
          expression: `location.href === ${JSON.stringify(url.href)} && document.readyState === "complete" && window.deck?.slide === ${number}`,
          returnByValue: true,
        });
        ready = status.result?.value === true;
        if (!ready) await delay(100);
      }
      if (!ready) throw new Error(`${slug} slide ${number} did not finish loading.`);
      const rendered = await call("Runtime.evaluate", {
        expression: `(async () => {
          document.querySelectorAll(".deck-reading-links").forEach(el => el.remove());
          await document.fonts.ready;
          const slide = document.querySelector(".slide.active");
          for (const video of slide.querySelectorAll("video")) {
            video.pause();
            const poster = video.poster || video.dataset.poster;
            if (!poster) throw new Error("Video has no still image");
            const image = document.createElement("img");
            image.src = poster;
            image.style.cssText = video.style.cssText;
            image.style.position = "absolute";
            if (!image.style.width) image.style.width = "100%";
            if (!image.style.height) image.style.height = "100%";
            video.replaceWith(image);
          }
          document.querySelectorAll(".vplay,.vbar,.vmute").forEach(el => el.remove());
          await Promise.all([...slide.querySelectorAll("img")].map(image => image.decode()));
          await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
          return { width: innerWidth, height: innerHeight };
        })()`,
        awaitPromise: true, returnByValue: true,
      });
      if (rendered.exceptionDetails) throw new Error(JSON.stringify(rendered.exceptionDetails));
      const screenshot = await call("Page.captureScreenshot", {
        format: "png", captureBeyondViewport: false,
      });
      const filename = path.join(destination, `${String(number).padStart(2, "0")}.png`);
      await writeFile(filename, Buffer.from(screenshot.data, "base64"));
      console.log(`${slug}/${String(number).padStart(2, "0")}.png (2880 x 1620)`);
    }
  }
} finally {
  if (socket) socket.close();
  if (browser.exitCode === null && browser.pid) {
    const exited = new Promise(resolve => browser.once("exit", resolve));
    browser.kill();
    await exited;
  }
  await rm(profile, { recursive: true, force: true, maxRetries: 3, retryDelay: 200 });
}
