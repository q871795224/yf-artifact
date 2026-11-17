// Execute with playwright-cli run-code on the current local or static game.
async function checkBattleReadability(page) {
  const checks = [], errors = [];
  const check = (ok, message) => { if (!ok) throw Error(message); checks.push(message); };
  page.on("pageerror", (error) => errors.push(error.message));
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(async () => { const packet = await api("/api/games", { seed: 13 }); await applyPacket(packet); });
  const state = await page.evaluate(() => ({ forecast: view.forecast, version: view.version, units: view.units, forts: view.forts }));
  check(state.forts.every((f) => f.col === 2 && f.row === (f.team === 0 ? 7 : 0)), "Buildings occupy the fountain center cells");
  check(await page.locator(".cell.structure").count() === 2, "Both buildings are visible on the board");
  check(await page.evaluate(() => view.units.filter((u) => u.id === 1006 && u.team === "enemy").every((u) => document.querySelector(`.cell[data-unit="${u.key}"] .unit-art`).getAttribute("src") === "assets/units/dire-melee.webp")), "Enemy melee creeps use the selected Dire artwork");
  check(await page.evaluate(() => view.units.filter((u) => u.id === 1006 && u.team === "ally").every((u) => document.querySelector(`.cell[data-unit="${u.key}"] .unit-art`).getAttribute("src").endsWith("mini_image/1006.webp"))), "Allied melee creeps retain the original artwork");
  check(await page.evaluate(() => view.units.every((u) => document.querySelector(`.cell[data-unit="${u.key}"]`).classList.contains("forecast-death") === view.forecast.units[u.key].dies)), "Every death marker matches the current engine forecast");
  check(await page.evaluate(() => getComputedStyle(document.querySelector('.cell[data-team="ally"]')).borderColor === "rgb(101, 201, 144)" && getComputedStyle(document.querySelector('.cell[data-team="enemy"]')).borderColor === "rgb(231, 118, 118)"), "Allied green and enemy red borders are visible");
  const hero = state.units.find((u) => u.id === 10033);
  const tile = page.locator(`.cell[data-unit="${hero.key}"]`);
  const bounds = await tile.boundingBox();
  await page.mouse.move(bounds.x + bounds.width/2, bounds.y + 10);
  await page.mouse.down();
  await page.waitForTimeout(520);
  await page.mouse.up();
  check(await page.locator("#detail-dialog").evaluate((d) => d.open), "Long press opens current unit details");
  check(await page.evaluate(() => view.version === 0), "Inspecting a unit consumes no action");
  await page.locator("#close-detail").click();
  await tile.click();
  check(await page.evaluate(() => mode?.kind === "move"), "A normal tap still selects movement after a long press");
  check(await page.locator(".reachable").evaluateAll((cells) => cells.every((cell) => { const r = cell.getBoundingClientRect(); return cell.contains(document.elementFromPoint(r.x+r.width/2, r.y+r.height/2)); })), "Context controls leave legal destinations touchable");
  await page.locator('[data-action="skill"]').click();
  await page.locator(`.cell[data-row="${hero.row-1}"][data-col="${hero.col}"]`).click();
  await page.waitForFunction(() => view.version === 1 && !busy);
  check(await page.evaluate((before) => JSON.stringify(view.forecast) !== JSON.stringify(before), state.forecast), "A real skill and opponent response update the forecast");
  const plan = await (await page.request.get(new URL("../scripts/fixtures/playthrough-13.json", page.url()).href)).json();
  for (const step of plan.steps.slice(1, 12)) {
    await page.evaluate(async (id) => perform(id), step.id);
    if (await page.evaluate(() => view.lastOpponent?.kind === "move")) break;
  }
  check(await page.locator("#history-overlay image").count() === 1, "Opponent movement leaves an origin ghost");
  check(await page.locator("#history-overlay path[marker-end]").count() === 1, "Opponent movement leaves a separate dashed route");
  await page.screenshot({ path: "output/playwright/v03-history-ghost.png" });
  await page.locator("#enemy-info").click();
  check(await page.locator(".history-entry").count() > 0, "Opponent portrait exposes actionable history");
  await page.locator(".history-entry").first().click();
  check(await page.locator("#history-overlay image").count() === 1, "Selecting a history entry highlights its original movement");
  for (const [width, height] of [[320,568],[375,667],[390,844],[430,932],[1440,900]]) {
    await page.setViewportSize({ width, height });
    await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    check(await page.evaluate(() => { const c = document.querySelector(".cell").getBoundingClientRect(); const b = document.querySelector("#board").getBoundingClientRect(); return Math.abs(c.width-c.height) < 1 && b.left >= 0 && b.right <= innerWidth && b.bottom <= innerHeight; }), `Square board fits ${width}×${height}`);
  }
  check(errors.length === 0, "No browser runtime errors");
  return { checks, errors };
}

async function checkAssetLibrary(page) {
  const checks = [], errors = [];
  const check = (ok, message) => { if (!ok) throw Error(message); checks.push(message); };
  page.on("pageerror", (error) => errors.push(error.message));
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("http://127.0.0.1:8741/effects-lab/assets.html");
  await page.waitForFunction(() => document.querySelectorAll(".asset-tile").length === 311);
  check(await page.locator("#asset-view").inputValue() === "large_image", "All 310 original card faces and the custom unit artwork are available by default");
  check(!await page.locator("#asset-dialog").evaluate((d) => d.open), "Browsing starts with the gallery filling the page");
  await page.locator("#asset-type").selectOption("Creep");
  check(await page.locator(".asset-tile").count() === 51, "Card-type filtering exposes 50 original creeps and the custom artwork");
  await page.locator("#asset-type").selectOption("");
  await page.locator("#asset-source").selectOption("local");
  check(await page.locator(".asset-tile").count() === 60, "The 59 cached original cards and the custom artwork can be filtered locally");
  for (const [width, height] of [[1440,1000],[390,844],[320,568]]) {
    await page.setViewportSize({ width, height });
    await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    const layout = await page.evaluate(() => {
      const cards = [...document.querySelectorAll(".asset-tile")].slice(0, 12);
      const boxes = cards.map((c) => c.getBoundingClientRect());
      const separate = boxes.every((a, i) => boxes.slice(i+1).every((b) => a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top));
      const imagesFit = cards.every((c) => { const r = c.getBoundingClientRect(), image = c.querySelector(".asset-image").getBoundingClientRect(); return r.height > image.height && image.bottom <= r.bottom; });
      return separate && imagesFit && document.documentElement.scrollWidth <= innerWidth;
    });
    check(layout, `Card images and labels fit without overlap at ${width}×${height}`);
    await page.screenshot({ path: `output/playwright/asset-gallery-${width}.png` });
  }
  await page.locator("#asset-search").fill("10020");
  await page.locator('.asset-tile[data-id="10020"]').click();
  await page.locator("#asset-preview").evaluate((img) => img.decode());
  check(await page.locator("#asset-dialog").evaluate((d) => d.open) && (await page.locator("#asset-description").innerText()).includes("10020"), "Clicking a card opens an enlarged image with its identity");
  check((await page.locator("#asset-open").getAttribute("href")).endsWith("large_image/10020.png"), "The original-image link opens the full local PNG");
  await page.locator("#asset-kind").selectOption("mini_image");
  await page.locator("#asset-preview").evaluate((img) => img.decode());
  check(await page.locator("#asset-preview").evaluate((img) => img.naturalWidth === img.naturalHeight), "Card details can switch to the square portrait");
  await page.locator("#asset-copy").click();
  await page.waitForFunction(() => document.querySelector("#asset-image-status").textContent.includes("10020"));
  check((await page.locator("#asset-image-status").innerText()).includes("10020"), "The card name and ID are available to share");
  await page.keyboard.press("Escape");
  check(!await page.locator("#asset-dialog").evaluate((d) => d.open) && await page.locator("#asset-search").inputValue() === "10020", "Closing details preserves the browsing filters");
  await page.locator("#asset-search").fill("1006");
  await page.locator('.asset-tile[data-id="1006"]').click();
  await page.locator("#asset-kind").selectOption("ingame_image");
  check(await page.locator("#asset-preview").isHidden(), "Missing image variants are explicitly indicated");
  await page.locator("#asset-close").click();
  await page.locator("#asset-search").fill("夜魇");
  await page.locator('.asset-tile[data-id="dire-melee"]').click();
  await page.locator("#asset-preview").evaluate((img) => img.decode());
  check((await page.locator("#asset-title").innerText()) === "夜魇近战小兵" && (await page.locator("#asset-open").getAttribute("href")).endsWith("assets/custom/originals/dire-melee.png"), "The user-provided Dire artwork is browsable with its preserved original");
  await page.locator("#asset-close").click();
  check(errors.length === 0, "No asset-library runtime errors");
  return { checks, errors };
}
