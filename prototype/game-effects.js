/* Translate authoritative state changes into the same effects used by the local lab. */
"use strict";
(() => {
  const point = (u) => ({ x: (u.col + 0.5) * 100, y: (u.row + 0.5) * 100 });
  const fortPoint = (state, team) => point(state.forts[team]);
  const cell = (u) => document.querySelector(`.cell[data-unit="${u.key}"]`);
  const scene = (from, to, actor, target, extra = {}) => ({ from, to, actorElement: actor && cell(actor), targetElement: target && cell(target), ...extra });
  const teamColor = (team) => team === "ally" ? "#75d49a" : "#ee8585";
  const area = (u, columns) => {
    const cells = [];
    for (let dr = -1; dr <= 1; dr++) for (let dc = -1; dc <= 1; dc++) {
      const row = u.row + dr, col = u.col + dc;
      if ((dr || dc) && row >= 0 && row < 8 && col >= 0 && col < columns) cells.push({ row, col });
    }
    return cells;
  };
  async function play(entries, duration) {
    if (!entries.length || matchMedia("(prefers-reduced-motion: reduce)").matches) return false;
    const layer = document.querySelector("#battle-effects"), effects = [];
    try {
      for (const entry of entries) {
        const effect = ArtifactFX.create(layer, entry.kind, entry.scene, { duration, damage: 0, glow: 2, ...entry.parameters });
        effects.push(effect); effect.play();
      }
      await new Promise((resolve) => setTimeout(resolve, duration + 30));
    } finally { effects.forEach((effect) => effect.dispose()); }
    return true;
  }
  async function combat(state) {
    const entries = [];
    for (const unit of state.units) {
      if (!unit.target || unit.stunned || unit.canAttack === false) continue;
      const victim = state.units.find((u) => u.key === unit.target);
      const fortTeam = unit.target === "AF" ? 0 : unit.target === "BF" ? 1 : null;
      const to = victim ? point(victim) : fortTeam !== null ? fortPoint(state, fortTeam) : null;
      if (to) entries.push({ kind: unit.range > 1 ? "projectile" : "melee", scene: scene(point(unit), to, unit, victim), parameters: { color: teamColor(unit.team) } });
    }
    for (const fort of state.forts) {
      const victim = state.units.find((u) => u.key === fort.target);
      if (fort.ready && fort.attack && victim) entries.push({ kind: "tower", scene: scene(fortPoint(state, fort.team), point(victim), null, victim) });
    }
    document.querySelector(".board-frame").classList.add("is-fighting");
    try { await play(entries, 650); }
    finally { document.querySelector(".board-frame").classList.remove("is-fighting"); }
  }
  async function action(previous, next, command) {
    if (!previous || !command) return false;
    const actor = previous.units.find((u) => u.key === command.actor);
    const target = previous.units.find((u) => u.key === command.target);
    if (command.kind === "stun" && actor) {
      const cells = [1, 2].map((n) => ({ row: actor.row + command.dr * n, col: actor.col + command.dc * n }))
        .filter((p) => p.row >= 0 && p.row < 8 && p.col >= 0 && p.col < next.columns);
      if (!cells.length) return false;
      return play([{ kind: "fissure", scene: scene(point(actor), point(cells.at(-1)), actor, target, { cells }) }], 600);
    }
    if (command.kind === "lion" && actor && target) return play([{ kind: "lightning", scene: scene(point(actor), point(target), actor, target), parameters: { color: "#e49b91" } }], 480);
    if (command.kind !== "card") return false;
    const card = CARDS[command.card_id];
    const caster = previous.units.find((u) => u.hero && u.team === "ally" && card?.colors.some((c) => CARDS[u.id]?.colors.includes(c)));
    // AI card metadata identifies its side explicitly, independent of hidden hand contents.
    const team = command.team === 1 ? "enemy" : "ally";
    const source = team === "ally" ? caster : previous.units.find((u) => u.hero && u.team === team && card?.colors.some((c) => CARDS[u.id]?.colors.includes(c)));
    if (!source) return false;
    if ([10352, 10353].includes(command.card_id)) return play([{ kind: "lightning", scene: scene(point(source), fortPoint(previous, team === "ally" ? 1 : 0), source, null) }], 500);
    const victims = [10402, 10412].includes(command.card_id) ? previous.units.filter((u) => u.team !== team)
      : [10270, 10354, 10410].includes(command.card_id) && target ? [target] : [];
    return play(victims.map((u) => ({ kind: command.card_id === 10412 ? "lightning" : "projectile", scene: scene(point(source), point(u), source, u) })), 480);
  }
  function deaths(previous, next) {
    if (!previous) return Promise.resolve(false);
    return play(previous.units.filter((u) => !next.units.some((v) => v.key === u.key)).map((u) => ({ kind: "death", scene: scene(point(u), point(u), null, u) })), 520);
  }
  function changes(previous, next) {
    if (!previous) return Promise.resolve(false);
    const entries = [];
    for (const u of next.units) {
      const old = previous.units.find((p) => p.key === u.key);
      const location = scene(point(u), point(u), null, u);
      if (!old || old.team !== u.team) entries.push({ kind: "summon", scene: location });
      else {
        if (u.hp !== old.hp) entries.push({ kind: u.hp > old.hp ? "heal" : "impact", scene: location, parameters: { damage: Math.abs(u.hp - old.hp) } });
        if (u.armor > old.armor) entries.push({ kind: "shield", scene: location });
      }
      if (old && u.level > old.level) entries.push({ kind: "aura", scene: location, parameters: { color: "#efcf76" } });
      if (u.stunned && !old?.stunned) entries.push({ kind: "stun", scene: location });
      if ([10014, 10036].includes(u.id) && (!old || old.row !== u.row || old.col !== u.col || previous.round !== next.round)) {
        entries.push({ kind: "aura", scene: { ...location, areaCells: area(u, next.columns) } });
      }
    }
    return play(entries, 600);
  }
  window.ArtifactBattleFX = Object.freeze({ combat, action, deaths, changes });
})();
