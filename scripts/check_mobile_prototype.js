// Execute with playwright-cli run-code against the running game server.
async function checkMobilePrototype(page) {
  const report = { checks: [], layouts: [], errors: [], playedCommands: 0 };
  const check = (condition, message) => {
    if (!condition) throw new Error(message);
    report.checks.push(message);
  };
  page.on("pageerror", (error) => report.errors.push(error.message));
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 390, height: 844 });
  const planResponse = await page.request.get(
    new URL("../scripts/fixtures/playthrough-13.json", page.url()).href,
  );
  const plan = await planResponse.json();
  const initial = await page.evaluate(
    (seed) => api("/api/games", { seed }),
    plan.seed,
  );
  await page.evaluate(
    (id) => localStorage.setItem("yf-artifact-match-v1", id),
    initial.game_id,
  );
  await page.reload();
  await page.waitForFunction(() => view && !busy && view.version === 0);
  check(
    (await page.locator(".cell").count()) === 48,
    "The full 6×8 board renders",
  );
  check(
    (await page.locator(".cell.hero").count()) === 4,
    "The match starts with two heroes per side",
  );
  check(
    (await page.locator("#tab-cards span").innerText()) === "5",
    "Five ordinary cards are dealt",
  );
  check(
    (await page.locator("#tab-items span").innerText()) === "1",
    "One item is dealt at the opening",
  );
  check(
    (await page.locator("#mana-value").innerText()) === "1 / 1",
    "Round one has one mana",
  );

  await page.getByRole("button", { name: "对局菜单", exact: true }).click();
  await page.locator('[data-menu="help"]').click();
  check(
    (await page.locator("#detail-body").innerText()).includes("双方连续让过"),
    "Rules explain alternating actions and combat",
  );
  await page.locator("#close-detail").click();
  await page.locator("#enemy-info").click();
  check(
    (await page.locator(".roster-unit").count()) === 6,
    "Roster shows all six heroes, including pending deployments",
  );
  check(
    (await page.locator(".roster-unit.waiting").count()) === 2,
    "The third hero on each side waits for round two",
  );
  await page.locator("#close-detail").click();
  await page.locator(".hand-card").first().click();
  await page.locator(".detail-art").evaluate((img) => img.decode());
  check(
    await page.locator(".detail-art").evaluate((img) => img.naturalWidth > 0),
    "Card details load original Chinese card art",
  );
  await page.screenshot({ path: "output/playwright/live-card-detail.png" });
  await page.locator("#close-detail").click();

  await page.locator('.cell.hero[data-team="ally"]').first().click();
  check(await page.locator(".reachable").count() > 0, "Tapping an allied hero directly reveals legal movement");
  check(await page.locator('[data-action="skill"]').isVisible(), "Skills remain available while choosing movement");
  check(await page.locator('.target-ray').count() > 0, "Attack intentions are visible without selecting a target");
  check(
    await page.locator(".reachable").evaluateAll((cells) =>
      cells.every((cell) => {
        const r = cell.getBoundingClientRect();
        return cell.contains(
          document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2),
        );
      }),
    ),
    "Every legal movement square is directly touchable, including the fountain",
  );
  await page.getByRole("button", { name: "取消", exact: true }).click();
  check(
    await page.evaluate(() => view.version === 0 && mode === null),
    "Cancelling target selection does not consume an action",
  );

  for (const [width, height] of [
    [320, 568],
    [375, 667],
    [390, 844],
    [430, 932],
    [1440, 900],
  ]) {
    await page.setViewportSize({ width, height });
    const metrics = await page.evaluate(async () => {
      await document.fonts.ready;
      await Promise.all(
        [...document.images].map((i) => i.decode().catch(() => {})),
      );
      const board = document.querySelector("#board").getBoundingClientRect();
      const footer = document
        .querySelector(".resource-bar")
        .getBoundingClientRect();
      return {
        width: innerWidth,
        height: innerHeight,
        scrollWidth: document.documentElement.scrollWidth,
        scrollHeight: document.documentElement.scrollHeight,
        board: {
          x: board.x,
          y: board.y,
          width: board.width,
          height: board.height,
        },
        cellWidth: document.querySelector(".cell").getBoundingClientRect()
          .width,
        footerBottom: footer.bottom,
        broken: [...document.images]
          .filter((i) => !i.naturalWidth)
          .map((i) => i.src),
      };
    });
    check(
      metrics.scrollWidth <= width && metrics.scrollHeight <= height,
      `The game fits ${width}×${height}`,
    );
    check(
      metrics.board.x >= 0 &&
        metrics.board.x + metrics.board.width <= width &&
        metrics.board.y + metrics.board.height <= height,
      `All 48 cells remain visible at ${width}×${height}`,
    );
    check(
      metrics.cellWidth >= 30 && metrics.footerBottom <= height + 1,
      `Units and footer remain usable at ${width}×${height}`,
    );
    check(
      !metrics.broken.length,
      `All original images load at ${width}×${height}`,
    );
    report.layouts.push(metrics);
    await page.screenshot({
      path: `output/playwright/live-viewport-${width}.png`,
    });
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: "output/playwright/live-opening.png" });
  let detailChecked = false,
    reloadChecked = false,
    damageChecked = false;
  for (const step of plan.steps) {
    await page.waitForFunction(() => !busy);
    const before = await page.evaluate(() => ({
      version: view.version,
      round: view.round,
      phase: view.phase,
    }));
    check(
      before.version === step.version,
      `Command ${step.version} starts at its expected revision`,
    );
    if (step.kind === "next_round" || step.kind === "pass") {
      await page.locator("#pass-button").click();
    } else if (
      step.kind === "move" ||
      step.kind === "stun" ||
      step.kind === "lion" ||
      step.kind === "chen"
    ) {
      await page.locator(`.cell[data-unit="${step.actor}"]`).click();
      if (step.kind !== "move") await page.locator('[data-action="skill"]').click();
      if (step.kind === "stun") {
        const pos = await page
          .locator(`.cell[data-unit="${step.actor}"]`)
          .evaluate((el) => ({
            row: Number(el.dataset.row),
            col: Number(el.dataset.col),
          }));
        await page
          .locator(
            `.cell[data-row="${pos.row + step.dr}"][data-col="${pos.col + step.dc}"]`,
          )
          .click();
      } else if (step.row !== undefined) {
        await page
          .locator(`.cell[data-row="${step.row}"][data-col="${step.col}"]`)
          .click();
      } else await page.locator(`.cell[data-unit="${step.target}"]`).click();
    } else if (step.kind === "card" || step.kind === "item") {
      await page
        .locator(step.kind === "card" ? "#tab-cards" : "#tab-items")
        .click();
      await page.locator(`.hand-card[data-index="${step.index}"]`).click();
      check(
        await page.locator("#play-card").isEnabled(),
        `The engine's legal ${step.kind} is actionable in the UI`,
      );
      await page.locator("#play-card").click();
      if (step.row !== undefined)
        await page
          .locator(`.cell[data-row="${step.row}"][data-col="${step.col}"]`)
          .click();
      else if (
        !["all", "self", "draw", "ticket", "improvement", "fort"].includes(
          step.target,
        )
      )
        await page.locator(`.cell[data-unit="${step.target}"]`).click();
      detailChecked = true;
    } else if (step.kind === "horn" || step.kind === "blade") {
      await page.locator(`.cell[data-unit="${step.actor}"]`).click();
      await page.locator('[data-action="equipment"]').click();
      await page.locator(`[data-gear-kind="${step.kind}"]`).click();
      if (step.kind === "horn")
        await page
          .locator(`.cell[data-row="${step.row}"][data-col="${step.col}"]`)
          .click();
    } else throw new Error("Unhandled test action " + step.kind);
    await page.waitForFunction(
      (version) => view.version === version + 1 && !busy,
      step.version,
      { timeout: 15000 },
    );
    report.playedCommands++;
    const after = await page.evaluate(() => ({
      round: view.round,
      phase: view.phase,
      version: view.version,
      heroes: view.heroes,
      log: view.log,
    }));
    check(
      (await page.locator("#pass-button").innerText()).includes(
        after.phase === "round_end"
          ? "下一回合"
          : after.phase === "finished"
            ? "查看结果"
            : "让过",
      ),
      `Command ${step.version} displays the correct phase control`,
    );
    if (after.phase === "round_end" && !damageChecked) {
      await page.screenshot({
        path: "output/playwright/live-combat-result.png",
      });
      damageChecked = true;
    }
    if (after.round >= 3 && !reloadChecked) {
      await page.reload();
      await page.waitForFunction(
        (version) => view && view.version === version && !busy,
        after.version,
      );
      check(
        (await page.evaluate(() => view.round)) >= 3,
        "Refreshing resumes the same match and round",
      );
      reloadChecked = true;
    }
    if (after.round === 8 && step.kind === "next_round")
      await page.screenshot({ path: "output/playwright/live-round-eight.png" });
  }
  check(
    detailChecked,
    "The complete playthrough includes real cards and equipment",
  );
  const end = await page.evaluate(() => ({
    phase: view.phase,
    winner: view.winner,
    round: view.round,
    version: view.version,
    forts: view.forts,
    stats: view.stats,
  }));
  check(
    end.phase === "finished" &&
      end.winner === plan.winner &&
      end.round === plan.round,
    "A complete human-controlled browser match reaches the expected base-destruction victory",
  );
  check(
    await page.locator(".result-title").isVisible(),
    "Victory displays a result screen",
  );
  await page.screenshot({ path: "output/playwright/live-victory.png" });
  const downloadPromise = page.waitForEvent("download");
  await page.locator("#result-export").click();
  const download = await downloadPromise;
  await download.saveAs("output/playwright/browser-match-export.json");
  check(
    download.suggestedFilename().includes(`artifact-${plan.seed}-round-${plan.round}`),
    "The real match can be exported for feedback",
  );
  await page.locator("#result-new").click();
  await page.waitForFunction(() => view && view.version === 0 && !busy);
  check(
    await page.evaluate(() => view.phase === "action" && view.round === 1),
    "Starting another match resets to a real opening",
  );
  check(
    report.errors.length === 0,
    "No browser runtime errors during the complete playthrough",
  );
  report.final = end;
  return report;
}
