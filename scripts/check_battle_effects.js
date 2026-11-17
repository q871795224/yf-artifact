// Execute with playwright-cli run-code against the static V0.2 game.
async function checkBattleEffects(page) {
  await page.emulateMedia({ reducedMotion: "no-preference" });
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const plan = await (await page.request.get(new URL("../scripts/fixtures/playthrough-13.json", page.url()).href)).json();
  await page.evaluate(async (seed) => {
    const packet = await api("/api/games", { seed });
    localStorage.setItem("yf-artifact-match-v1", packet.game_id);
  }, plan.seed);
  await page.reload();
  await page.waitForFunction(() => view && !busy && view.version === 0);
  await page.evaluate(() => {
    window.observedBattleEffects = {};
    const observer = new MutationObserver((records) => {
      for (const record of records) for (const node of record.addedNodes) {
        const kind = node.dataset?.effect;
        if (kind) window.observedBattleEffects[kind] = (window.observedBattleEffects[kind] || 0) + 1;
      }
    });
    observer.observe(document.querySelector("#battle-effects"), { childList: true });
  });
  for (const step of plan.steps) {
    const state = await page.evaluate(async (step) => {
      await perform(step.id);
      return { version: view.version, busy, columns: view.columns,
        bounded: view.units.every((u) => u.row >= 0 && u.row < 8 && u.col >= 0 && u.col < 5),
        activeEffects: document.querySelectorAll("#battle-effects > [data-effect]").length };
    }, step);
    if (state.version !== step.version + 1 || state.busy || state.columns !== 5 || !state.bounded || state.activeEffects) {
      throw new Error(`Animation transition failed at command ${step.version}: ${JSON.stringify(state)}`);
    }
  }
  const report = await page.evaluate(() => ({ effects: window.observedBattleEffects,
    phase: view.phase, round: view.round, winner: view.winner, commands: view.version, release: view.release }));
  for (const kind of ["fissure", "melee", "projectile", "impact", "heal", "summon", "lightning", "stun", "shield", "aura", "death", "tower"]) {
    if (!report.effects[kind]) throw new Error(`The full match did not play ${kind}`);
  }
  if (report.phase !== "finished" || report.winner !== plan.winner || report.round !== plan.round) throw new Error("Animated playback diverged from the engine replay");
  if (errors.length) throw new Error(errors.join("\n"));
  await page.screenshot({ path: "output/playwright/v02-animated-finish.png" });
  return { ...report, errors };
}
