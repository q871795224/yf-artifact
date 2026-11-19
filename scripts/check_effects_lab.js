// Run through playwright-cli run-code after opening the local effects workbench.
async function checkEffectsLab(page) {
  const report = { checks: [], layouts: [], errors: [], remoteRequests: [] };
  const check = (value, message) => { if (!value) throw new Error(message); report.checks.push(message); };
  page.on("pageerror", (error) => report.errors.push(error.message));
  const origin = new URL(page.url()).origin;
  page.on("request", (request) => { if (/^https?:/.test(request.url()) && new URL(request.url()).origin !== origin) report.remoteRequests.push(request.url()); });
  const previousStorage = await page.evaluate(() => localStorage.getItem("yf-artifact-effects-lab-v1"));
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.reload();
  check(page.url().startsWith("file:") || new URL(page.url()).hostname === "127.0.0.1", "The workbench runs locally from a file or background service");
  const catalog = await page.evaluate(() => Object.entries(ArtifactFX.catalog).map(([kind, entry]) => ({ kind, name: entry.name })));
  check(catalog.length === 13, "All thirteen effect types are available");
  check(await page.locator("#effect-count").textContent() === "13", "The library displays the current effect count");
  const scrub = (fraction) => page.locator("#timeline").evaluate((input, f) => { input.value = Number(input.max) * f; input.dispatchEvent(new Event("input", { bubbles: true })); }, fraction);
  const frame = () => page.evaluate(() => document.getAnimations().map((a) => {
    const style = getComputedStyle(a.effect.target);
    return { time: a.currentTime, opacity: style.opacity, transform: style.transform, filter: style.filter };
  }));
  for (const entry of catalog) {
    await page.locator(`[data-kind="${entry.kind}"]`).click();
    check(await page.locator("#effect-name").innerText() === entry.name, `${entry.kind} can be selected`);
    check(await page.locator(`#effect-layer [data-effect="${entry.kind}"]`).count() === 1, `${entry.kind} builds its preview`);
    check(await page.evaluate(() => document.getAnimations().every((a) => a.playState === "paused")), `${entry.kind} starts as a paused keyframe`);
    await scrub(0.5); const middle = await frame();
    await scrub(1); await scrub(0); await scrub(0.5);
    check(JSON.stringify(await frame()) === JSON.stringify(middle), `${entry.kind} can scrub backward and reproduce the same keyframe`);
  }
  await page.locator('[data-kind="clash"]').click();
  const visibleHealth = () => page.evaluate(() => Array.from(document.querySelectorAll(".clash-health span"))
    .filter((el) => getComputedStyle(el).opacity === "1").map((el) => el.textContent));
  await scrub(0.36);
  check(JSON.stringify(await visibleHealth()) === JSON.stringify(["♥ 4", "♥ 7"]), "Clash preserves both health values before impact");
  await scrub(0.45);
  check(JSON.stringify(await visibleHealth()) === JSON.stringify(["♥ 0", "♥ 3"]), "Clash changes both health values on impact");
  await scrub(1);
  const clashOpacity = (id) => page.locator(`#${id}-unit .clash-piece`).evaluate((el) => getComputedStyle(el).opacity);
  check(await clashOpacity("source") === "1" && await clashOpacity("target") === "0", "The defeated clash unit fades while the survivor returns");
  await scrub(0);
  check(await clashOpacity("target") === "1", "Rewinding restores the defeated clash unit");
  for (const kind of ["lightning", "stun", "shield", "aura", "death", "tower"]) {
    await page.locator(`[data-kind="${kind}"]`).click();
    await scrub(0.25); const early = await frame();
    await scrub(0.7);
    check(JSON.stringify((await frame()).map(({ time, ...visual }) => visual)) !== JSON.stringify(early.map(({ time, ...visual }) => visual)), `${kind} changes visually over time`);
    const preset = JSON.parse(await page.locator("#preset-json").textContent());
    await page.locator('[data-kind="melee"]').click();
    await page.locator("#import-file").setInputFiles({ name: `${kind}.json`, mimeType: "application/json", buffer: Buffer.from(JSON.stringify(preset)) });
    await page.waitForFunction((k) => document.querySelector(`#effect-layer [data-effect="${k}"]`), kind);
    check(JSON.parse(await page.locator("#preset-json").textContent()).kind === kind, `${kind} presets import correctly`);
  }
  await page.locator('[data-kind="death"]').click(); await scrub(1);
  check(await page.locator("#target-unit").evaluate((el) => Number(getComputedStyle(el).opacity)) === 0, "A completed death animation hides the target");
  await scrub(0);
  check(await page.locator("#target-unit").evaluate((el) => Number(getComputedStyle(el).opacity)) === 1, "Rewinding death restores the target");
  await page.locator('[data-kind="aura"]').click();
  await page.locator("#direction").selectOption("N");
  check(await page.locator('#effect-layer [data-effect="aura"] rect').count() === 8, "Aura highlights all eight neighboring cells");
  await page.locator('[data-kind="tower"]').click();
  check((await page.locator("#source-unit img").getAttribute("src")).endsWith("/1000.webp"), "Tower attacks use the local tower artwork");
  await page.setViewportSize({ width: 390, height: 844 });
  const sizes = {};
  for (const columns of [6, 5]) {
    await page.locator("#columns").selectOption(String(columns));
    check(await page.locator(".preview-cell").count() === columns * 8, `${columns} columns create eight complete rows`);
    check(await page.locator("#effect-layer").getAttribute("viewBox") === `0 0 ${columns * 100} 800`, `${columns} columns use matching effect coordinates`);
    check(await page.locator(".home-fountain").count() === columns, `${columns} columns preserve the fountain row`);
    sizes[columns] = await page.locator("#source-unit").evaluate((el) => el.getBoundingClientRect().width);
    for (const entry of catalog) {
      await page.locator(`[data-kind="${entry.kind}"]`).click();
      for (const direction of ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]) {
        await page.locator("#direction").selectOption(direction);
        check(await page.locator("#source-unit").count() === 1 && await page.locator("#target-unit").count() === 1, `${entry.kind} has valid targets toward ${direction} on ${columns} columns`);
      }
    }
    await page.locator("#direction").selectOption("E");
    const aligned = await page.evaluate(() => {
      const target = document.querySelector("#target-unit").getBoundingClientRect();
      const svg = document.querySelector("#effect-layer");
      const point = new DOMPoint(450, 450).matrixTransform(svg.getScreenCTM());
      return Math.hypot(point.x - target.x - target.width / 2, point.y - target.y - target.height / 2) < 2;
    });
    check(aligned, `${columns} columns align effect coordinates with the target cell`);
  }
  check(sizes[5] / sizes[6] > 1.18, "Five columns enlarge mobile units by about twenty percent");
  await page.reload();
  check(await page.locator("#columns").inputValue() === "5" && await page.locator(".preview-cell").count() === 40, "Refreshing preserves the five-column layout");
  const legacy = JSON.parse(await page.locator("#preset-json").textContent());
  delete legacy.scene.columns;
  await page.locator("#import-file").setInputFiles({ name: "legacy.json", mimeType: "application/json", buffer: Buffer.from(JSON.stringify(legacy)) });
  await page.waitForFunction(() => document.querySelectorAll(".preview-cell").length === 48);
  check(await page.locator("#columns").inputValue() === "6", "Older presets without a column count retain their six-column layout");
  await page.locator("#columns").selectOption("5");
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.locator('[data-kind="projectile"]').click();
  await page.locator("#timeline").evaluate((input) => { input.value = 200; input.dispatchEvent(new Event("input", { bubbles: true })); });
  const time = () => page.locator("#timeline").inputValue().then(Number);
  const before = await time();
  await page.locator("#next-frame").click();
  check(Math.abs(await time() - before - 1000 / 60) < 1, "Frame stepping advances by one 60fps frame");
  await page.locator("#previous-frame").click();
  check(Math.abs(await time() - before) < 1, "Backward frame stepping restores the same time");
  await page.locator("#play").click();
  await page.waitForTimeout(100);
  await page.locator("#play").click();
  const paused = await time();
  check(paused > before, "Playback actually advances the timeline");
  await page.waitForTimeout(100);
  check(await time() === paused, "Pause freezes the exact current frame");
  await page.locator("#rate").selectOption("0.5");
  check(await page.evaluate(() => document.getAnimations().every((a) => a.playbackRate === 0.5)), "Playback speed applies to every particle");
  await page.locator("#direction").selectOption("NE");
  check((await page.locator("#scene-caption").innerText()).includes("右上"), "Direction updates the preview scene");
  await page.locator("#duration").evaluate((input) => { input.value = 1400; input.dispatchEvent(new Event("input", { bubbles: true })); });
  await page.locator("#color").evaluate((input) => { input.value = "#ef7654"; input.dispatchEvent(new Event("input", { bubbles: true })); });
  await page.locator("#damage").fill("17");
  await page.locator("#preset-name").fill("浏览器验证预设");
  const saved = await page.locator("#preset-json").textContent();
  await page.locator("#save-preset").click();
  check((await page.locator("#notice").innerText()).includes("已保存"), "A named preset can be saved locally");
  await page.locator("#reset").click();
  check(await page.locator("#color").inputValue() !== "#ef7654", "Reset restores the effect defaults");
  await page.locator("#load-preset").click();
  check(await page.locator("#preset-json").textContent() === saved, "Loading a saved preset restores all parameters and scene settings");
  const downloadPromise = page.waitForEvent("download");
  await page.locator("#export-preset").click();
  const download = await downloadPromise;
  await download.saveAs("output/playwright/effects-lab-export.json");
  check(download.suggestedFilename() === "artifact-fx-projectile.json", "The current effect can be exported as a JSON file");
  await page.locator('[data-kind="heal"]').click();
  await page.locator("#import-file").setInputFiles("output/playwright/effects-lab-export.json");
  await page.waitForFunction(() => document.querySelector("#effect-name").textContent === "远程弹道");
  check(await page.locator("#preset-json").textContent() === saved, "Exported JSON imports without losing data");
  await page.reload();
  check(await page.locator("#preset-json").textContent() === saved, "Refreshing restores the local working preset");
  for (const bad of [{ ...JSON.parse(saved), kind: "__proto__" }, { ...JSON.parse(saved), parameters: { duration: 999999 } }, { ...JSON.parse(saved), scene: { direction: "N", distance: 2, columns: 4 } }]) {
    await page.locator("#import-file").setInputFiles({ name: "invalid-preset.json", mimeType: "application/json", buffer: Buffer.from(JSON.stringify(bad)) });
    await page.waitForFunction(() => document.querySelector("#notice").textContent.includes("导入失败"));
    check(await page.locator("#preset-json").textContent() === saved, "An invalid import leaves the working preset intact");
  }
  await page.locator("#duration").evaluate((input) => { input.value = 200; input.dispatchEvent(new Event("input", { bubbles: true })); });
  await page.locator("#rate").selectOption("1");
  await page.locator("#loop").check();
  await page.locator("#replay").click();
  await page.waitForTimeout(550);
  check(await page.locator("#play").innerText() === "暂停", "Looping continues past the end of one playback");
  await page.locator("#loop").uncheck();
  await page.waitForTimeout(300);
  check(await page.locator("#play").innerText() === "播放", "Disabling loop allows playback to finish");
  for (const [width, height] of [[1440, 900], [1024, 768], [390, 844], [320, 568]]) {
    await page.setViewportSize({ width, height });
    for (const columns of [5, 6]) {
      await page.locator("#columns").selectOption(String(columns));
      const metrics = await page.evaluate(() => ({
        width: innerWidth, scrollWidth: document.documentElement.scrollWidth,
        boardWidth: document.querySelector("#preview-board").getBoundingClientRect().width,
        broken: [...document.images].filter((i) => !i.complete || !i.naturalWidth).length,
      }));
      check(metrics.scrollWidth <= width && metrics.boardWidth > 150, `The ${columns}-column preview fits a ${width}px viewport`);
      check(!metrics.broken, `All local images load at ${width}px`);
      report.layouts.push({ ...metrics, columns });
    }
  }
  check(!report.errors.length, "No browser runtime errors");
  check(!report.remoteRequests.length, "The local workbench makes no external network requests");
  await page.evaluate((value) => {
    if (value === null) localStorage.removeItem("yf-artifact-effects-lab-v1");
    else localStorage.setItem("yf-artifact-effects-lab-v1", value);
  }, previousStorage);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.reload();
  await page.screenshot({ path: "output/playwright/effects-lab-desktop.png" });
  return report;
}
