// Run with playwright-cli run-code against a static build in Chrome.
async function checkGameFeedback(page) {
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.setViewportSize({ width: 390, height: 844 });
  const opening = await page.evaluate(() => api("/api/games", { seed: 13 }));
  await page.evaluate((id) => localStorage.setItem("yf-artifact-match-v1", id), opening.game_id);
  await page.reload();
  await page.waitForFunction(() => view && !busy && view.version === 0);
  const report = { fissure: false, combat: false, cachedRuntimeFiles: 0, offlineRuntimeBytes: [] };
  await page.screenshot({ path: "output/playwright/feedback-arrows.png" });
  const hero = opening.state.units.find((u) => u.id === 10033);
  await page.locator(`.cell[data-unit="${hero.key}"]`).click();
  if (!(await page.locator(".reachable").count())) throw new Error("Hero click did not open movement");
  await page.locator('[data-action="skill"]').click();
  await page.locator(`.cell[data-row="${hero.row - 1}"][data-col="${hero.col}"]`).click();
  await page.locator('[data-effect="fissure"]').waitFor({ state: "attached" });
  report.fissure = true;
  await page.waitForTimeout(150);
  await page.screenshot({ path: "output/playwright/feedback-fissure.png" });
  await page.waitForFunction(() => !busy);
  for (let i = 0; i < 20 && !report.combat; i++) {
    await page.locator("#pass-button").click();
    await page.waitForFunction(() => view.phase === "combat" || !busy);
    if (await page.evaluate(() => view.phase === "combat")) {
      if (!(await page.locator('[data-effect="melee"], [data-effect="projectile"], [data-effect="tower"]').count())) throw new Error("Combat had no visible attacks");
      report.combat = true;
      await page.waitForTimeout(150);
      await page.screenshot({ path: "output/playwright/feedback-combat.png" });
    }
    await page.waitForFunction(() => !busy);
  }
  if (!report.combat) throw new Error("Never reached combat");
  const validTargets = await page.evaluate(() => {
    const rays = [...document.querySelectorAll(".target-ray")];
    const expected = view.units.filter((u) => u.target && !u.stunned);
    return rays.length === expected.length && rays.every((p) => expected.some((u) => u.key === p.dataset.origin && u.target === p.dataset.target));
  });
  if (!validTargets) throw new Error("Attack indicators diverged from the engine targets");
  report.cachedRuntimeFiles = await page.evaluate(async () => {
    const key = (await caches.keys()).find((k) => k.startsWith("yf-artifact-runtime:"));
    return key ? (await (await caches.open(key)).keys()).length : 0;
  });
  if (report.cachedRuntimeFiles < 5) throw new Error("The full pinned runtime was not cached");
  const client = await page.context().newCDPSession(page);
  await client.send("Network.enable");
  await client.send("Network.emulateNetworkConditions", { offline: true, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
  try {
    report.offlineRuntimeBytes = await page.evaluate(async () => {
      const result = [];
      for (const name of ["pyodide.asm.wasm", "python_stdlib.zip"]) {
        const response = await fetch(new URL(`../vendor/pyodide/${name}`, location.href), { cache: "no-store" });
        if (!response.ok) throw new Error("Runtime cache returned an error");
        result.push((await response.arrayBuffer()).byteLength);
      }
      return result;
    });
  } finally {
    await client.send("Network.emulateNetworkConditions", { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
    await client.detach();
  }
  if (report.offlineRuntimeBytes[0] < 9000000 || report.offlineRuntimeBytes[1] < 2000000) throw new Error("Cached runtime is incomplete");
  const version = await page.evaluate(() => view.version);
  await page.reload();
  await page.waitForFunction((v) => view && !busy && view.version === v, version);
  return report;
}
