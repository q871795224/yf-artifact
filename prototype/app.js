/* The Python match engine is authoritative. This file only presents its state. */
"use strict";
const ASSETS = "../references/artifact-classic/assets/mobile/";
const $ = (selector) => document.querySelector(selector);
const icon = (name) => `<svg aria-hidden="true"><use href="#i-${name}"/></svg>`;
const esc = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (ch) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        ch
      ],
  );
const cardName = (id) => CARDS[id]?.card_name.schinese || "未知卡牌";
// The numbered illustrations are bundled with the client so art updates leave replay rules intact.
const illustratedCardRanges = [[61001, 61012], [62001, 62019], [63001, 63006], [65001, 65022]];
const hasCustomCardArt = (id) => CARDS[id]?.custom_art
  || illustratedCardRanges.some(([first, last]) => id >= first && id <= last);
const image = (id, kind = "mini_image") => hasCustomCardArt(id)
  ? `assets/cards/${id}.webp` : `${ASSETS}${kind}/${CARDS[id]?.art_id || id}.webp`;
const isDireMelee = (u) => u.id === 1006 && u.team === "enemy";
const unitArt = (u) => u.id === 64004 ? (u.team === "enemy" ? "dire-ranged" : "radiant-ranged")
  : isDireMelee(u) ? "dire-melee" : null;
const unitImage = (u, kind = "mini_image") => {
  const art = unitArt(u);
  return art ? `assets/units/${art}.webp` : image(u.id, kind);
};
const unitName = (u) => u.id === 64004 ? (u.team === "enemy" ? "夜魇远程小兵" : "天辉远程小兵")
  : isDireMelee(u) ? "夜魇近战小兵" : cardName(u.id);
const identity = (id) => CARDS[id]?.colors?.[0] || "neutral";
const pip = (id) =>
  `<i class="color-pip identity-${identity(id)}" aria-hidden="true"></i>`;
const HEROES = {
  10020: { text: "没有额外技能，以扎实的攻击、护甲和生命正面作战。" },
  10069: {
    text: "受到普通攻击时，对攻击者造成固定 2 点普通反伤，受护甲影响；法术不触发。",
  },
  10054: {
    text: "普攻单位时，对目标两侧各一格敌人造成自身攻击一半的溅射伤害，向下取整。",
  },
  10065: { text: "己方施放蓝色法术后，对周围八格敌人造成 1 点透甲伤害。" },
  10064: {
    text: "己方每回合首次施放法术后恢复 2 法力，不超过本回合法力上限。",
  },
  10033: {
    skill: "沟壑",
    kind: "stun",
    text: "八个方向中选择一个，对该直线前两格敌人造成 2 点普通伤害（受护甲减免），并眩晕至本回合结束。冷却 4 回合，不花费法力。",
  },
  10017: {
    skill: "劝化",
    kind: "chen",
    text: "控制周围两圈内一名敌方非英雄单位。冷却 4 回合，不花费法力。",
  },
  10014: { text: "周围八格友军 +2 攻击，不包含自身。" },
  10036: { text: "自身及周围八格友军 +2 恢复，在交战时结算。" },
  10023: { text: "每回合行动前，有 50% 概率本回合 +4 攻击，结果提前公开。" },
  10047: { text: "普通攻击英雄时额外造成 4 点伤害。" },
  10060: {
    skill: "死亡之指",
    kind: "lion",
    text: "对周围两圈内一个敌人造成 8 点透甲伤害。初始冷却 4，后续逐次减少，最低 1。",
  },
};
const RULES = {
  10355:
    "在英雄周围八格或己方泉水选择空格，召唤三名 2 攻／4 血近战兵。位置不足时只召唤能容纳的数量。",
  10352: "对敌方防御塔造成 6 点伤害。",
  10402: "对所有敌方单位造成 2 点普通伤害，受护甲影响。",
  10344: "本回合己方英雄获得 4 顺势：普攻目标两侧各一格受到 4 点溅射伤害。",
  10425:
    "永久强化全部在场己方英雄：+4 攻击、+4 护甲、+4 生命，以及 4 顺势、4 反伤、4 攻城。",
  10169: "每回合开始时，己方在场单位永久 +1 攻击。多个魔霭迷雾可以叠加。",
  10223:
    "装备英雄 +2 攻击、5 攻城。攻击单位时，若敌方建筑也在射程内，额外对建筑造成 5 伤害。",
  10212: "装备英雄 +2 攻击、2 顺势。普攻目标两侧各一格受到 2 点溅射伤害。",
  10252:
    "装备英雄 +2 攻击；每次存活到交战结束，额外永久 +1 攻击，替换这件武器后失去其累计加成。",
  10256: "装备英雄 +2 攻击，普通攻击无视护甲。穿戴时解除该英雄眩晕。",
  10260:
    "装备英雄 +4 生命。主动：在合法空格召唤 14 攻／14 血、6 攻城的雷肤兽群。冷却 2 回合，不花费法力或金币。",
  10263:
    "装备英雄 +8 攻击、4 攻城。对单位造成正数战斗伤害后处决它。主动：摧毁敌方全部改良及当前普攻目标的全部装备，冷却 1 回合。",
  3006: "将一名己方英雄送回泉水空格。不会恢复它的首次两格移动机会。",
  10216:
    "随机获得本场装备池的一件装备，放入物品手牌；该装备已经付费，使用时不再花金币。",
};
const SLOT_NAMES = { Weapon: "武器", Armor: "护甲", Accessory: "饰品" };
const expansion = new URLSearchParams(location.search).get("expansion") === "1";
const storageKey = expansion ? "yf-artifact-expansion-match" : "yf-artifact-match-v04";
const deckStorageKey = expansion ? "yf-artifact-expansion-deck" : "yf-artifact-deck-v04";
let growthCatalog = null, deckDraft = null;
const cardCost = (id) => view?.cardCosts?.[id] ?? CARDS[id].mana_cost;
const skillKind = (u) => u.skillKind || HEROES[u.id]?.kind;
const skillName = (u) => ({chen:"劝化",purify:"洗礼",swap:"换位",redirect:"引导箭头",whirl:"死亡旋风",multishot:"数箭齐发"})[skillKind(u)] || "被动技能";
const statusNames = {attack_down:"减攻",unprepared:"等待装备",hex:"妖术",silence:"沉默",taunt:"嘲讽"};
const statusText = (u) => Object.keys(u.debuffs || {}).map(k => statusNames[k] || k).join("、");
if (window.ArtifactAPI.browserMode) {
  $(".prototype-note").textContent =
    "试玩版 · 进度保存在此浏览器，可直接通过互联网游玩";
}
window.addEventListener("artifact-engine-progress", (event) => {
  if (view) return;
  $("#turn-text").textContent = "准备中";
  $("#unit-panel").innerHTML =
    `<span class="idle-panel" role="status">${esc(event.detail)}</span>`;
});
window.addEventListener("artifact-save-warning", () =>
  toast("浏览器未能保存进度，刷新页面后本局可能丢失"),
);
let gameId = null,
  view = null,
  selected = null,
  tab = "cards",
  mode = null,
  busy = true,
  toastTimer,
  returnFocus,
  reviewingAction = null,
  requestSequence = 0;
const reducedMotion = () =>
  matchMedia("(prefers-reduced-motion: reduce)").matches;
const delay = (ms) =>
  new Promise((resolve) => setTimeout(resolve, reducedMotion() ? 0 : ms));
const actions = () =>
  !busy && view?.phase === "action" ? view.actions || [] : [];
const selectedUnit = () =>
  view?.units.find((u) => u.key === selected) ||
  view?.heroes.find((u) => u.key === selected);
const actionFor = (kind, actor) =>
  actions().filter(
    (a) => a.kind === kind && (actor === undefined || a.actor === actor),
  );
function savedId() {
  try {
    return localStorage.getItem(storageKey);
  } catch {
    return null;
  }
}
function rememberId(id) {
  try {
    if (id) localStorage.setItem(storageKey, id);
    else localStorage.removeItem(storageKey);
  } catch {
    /* Private browser storage may be unavailable. */
  }
}
function toast(text, cardId = null) {
  clearTimeout(toastTimer);
  $("#toast").innerHTML = `${cardId ? `<img src="${image(cardId)}" alt="${esc(cardName(cardId))}">` : ""}<span>${esc(text)}</span>`;
  $("#toast").hidden = false;
  toastTimer = setTimeout(() => ($("#toast").hidden = true), 3000);
}
async function api(path, body) {
  return window.ArtifactAPI.request(path, body);
}
function stats(u) {
  return `<span class="stat atk ${u.attack > (u.baseAttack ?? CARDS[u.id]?.attack ?? 0) ? "buffed" : ""}">${icon("sword")}${u.attack}</span><span class="stat hp">${icon("heart")}${u.hp}</span>`;
}
function targetAt(row, col) {
  if (!mode) return [];
  const unit = view.units.find((u) => u.row === row && u.col === col);
  return mode.choices.filter((a) => {
    if (mode.kind === "march") {
      if (!mode.center) return a.centers.some(([r,c]) => r === row && c === col);
      if (mode.marchUnit) return a.march.some(m => m.unit === mode.marchUnit && m.row === row && m.col === col);
      return unit && !mode.moves.includes(unit.key) && a.march.some(m => m.unit === unit.key);
    }
    if (a.kind === "stun") {
      const h = selectedUnit(),
        dr = row - h.row,
        dc = col - h.col;
      return (
        Math.max(Math.abs(dr), Math.abs(dc)) > 0 &&
        Math.max(Math.abs(dr), Math.abs(dc)) <= 2 &&
        dr === a.dr * Math.max(Math.abs(dr), Math.abs(dc)) &&
        dc === a.dc * Math.max(Math.abs(dr), Math.abs(dc))
      );
    }
    if (a.firstTarget) return unit && a.firstTarget === unit.key;
    if (a.row !== undefined) return a.row === row && a.col === col;
    return unit && a.target === unit.key;
  });
}
const unitPoint = (u) => ({ x: (u.col + 0.5) * 100, y: (u.row + 0.5) * 100 });
const fortPoint = (key) => {
  const fort = view.forts[key === "AF" ? 0 : 1];
  return unitPoint(fort);
};
function targetPoint(u) {
  const target = view.units.find((v) => v.key === u.target);
  return target ? unitPoint(target) : ["AF", "BF"].includes(u.target) ? fortPoint(u.target) : null;
}
function ray(from, to, inset = 33, side = 0) {
  const dx = to.x - from.x, dy = to.y - from.y;
  const length = Math.hypot(dx, dy);
  const pad = Math.min(inset, length * 0.3);
  const ox = length ? -dy / length * side : 0;
  const oy = length ? dx / length * side : 0;
  return `M${from.x + dx / length * pad + ox},${from.y + dy / length * pad + oy} L${to.x - dx / length * pad + ox},${to.y - dy / length * pad + oy}`;
}
function renderTargets() {
  const markers = ["ally", "enemy"].map((team) => `<marker id="arrow-${team}" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0 L8 4 L0 8z" fill="${team === "ally" ? "#75d49a" : "#ee8585"}"/></marker>`).join("");
  $("#target-overlay").innerHTML = `<defs>${markers}</defs>` + view.units.map((u) => {
    const to = targetPoint(u);
    if (!to || u.stunned) return "";
    return `<path class="target-ray ${u.team} ${u.range > 1 ? "ranged" : ""} ${u.key === selected ? "focused" : ""}" data-origin="${u.key}" data-target="${u.target}" d="${ray(unitPoint(u), to, 34, 7)}" marker-end="url(#arrow-${u.team})"><title>${esc(unitName(u) + "：" + targetDescription(u))}</title></path>`;
  }).join("");
}
function renderBoard(previous) {
  if (!view) return;
  const cells = [];
  $(".game").style.setProperty("--board-columns", view.columns);
  for (const layer of document.querySelectorAll(".board-overlay")) layer.setAttribute("viewBox", `0 0 ${view.columns * 100} 800`);
  const focus = selectedUnit();
  for (let row = 0; row < 8; row++)
    for (let col = 0; col < view.columns; col++) {
      const u = view.units.find((u) => u.row === row && u.col === col);
      const fort = view.forts.find((f) => f.row === row && f.col === col);
      const classes = [
        "cell",
        row === 0 || row === 7 ? "fountain" : "",
        row === 7 ? "ally-fountain-cell" : "",
        row === 3 ? "frontline" : "",
      ];
      let content =
        row === 0 || row === 7
          ? `<span class="fountain-glyph">${icon("fountain")}</span>`
          : "";
      if (u) {
        const prediction = !busy && view.phase === "action" ? view.forecast?.units[u.key] : null;
        classes.push(
          "occupied",
          u.hero ? "hero" : "creep",
          u.key === selected ? "selected" : "",
          u.stunned ? "stunned" : "",
          focus?.target === u.key ? "current-target" : "",
          prediction?.dies ? "forecast-death" : "",
          unitArt(u) || hasCustomCardArt(u.id) ? "custom-unit-art" : "",
        );
        content = `<img class="unit-art" src="${unitImage(u)}" alt=""><span class="unit-vignette"></span>${u.hero ? pip(u.id) : ""}${u.level ? `<span class="level-badge">Lv${u.level}</span>` : ""}${u.debuffs?.silence || u.debuffs?.hex || u.forcedTarget || u.buffs?.bkb ? `<span class="status-badge">${u.buffs?.bkb ? "BKB" : u.debuffs.hex ? "妖" : u.forcedTarget ? "嘲" : "默"}</span>` : ""}<span class="unit-stats">${stats(u)}</span>${u.armor ? `<span class="armor-badge">${icon("shield")}${u.armor}</span>` : ""}${u.stunned ? '<span class="stun-badge">晕</span>' : ""}${prediction && prediction.hp !== u.hp ? `<span class="forecast-hp" title="按当前局面交战后的生命">→ ${prediction.hp} ♥</span>` : ""}${prediction?.dies ? '<span class="forecast-cross" aria-label="预计交战阵亡">×</span>' : ""}`;
      }
      if (fort) {
        classes.push("structure", fort.ready ? "" : "structure-immune");
        const prediction = !busy && view.phase === "action" ? view.forecast?.forts.find((f) => f.team === fort.team) : null;
        if (prediction?.destroyed) classes.push("forecast-death");
        content = `<span class="structure-art">${icon(fort.stage === "tower" ? "tower" : "base")}</span><span class="structure-label">${fort.stage === "tower" ? "塔" : "基地"}${fort.ready ? "" : " · 待激活"}</span><span class="unit-stats">${stats(fort)}</span>${prediction && prediction.hp !== fort.hp ? `<span class="forecast-hp">→ ${prediction.hp} ♥</span>` : ""}${prediction?.destroyed ? '<span class="forecast-cross">×</span>' : ""}`;
      }
      const possible = targetAt(row, col);
      if (mode?.kind === "march" && mode.preview.some(([r,c]) => r === row && c === col))
        classes.push("reachable");
      if (possible.length)
        classes.push(
          mode.kind === "move"
            ? "reachable"
            : mode.kind === "skill"
              ? "skill-range"
              : "targetable",
        );
      const label = `第${row + 1}排第${col + 1}列${fort ? `，${fort.team === 0 ? "我方" : "敌方"}${fort.stage === "tower" ? "防御塔" : "基地"}，生命${fort.hp}` : u ? `，${u.team === "ally" ? "我方" : "敌方"}${unitName(u)}，攻击${u.attack}，生命${u.hp}${u.stunned ? "，眩晕" : ""}，${targetDescription(u)}` : "，空位"}`;
      cells.push(
        `<button class="${classes.filter(Boolean).join(" ")}" data-row="${row}" data-col="${col}" ${fort ? `data-fort="${fort.team}" data-team="${fort.team === 0 ? "ally" : "enemy"}"` : u ? `data-unit="${u.key}" data-team="${u.team}" aria-pressed="${u.key === selected}"` : ""} aria-label="${label}">${content}</button>`,
      );
    }
  $("#board").innerHTML = cells.join("");
  renderTargets();
  renderHistory();
}
function renderUnit() {
  const panel = $("#unit-panel"), prompt = $("#target-prompt");
  $("#global-skill").setAttribute("aria-pressed", String(!!mode && mode.kind === view.globalSkill?.kind));
  const u = selectedUnit();
  panel.hidden = !u || u.row === null || busy || (mode && mode.kind !== "move");
  prompt.hidden = !mode;
  const ready = mode?.kind === "march" && !mode.marchUnit && mode.moves.length &&
    mode.choices.some(a => a.march.length === mode.moves.length);
  prompt.innerHTML = mode ? `<span>${esc(mode.hint)}</span>${ready ? '<button data-action="confirm-march">确认行军</button>' : ""}<button data-action="cancel" aria-label="取消选择目标">取消</button>` : "";
  if (panel.hidden) return;
  const mine = u.team === "ally" && (u.hero || u.skillKind);
    const skill = skillKind(u) ? actionFor(skillKind(u), u.key) : [];
  panel.innerHTML = mine
    ? `<button data-action="skill" ${skill.length ? "" : "disabled"} aria-label="${skillName(u)}${u.cooldown ? `，冷却 ${u.cooldown} 回合` : ""}" title="${skillName(u)}">${u.cooldown || icon("fissure")}</button><button data-action="equipment" aria-label="查看装备并使用主动装备" title="装备">${icon("shield")}</button><button data-action="detail" aria-label="查看成长与状态">ⓘ</button>`
    : '<button data-action="detail" aria-label="查看单位详情">ⓘ</button>';
  const anchor = $(`.cell[data-unit="${u.key}"]`);
  if (anchor) {
    panel.style.left = `${anchor.offsetLeft}px`;
    panel.style.top = `${anchor.offsetTop + anchor.offsetHeight - 47}px`;
    panel.style.width = `${anchor.offsetWidth}px`;
  }
}
function renderHistory() {
  const entry = reviewingAction || view.lastOpponent;
  const layer = $("#history-overlay");
  if (!entry || busy || (!reviewingAction && entry.round !== view.round)) { layer.innerHTML = ""; return; }
  let markup = '<defs><marker id="history-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0 L8 4 L0 8z" fill="#d7c5ef"/></marker></defs>';
  if (entry.kind === "move" && entry.source && entry.path?.length) {
    const from = entry.source;
    markup += `<image href="${unitImage({ ...from, team: entry.team === 1 ? "enemy" : "ally" })}" x="${from.col * 100 + 8}" y="${from.row * 100 + 8}" width="84" height="75" opacity=".28"/><rect x="${from.col * 100 + 4}" y="${from.row * 100 + 4}" width="92" height="92" rx="4" fill="none" stroke="#d7c5ef" stroke-width="2" stroke-dasharray="7 5"/><path d="${entry.path.map((p, i) => `${i ? "L" : "M"}${(p.col + .5)*100},${(p.row + .5)*100}`).join(" ")}" fill="none" stroke="#d7c5ef" stroke-width="4" stroke-dasharray="8 7" marker-end="url(#history-arrow)"/>`;
  }
  for (const p of entry.affected || []) markup += `<rect x="${p.col*100+5}" y="${p.row*100+5}" width="90" height="90" rx="5" fill="none" stroke="#d7c5ef" stroke-width="3" stroke-dasharray="5 4"/>`;
  if (entry.source && entry.kind !== "move") markup += `<rect x="${entry.source.col*100+3}" y="${entry.source.row*100+3}" width="94" height="94" rx="5" fill="none" stroke="#d7c5ef" stroke-width="3"/>`;
  if (entry.fortTeam !== undefined) { const f = view.forts[entry.fortTeam]; markup += `<rect x="${f.col*100+3}" y="${f.row*100+3}" width="94" height="94" fill="none" stroke="#d7c5ef" stroke-width="4"/>`; }
  layer.innerHTML = markup;
}
function unavailableReason(id, isItem, index) {
  if (view.phase !== "action")
    return view.phase === "finished"
      ? "对局已经结束"
      : "下一回合开始后可以使用";
  const c = CARDS[id];
  if (isItem) {
    const price = view.items[index].paid ? 0 : c.gold_cost;
    if (price > view.gold) return `需要 ${price} 金币，当前 ${view.gold}`;
  } else {
    if (c.hero_id) {
      const hero = view.heroes.find(u => u.id === c.hero_id && u.team === "ally");
      if (!hero || hero.row === null) return `需要${cardName(c.hero_id)}在场`;
      if (hero.level < c.unlock_level) return `需要${cardName(c.hero_id)}达到${c.unlock_level}级（当前${hero.level}级）`;
    }
    if (cardCost(id) > view.mana)
      return `需要 ${cardCost(id)} 法力，当前 ${view.mana}`;
    if (
      c.colors?.length &&
      !view.units.some(
        (u) => u.team === "ally" && u.hero && c.colors.includes(identity(u.id)),
      )
    )
      return `需要在场的${{ red: "红色", blue: "蓝色", green: "绿色", black: "黑色" }[c.colors[0]]}英雄`;
  }
  return "当前没有合法目标或可部署的空格";
}
function cardTypeLabel(card) {
  if (card.card_type === "Item") return SLOT_NAMES[card.sub_type] || "消耗品";
  return card.card_type === "Creep" ? "单位" : "法术";
}
function cardFace(id, cost, {paid = false, detail = false} = {}) {
  const c = CARDS[id], item = c.card_type === "Item";
  const kind = paid ? "已付费" : cardTypeLabel(c);
  const stats = c.card_type === "Creep"
    ? `<span class="face-unit-stats">${icon("sword")}${c.attack}${icon("heart")}${c.hit_points}</span>`
    : "";
  return `<span class="card-face identity-${identity(id)} ${item ? "gold-face" : ""} ${detail ? "full-face" : ""}">
    <span class="face-heading"><span class="card-cost">${cost}</span><span class="face-title">${esc(cardName(id))}</span></span>
    <span class="card-art"><img ${detail ? 'class="detail-art"' : ""} src="${image(id)}" alt=""></span>
    <span class="face-footer"><span>${kind}</span>${stats}</span>
  </span>`;
}

function renderHand() {
  if (!view) return;
  const item = tab === "items",
    hand = item ? view.items.map((x) => x.id) : view.hand;
  document.querySelectorAll(".hand-tab").forEach((b) => {
    const active = b.dataset.tab === tab;
    b.classList.toggle("active", active);
    b.setAttribute("aria-selected", active);
    b.tabIndex = active ? 0 : -1;
    b.querySelector("span").textContent =
      b.dataset.tab === "items" ? view.items.length : view.hand.length;
  });
  $("#deck-count").textContent =
    `${item ? "物品牌库" : "牌库"} ${item ? view.itemDeck : view.deck}`;
  $("#hand").setAttribute("aria-labelledby", item ? "tab-items" : "tab-cards");
  const scroll = $("#hand").scrollLeft;
  $("#hand").innerHTML =
    hand
      .map((id, index) => {
        const c = CARDS[id],
          paid = item && view.items[index].paid,
          cost = item ? (paid ? 0 : c.gold_cost) : cardCost(id);
        const usable = actions().some(
          (a) => a.kind === (item ? "item" : "card") && a.index === index,
        );
        return `<button class="hand-card ${item ? "item-card" : ""} ${usable ? "" : "unavailable"}" data-card="${id}" data-index="${index}" data-item="${item}" aria-label="${esc(cardName(id))}，${cost}${item ? "金币" : "法力"}，查看详情">${cardFace(id,cost,{paid})}</button>`;
      })
      .join("") || '<span class="empty-hand">暂无手牌</span>';
  $("#hand").scrollLeft = scroll;
}
function render(previous) {
  if (!view) return;
  if (
    !selected ||
    (!view.units.some((u) => u.key === selected) &&
      !view.heroes.some((u) => u.key === selected))
  )
    selected = null;
  document.title = `V${view.release} · 单路战场`;
  $(".game").dataset.release = view.release;
  $(".prototype-note").textContent = `V${view.release} · ${view.columns} 列战场 · ${window.ArtifactAPI.browserMode ? "进度保存在此浏览器" : "本地试玩"}`;
  $("#round-label").textContent = `第 ${view.round} 回合`;
  $("#turn-text").textContent = busy
    ? "行动中"
    : view.phase === "action"
      ? "你的行动"
      : view.phase === "round_end"
        ? "交战结束"
        : view.phase === "combat"
          ? "正在交战"
          : "对局结束";
  $("#mana-value").innerHTML = `${view.mana} <span>/ ${view.maxMana}</span>`;
  const commandButton = $("#global-skill"), command = view.globalSkill;
  commandButton.hidden = !command;
  if (command) {
    commandButton.textContent = command.name;
    commandButton.disabled = busy || view.phase !== "action" || !actions().some(a => a.kind === command.kind);
    commandButton.title = command.used ? "本轮已使用" : `${command.name} · 每轮一次，消耗 ${command.cost} 法力和一次行动`;
    commandButton.setAttribute("aria-label", commandButton.title);
  }
  $("#gold-value").textContent = view.gold;
  $("#enemy-mana-value").innerHTML = `${view.opponent.mana}<span>/${view.maxMana}</span>`;
  $("#enemy-gold-value").textContent = view.opponent.gold;
  view.forts.filter((f) => f.team === 1).forEach((f) => {
    const el = $(".enemy-fort");
    el.querySelector("b").innerHTML = `${f.hp}<span>/${f.maxHp}</span>`;
    el.querySelector("i").style.width =
      `${Math.max(0, (f.hp / f.maxHp) * 100)}%`;
    el.querySelector(".fort-caption").textContent =
      `${f.team === 0 ? "我" : "敌"}${f.stage === "tower" ? "塔" : "基地"}`;
    el.classList.toggle("fort-immune", !f.ready);
    const prediction = !busy && view.phase === "action" ? view.forecast?.forts.find((p) => p.team === f.team) : null;
    let loss = el.querySelector(".fort-forecast");
    if (!loss) { loss = document.createElement("em"); loss.className = "fort-forecast"; el.querySelector(".fort-meter").append(loss); }
    loss.style.left = `${(prediction?.hp ?? f.hp) / f.maxHp * 100}%`;
    loss.style.width = `${Math.max(0, f.hp - (prediction?.hp ?? f.hp)) / f.maxHp * 100}%`;
    el.title = prediction ? `当前直接交战：${prediction.destroyed ? f.stage === "tower" ? "预计破塔" : "预计摧毁基地" : `预计剩余 ${prediction.hp} 生命`}` : "查看建筑详情";
    const old = previous?.forts.find((p) => p.team === f.team);
    el.classList.toggle("fort-hit", !!old && (old.hp > f.hp || old.stage !== f.stage));
    el.setAttribute(
      "aria-label",
      `${f.team === 0 ? "我方" : "敌方"}${f.stage === "tower" ? "防御塔" : "基地"}，生命${f.hp}，攻击${f.attack}${f.ready ? "" : "，下回合激活"}`,
    );
  });
  const footer = $("#pass-button");
  footer.disabled = busy;
  footer.innerHTML = `${busy ? "请稍候" : view.phase === "round_end" ? "采购" : view.phase === "finished" ? "查看结果" : "让过"}${icon("arrow")}`;
  footer.classList.toggle("next-round", view.phase === "round_end");
  footer.title = `第 ${view.round} 回合 · ${$("#turn-text").textContent}`;
  footer.classList.toggle(
    "long-label",
    ["round_end", "finished"].includes(view.phase),
  );
  $("#concede-button").hidden = view.phase === "finished";
  const dead = view.heroes.filter((h) => h.team === "ally" && h.row === null);
  $("#enemy-info").setAttribute(
    "aria-label",
    `查看对手行动记录${view.lastOpponent ? `，上一手：${view.lastOpponent.label}` : ""}`,
  );
  let badge = $("#enemy-info .reserve-count");
  if (dead.length) {
    if (!badge) {
      badge = document.createElement("span");
      badge.className = "reserve-count";
      $("#enemy-info").append(badge);
    }
    badge.textContent = dead.length;
  } else badge?.remove();
  renderBoard(previous);
  renderUnit();
  renderHand();
}
function openDetail(content) {
  $("#close-detail").hidden = !view;
  if (!$("#detail-dialog").open) returnFocus = document.activeElement;
  $("#detail-body").innerHTML = content;
  if (!$("#detail-dialog").open) $("#detail-dialog").showModal();
}
function closeDetail() {
  $("#detail-dialog").close();
}
function targetDescription(u) {
  if (u.debuffs?.hex) return "妖术，无法攻击、移动或使用主动能力";
  if (u.stunned) return "眩晕，无法普攻";
  if (!u.target) return "射程内暂无普攻目标";
  if (u.target === "AF" || u.target === "BF")
    return `普攻${u.team === "ally" ? "敌方" : "我方"}建筑`;
  const target = view.units.find((x) => x.key === u.target);
  return `${u.canAttack === false ? "仇恨目标（当前打不到，未移动则交战前追击）" : "普攻目标"}：${target ? unitName(target) : "未知单位"}`;
}
function showUnit(u) {
  if (!u) return;
  const prediction = view.phase === "action" ? view.forecast?.units[u.key] : null;
  const gear = u.equipment.map((e) => cardName(e.id)).join("、");
  const customArt = unitArt(u) || hasCustomCardArt(u.id);
  openDetail(
    `<h2 id="detail-title" class="detail-heading">${u.hero ? pip(u.id) : ""}${unitName(u)}</h2><p class="detail-subtitle">${u.team === "ally" ? "我方" : "敌方"}${u.hero ? "英雄" : "单位"} · ${u.row === null ? `等待第 ${u.due} 回合登场` : `第 ${u.row + 1} 排，第 ${u.col + 1} 列`}</p><div class="detail-layout"><img class="detail-art" src="${unitImage(u, "large_image")}" alt="${unitName(u)}${customArt ? "立绘" : "原版卡面"}"><div class="detail-copy"><div class="detail-stats">${stats(u)}${u.armor ? `<span class="stat">${icon("shield")}${u.armor}</span>` : ""}</div><p>${esc(HEROES[u.id]?.text || CARDS[u.id]?.card_text.schinese || "近战一格，自动移动与交战。")}</p><p class="detail-muted">射程 ${u.range} 格${u.siege ? ` · 攻城 ${u.siege}` : ""}${u.cleave ? ` · 顺势 ${u.cleave}` : ""}${u.regeneration ? ` · 恢复 ${u.regeneration}` : ""}</p>${u.row !== null ? `<p class="detail-muted">${esc(targetDescription(u))}</p>` : ""}${prediction ? `<p class="forecast-detail">当前局面直接交战：${prediction.dies ? "预计阵亡" : `预计剩余 ${prediction.hp} 生命`}。对手行动后会更新。</p>` : ""}${gear ? `<p class="detail-muted">装备：${esc(gear)}</p>` : ""}${u.level ? `<p class="growth-progress">Lv${u.level} · 经验 ${u.xp}${u.level < 3 ? ` / ${u.level === 1 ? 3 : 6}` : ""}${u.pendingLevel > u.level ? ` · 下轮升至Lv${u.pendingLevel}` : ""}</p><p class="detail-muted">成长（攻/甲/血）：${u.panels.map((p,i)=>`Lv${i+1} ${p.join("/")}`).join(" → ")}</p>` : ""}${statusText(u) ? `<p class="detail-muted">负面状态：${esc(statusText(u))}</p>` : ""}${u.buffs?.bkb ? '<p class="detail-muted">BKB：本轮魔法、负面状态免疫</p>' : ""}${u.cooldown ? `<p class="detail-muted">技能冷却 ${u.cooldown} 回合</p>` : ""}</div></div><p class="detail-note">${customArt ? "使用自制立绘。" : "沿用原版立绘。"}当前能力和攻血以战场数值为准。</p>`,
  );
}
function showEquipment(u) {
  const entries = u.equipment
    .map((e) => {
      const kind = e.active || (e.id === 10260 ? "horn" : e.id === 10263 ? "blade" : null);
      const choices = kind ? actionFor(kind, u.key) : [];
      return `<div class="gear-row"><img src="${image(e.id)}" alt=""><span><b>${cardName(e.id)}</b><small>${SLOT_NAMES[e.slot] || e.slot}${e.cooldown !== null ? ` · ${e.cooldown ? `冷却 ${e.cooldown}` : "主动就绪"}` : ""}</small><small>${esc(CARDS[e.id].card_text.schinese)}</small></span>${kind ? `<button class="gear-active" data-gear-kind="${kind}" ${choices.length ? "" : "disabled"}>使用</button>` : ""}</div>`;
    })
    .join("");
  openDetail(
    `<h2 id="detail-title" class="detail-heading">${unitName(u)}的装备</h2><p class="sheet-note">每类槽位一件，新装备替换同槽旧装备。阵亡后保留；圣剑按击杀归属转移。</p>${entries || '<p class="sheet-note">暂未穿戴装备。</p>'}<button class="detail-action" id="open-item-hand">查看物品手牌</button>`,
  );
}
function showCard(id, index, item) {
  if (busy) return;
  mode = null;
  renderBoard();
  renderUnit();
  const c = CARDS[id],
    choices = actions().filter(
      (a) => a.kind === (item ? "item" : "card") && a.index === index,
    ),
    cost = item ? (view.items[index].paid ? 0 : c.gold_cost) : cardCost(id);
  const global =
    choices.length &&
    ["all", "self", "draw", "ticket", "improvement", "fort"].includes(
      choices[0].target,
    );
  const label = !choices.length
    ? unavailableReason(id, item, index)
    : global
      ? choices[0].target === "fort"
        ? `施放 · 敌方${view.forts[1].stage === "tower" ? "防御塔" : "基地"}`
        : item
          ? "使用"
          : "施放"
      : "选择目标";
  openDetail(
    `<h2 id="detail-title" class="sr-only">${esc(cardName(id))}</h2>
    <div class="detail-layout framed-card-detail">${cardFace(id,cost,{paid:item && view.items[index].paid,detail:true})}
      <div class="detail-copy"><p class="card-detail-type">${item ? "金币" : "法力"} ${cost} · ${cardTypeLabel(c)}</p>
      <p>${esc(RULES[id] || c.card_text.schinese).replace(/\n+/g, "<br>")}</p>
      ${item && c.sub_type !== "Consumable" ? '<p class="detail-muted">穿戴占一次行动，同槽装备会被替换。</p>' : ""}
      ${c.card_type === "Creep" ? `<div class="detail-stats" aria-label="攻击、护甲、生命">${icon("sword")}${c.attack}${icon("shield")}${c.armor}${icon("heart")}${c.hit_points}</div>` : ""}</div></div>
    <button class="detail-action" id="play-card" data-id="${id}" data-index="${index}" data-item="${item}" ${choices.length ? "" : "disabled"}>${esc(label)}</button>
    ${item ? "" : `<button class="quiet-button" id="reforge-card" data-index="${index}" data-item="${item}" ${actions().some(a => a.kind === "reforge" && a.actor === String(index)) ? "" : "disabled"}>重铸 · 1行动 / 0法力</button><p class="detail-muted">先抽一张，再将本卡放回原牌库；牌库为空时不可重铸。</p>`}`,
  );
}
function setMode(kind, choices, hint) {
  mode = { kind, choices, hint };
  renderBoard();
  renderUnit();
}
function chooseCard(index, item) {
  const choices = actions().filter(
    (a) => a.kind === (item ? "item" : "card") && a.index === index,
  );
  if (!choices.length) return;
  closeDetail();
  if (choices[0].march) {
    mode = {kind:"march", choices, moves:[], preview:[], hint:"协同行军 · 选择九格区域的中心"};
    renderBoard(); renderUnit();
    return;
  }
  if (
    ["all", "self", "draw", "ticket", "improvement", "fort"].includes(
      choices[0].target,
    )
  ) {
    perform(choices[0].id);
    return;
  }
  const id = choices[0].card_id;
  setMode(
    item ? "item" : "card",
    choices,
    choices[0].row !== undefined
      ? `${cardName(id)} · 选择高亮位置`
      : `${cardName(id)} · 选择高亮单位`,
  );
}
function unitAction(kind) {
  if (kind === "cancel") {
    cancelMode();
    return;
  }
  if (kind === "roster") {
    showRoster();
    return;
  }
  const u = selectedUnit();
  if (!u) return;
  if (kind === "detail") {
    showUnit(u);
    return;
  }
  if (kind === "equipment") {
    showEquipment(u);
    return;
  }
  if (busy || view.phase !== "action") return;
  if (kind === "move") {
    if (mode?.kind === "move") {
      cancelMode();
      return;
    }
    const choices = actionFor("move", u.key);
    if (choices.length)
      setMode(
        "move",
        choices,
        u.firstMove
          ? "首次移动 · 最多两格，不能穿过单位"
          : "移动 · 选择相邻空格",
      );
  } else if (kind === "skill") {
    if (mode?.kind === "skill") {
      cancelMode();
      return;
    }
    const choices = actionFor(skillKind(u), u.key);
    if (skillKind(u) === "whirl" && choices.length) {
      perform(choices[0].id);
      return;
    }
    if (choices.length)
      setMode(
        "skill",
        choices,
        u.id === 10033
          ? "沟壑 · 直线两格，2 点普通伤害并眩晕"
          : `${skillName(u)} · 选择目标`,
      );
  }
}
function cancelMode() {
  mode = null;
  renderBoard();
  renderUnit();
}
function cellClick(row, col) {
  if (!view) return;
  if (busy) return;
  const u = view.units.find((x) => x.row === row && x.col === col);
  if (mode && !(mode.kind === "move" && u)) {
    const choices = targetAt(row, col);
    if (choices.length) {
      if (mode.kind === "march") {
        mode.choices = choices;
        if (!mode.center) {
          mode.center = [row,col];
          mode.hint = "协同行军 · 选择区域内的友军";
        } else if (!mode.marchUnit) {
          mode.marchUnit = u.key;
          mode.hint = "协同行军 · 选择前进落点";
        } else {
          mode.moves.push(mode.marchUnit);
          mode.preview.push([row,col]);
          mode.marchUnit = null;
          const ready = choices.some(a => a.march.length === mode.moves.length);
          mode.hint = !ready ? "协同行军 · 继续选择会腾出路线的友军"
            : choices.every(a => a.march.length === mode.moves.length)
              ? "协同行军 · 确认本次移动" : "协同行军 · 确认移动，或继续选择友军";
        }
        renderBoard(); renderUnit();
        return;
      }
      if (choices[0].firstTarget) {
        if (mode.kind === "rally_swap") selected = u.key;
        mode.choices = choices.map(a => ({...a, target:a.secondTarget, firstTarget:null, row:a.secondRow ?? a.row, col:a.secondCol ?? a.col}));
        mode.hint = mode.kind === "rally_swap" ? "调位 · 选择相邻友军或空格" : "已选定施法单位 · 再选择高亮目标";
        renderBoard(); renderUnit();
        return;
      }
      mode = null;
      perform(choices[0].id);
    } else if (!u && mode.kind === "move") { selected = null; cancelMode(); }
    else toast("请选择高亮位置，或点取消");
    return;
  }
  const fort = view.forts.find((f) => f.row === row && f.col === col);
  if (fort) { showFort(fort); return; }
  if (!u) { selected = null; cancelMode(); return; }
  if (u) {
    const cancel = mode?.kind === "move" && selected === u.key;
    mode = null;
    selected = u.key;
    if (!cancel && u.team === "ally" && u.hero && actionFor("move", u.key).length) {
      setMode("move", actionFor("move", u.key), u.firstMove ? "首次移动 · 最多两格，不能穿过单位" : "移动 · 选择相邻空格");
      return;
    }
    renderBoard();
    renderUnit();
  }
}
function showRoster() {
  const groups = ["ally", "enemy"]
    .map(
      (team) =>
        `<h3 class="roster-heading">${team === "ally" ? "我方英雄" : "敌方英雄"}</h3><div class="roster-list">${view.heroes
          .filter((h) => h.team === team)
          .map(
            (h) =>
              `<button class="roster-unit ${h.row === null ? "waiting" : ""}" data-hero="${h.key}"><img src="${image(h.id)}" alt=""><span>${pip(h.id)}${cardName(h.id)}<small>${h.row === null ? `第 ${h.due} 回合登场` : h.stunned ? "眩晕，仍提供出牌颜色" : `Lv${h.level} · 经验${h.xp} · ${h.hp}/${h.maxHp} 生命`}${h.cooldown ? ` · CD ${h.cooldown}` : ""}</small></span></button>`,
          )
          .join("")}</div>`,
    )
    .join("");
  openDetail(
    `<h2 id="detail-title" class="detail-heading">阵容与返场</h2>${groups}<p class="detail-note">死亡后跳过下一回合，再下一回合从泉水返场。泉水可用空位不足时，自动替换己方生命最低的小兵。</p>`,
  );
}
function showLog(enemyOnly = false) {
  const entries = (view.history || []).map((entry, index) => ({ ...entry, index })).filter((e) => !enemyOnly || e.team === 1);
  openDetail(
    `<h2 id="detail-title" class="detail-heading">${enemyOnly ? "对手" : "双方"}行动记录</h2><p class="sheet-note">点击行动可在棋盘上查看位置与路径。</p><div class="log-options"><button id="log-toggle" data-enemy-only="${!enemyOnly}">${enemyOnly ? "查看双方行动" : "只看对手"}</button><button data-action="roster">阵容与返场</button></div><div class="history-list">${entries.slice().reverse().map((e) => `<button class="history-entry" data-history="${e.index}">${e.card_id ? `<img src="${image(e.card_id)}" alt="">` : e.source ? `<img src="${unitImage({ ...e.source, team: e.team === 1 ? "enemy" : "ally" })}" alt="">` : '<span class="history-pass">让</span>'}<span><b>${esc(e.label)}</b><small>第 ${e.round} 回合 · ${e.team === 1 ? "敌方" : "我方"}${e.kind === "move" ? " · 查看移动路径" : ""}</small></span></button>`).join("") || '<p class="sheet-note">尚无行动</p>'}</div><details><summary>详细事件</summary><div class="action-log">${
      view.log
        .slice()
        .reverse()
        .map((e) => `<p><span>${e.round}</span>${esc(e.text)}</p>`)
        .join("") || "暂无记录"
    }</div></details>`,
  );
}
function showHelp() {
  openDetail(
    `<h2 id="detail-title" class="detail-heading">单路战场</h2><div class="help-copy"><p><b>行动：</b>打牌、移动英雄、使用技能、穿戴或使用装备，每次占一个行动，随后由对手回应。普通攻击自动进行。打不到主动指定或受控锁定的目标时，未移动的单位在交战前尝试追击。重铸消耗一次行动、0法力，先抽牌再将原牌归库。</p><p><b>预测：</b>箭头表示普攻目标；灰色头像和红叉表示预计阵亡，→ 后的数字表示交战后的生命。预测按当前局面双方直接交战计算，对手行动后会更新。</p><p><b>交战：</b>双方连续让过后，先处理仇恨追击，再由所有单位与建筑同时结算攻击。恢复在阵亡清理前结算。交战后可查看损伤，再打开采购。</p><p><b>移动：</b>点己方英雄显示可移动格；棋子上的按钮用于技能和装备，长按查看详情。点空格或取消退出选择，不占行动。英雄每回合移动一次，平时八邻一格；从泉水出生／返场后的首次移动最多两格，不能穿过单位。小兵自动向前推进。</p><p><b>仇恨与箭头：</b>绿色为我方，红色为敌方；远程虚线指向具体目标。自动仇恨保留仍在射程内的旧目标；目标出射程后选择四向射程内最近敌人，同距离按固定顺序；没有单位可打时才攻击建筑。英雄不自动保护转火，这条只作用于小兵和建筑。</p><p><b>全局技能：</b>每方每轮一次，2 法力，消耗一次行动。绿色调位可移到八邻空格，或与八邻友军交换。红色指引攻击可选场上敌军，让目标周围八格的可行动友军集火。</p><p><b>出牌：</b>普通牌需要对应颜色英雄在场；眩晕仍提供颜色。起手5张，后续每轮抽1张；首轮1法力，每轮刷新并加1，上限10。所有专属卡都要求对应英雄在场并达到解锁等级；阵亡保留等级，返场后可继续使用。</p><p><b>成长：</b>英雄在场且存活到回合末获得1经验，3/6经验分别升至2/3级，下轮生效。死亡保留等级、经验与永久强化，升级增加的生命直接补到当前生命。</p><p><b>金币：</b>无工资，敌方小兵死亡 +1，英雄死亡 +5。开局发一张物品；交战后可从三个货源选购一件，或跳过。购入手牌的物品已经支付。</p><p><b>装备：</b>武器、护甲、饰品各一件，同类替换。主动效果消耗一次行动、0法力，有冷却。沉默不禁装备，妖术禁装备主动、保留被动。BKB驱散全部负面状态，并在本轮免疫魔法伤害和新增负面状态。</p><p><b>胜负：</b>摧毁敌方 40 血防御塔即可获胜，双方塔同时被摧毁则平局，不再出现基地。塔位于每方从中线往后数的第三排，占中央一格，攻击 4，每次交战攻击八邻内一名敌军；进入敌方泉水会受到 10 点范围伤害。</p><p>当前固定阵容与候选牌池，双方交替获得每回合先手。右上角可查看记录和导出本局。</p></div>`,
  );
}
function showResult() {
  const won = view.winner === 0,
    draw = view.winner === null;
  const title = draw
    ? "同归于尽"
    : won
      ? "防御塔已摧毁 · 胜利"
      : view.endReason === "conceded"
        ? "本局认输"
        : "防御塔失守 · 失利";
  const stats = view.stats[0];
  openDetail(
    `<div class="result-mark">${icon("tower")}</div><h2 id="detail-title" class="result-title">${title}</h2><p class="result-subtitle">${view.endReason === "conceded" ? "你结束了这场对局" : draw ? "双方防御塔同时被摧毁" : won ? "敌方防御塔已被摧毁" : "我方防御塔已被摧毁"}</p><div class="result-stats"><span><b>${view.round}</b>回合</span><span><b>${stats.hero_kills || 0}</b>英雄击杀</span><span><b>${stats.gold_spent || 0}</b>花费金币</span></div><button class="detail-action" id="result-new">再来一局</button><button class="quiet-button" id="result-export">导出本局记录</button>`,
  );
}
function showShop() {
  const shop = view.shop;
  if (!shop) {
    perform("next_round");
    return;
  }
  const offers = shop.offers.map(({id, source, price, action_id}, index) => `
    <div class="shop-offer">
      <div class="shop-art">${id === null ? "" : `<img src="${image(id)}" alt="">`}</div>
      <div><b>${esc(source)}</b><p>${id === null ? "牌堆已空" : esc(cardName(id)) + ` · ${price} 金`}</p>
        ${id === null ? "" : `<small>${esc(CARDS[id]?.card_text.schinese || "")}</small>`}</div>
      ${id === null ? "" : `<button data-shop-offer="${action_id ?? ""}" ${action_id ? "" : "disabled"}>${shop.selected === index ? "已购入" : "购买"}</button>`}
    </div>`).join("");
  openDetail(`<h2 id="detail-title" class="detail-heading">战后采购 · ${view.gold} 金</h2>
    <div class="shop-list">${offers}</div>
    <button class="detail-action" id="finish-shop">${shop.bought ? "结束采购" : "跳过采购"}</button>`);
  $("#detail-body").querySelectorAll("[data-shop-offer]:not([disabled])").forEach(button => {
    button.addEventListener("click", async () => {
      closeDetail();
      await perform(button.dataset.shopOffer);
      if (view.phase === "round_end") showShop();
    });
  });
  $("#finish-shop").addEventListener("click", () => {
    closeDetail();
    perform("next_round");
  });
}
function downloadPlaytest(data) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob), link = document.createElement("a");
  link.href = url;
  link.download = `artifact-${data.seed}-round-${data.round}.json`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function exportMatch() {
  try {
    downloadPlaytest(await api(`/api/games/${gameId}/export`));
    toast("对局记录已导出");
  } catch (e) {
    toast(e.message);
  }
}
async function showPlaytests() {
  try {
    const matches = await window.ArtifactAPI.listPlaytests();
    const entries = matches.map((match, index) =>
      `<button class="scene-option" data-playtest-index="${index}"><span>第 ${match.round} 回合 · ${match.phase === "finished" ? "已结束" : "进行中"}<small>${esc(new Date(match.updated_at).toLocaleString())} · 种子 ${match.seed}</small></span><b>↓</b></button>`).join("");
    openDetail(`<h2 id="detail-title" class="detail-heading">本机对局</h2>
      ${entries || '<p class="sheet-note">当前浏览器还没有归档。</p>'}`);
    $("#detail-body").querySelectorAll("[data-playtest-index]").forEach(button => {
      button.addEventListener("click", () => downloadPlaytest(matches[Number(button.dataset.playtestIndex)]));
    });
  } catch {
    toast("打不开浏览器对局归档。仍可导出当前一局。");
  }
}
function confirmConcede() {
  openDetail(
    `<h2 id="detail-title" class="detail-heading">认输并结束本局？</h2><p class="sheet-note">本局会记为失利，仍可查看和导出对局记录。</p><button class="detail-action" id="confirm-concede">确认认输</button><button class="quiet-button" id="keep-playing">继续战斗</button>`,
  );
}
async function applyPacket(packet, animate = false, command = null) {
  gameId = packet.game_id;
  rememberId(gameId);
  mode = null;
  const sequence = requestSequence;
  if (animate) {
    const frames = packet.frames.length ? packet.frames : [packet.state];
    for (const [index, frame] of frames.entries()) {
      if (sequence !== requestSequence) return;
      const previous = view;
      const next = { ...packet.state, ...frame, actions: [] };
      if (frame.phase !== "combat") {
        await window.ArtifactBattleFX.action(previous, next, frame.action || (index === 0 ? command : null));
        await window.ArtifactBattleFX.deaths(previous, next);
      }
      if (sequence !== requestSequence) return;
      view = next;
      render(previous);
      toast(frame.label, frame.action?.card_id);
      if (frame.phase === "combat") await window.ArtifactBattleFX.combat(view);
      else if (!await window.ArtifactBattleFX.changes(previous, view)) await delay(120);
    }
  }
  if (sequence !== requestSequence) return;
  const previous = view;
  view = packet.state;
  busy = false;
  render(previous);
  if (view.phase === "finished") showResult();
  else if (view.phase === "round_end") toast(view.shop?.bought ? "物品已入手牌 · 结束采购可继续" : "交战结束 · 可以采购");
  else if (animate && !packet.frames.length) toast(view.label);
}
async function perform(id) {
  if (busy || !view) return;
  const command = view.actions.find((a) => a.id === id);
  clearTimeout(toastTimer);
  $("#toast").hidden = true;
  busy = true;
  mode = null;
  selected = null;
  reviewingAction = null;
  render();
  const sequence = ++requestSequence;
  try {
    const packet = await api(`/api/games/${gameId}/actions`, {
      version: view.version,
      action_id: id,
    });
    if (sequence === requestSequence) await applyPacket(packet, true, command);
  } catch (error) {
    try {
      if (gameId) {
        const packet = await api(`/api/games/${gameId}`);
        await applyPacket(packet);
      }
    } catch {
      showReconnect(error);
      return;
    }
    toast(
      error.name === "AbortError"
        ? "连接超时，已恢复到最新战场"
        : error.message,
    );
  }
}
function showReconnect(error) {
  busy = true;
  if (view) render();
  $("#turn-text").textContent = "连接中断";
  openDetail(
    `<h2 id="detail-title" class="detail-heading">重新载入战场</h2><p class="sheet-note">${esc(error.status || window.ArtifactAPI.browserMode ? error.message : "请确认电脑上的游戏服务仍在运行，手机和电脑处于同一网络。")}</p><button class="detail-action" id="retry-connect">重试</button><button class="quiet-button" id="recover-new">开始新一局</button>`,
  );
}
function defaultDeck(color = "green") {
  if (color === "red") return expansion ? growthCatalog.expansionRedDeck : growthCatalog.redDeck;
  return expansion ? growthCatalog.expansionDeck : growthCatalog.defaultDeck;
}

const canBuild = (card, color) => card && card.card_id < (expansion ? 63000 : 62020)
  && ["Creep", "Spell"].includes(card.card_type) && card.colors.includes(color);
const cardCounts = (ids) => ids.reduce((counts, id) => (counts[id] = (counts[id] || 0) + 1, counts), {});
const copyPile = ({ordinary, items}) => ({ordinary:[...ordinary],items:[...items]});
const deckColors = {green:"绿色",red:"红色"};
const starterName = "绿色预设";
const savedLibraryKey = `${deckStorageKey}-library-v1`;
let setup = {deckId:null, opponentId:"pressure"};
let deckBackToSetup = false;

function validPiles(deck, color) {
  return deck && Array.isArray(deck.ordinary) && Array.isArray(deck.items)
    && deck.ordinary.length === 21 && deck.items.length === 10
    && deck.ordinary.every(id => Number.isInteger(id) && canBuild(CARDS[id], color))
    && deck.items.every(id => Number.isInteger(id) && CARDS[id]?.card_type === "Item")
    && [deck.ordinary, deck.items].every(pile => Object.values(cardCounts(pile)).every(n => n <= 3));
}

function readLibrary() {
  try {
    const saved = localStorage.getItem(savedLibraryKey);
    if (saved !== null) {
      const decks = JSON.parse(saved);
      if (Array.isArray(decks)) return decks.filter(d =>
        d && typeof d.id === "string" && d.id.length && typeof d.name === "string" && d.name.trim().length
        && d.name.length <= 40 && Object.hasOwn(deckColors,d.color) && validPiles(d,d.color));
    }
    const old = JSON.parse(localStorage.getItem(deckStorageKey));
    if (validPiles(old,"green")) return [{id:"previous-deck", name:"已保存牌组", color:"green", ...copyPile(old)}];
  } catch {
    // Allow the preset to start a match when browser storage is unavailable.
  }
  return [];
}

function opponentPresets() {
  return expansion ? growthCatalog.expansionOpponentPresets : growthCatalog.opponentPresets;
}

function showMatchSetup(message = "") {
  const decks = readLibrary();
  const green = decks.filter(d => d.color === "green");
  const red = decks.filter(d => d.color === "red");
  const presets = opponentPresets();
  if (setup.deckId === null) setup.deckId = green.find(d => d.id === "previous-deck")?.id || "";
  if (!green.some(d => d.id === setup.deckId)) setup.deckId = "";
  if (setup.opponentId === "saved" && !red.length) setup.opponentId = presets[0].id;
  const options = [{id:"",name:starterName}, ...green].map(d =>
    `<option value="${esc(d.id)}" ${d.id === setup.deckId ? "selected" : ""}>${esc(d.name)}</option>`).join("");
  const opponents = [...presets,{id:"saved", name:"随机自存牌组",
    description:red.length ? `从 ${red.length} 副红色牌组里随机挑选。` : "保存一副红色牌组后可选。"}];
  openDetail(`
    <div class="match-lobby">
      <header class="lobby-banner">
        <h2 id="detail-title" class="lobby-title">开始对局</h2>
        <div class="lobby-portraits" aria-hidden="true"><img src="assets/cards/10032.webp" alt=""><img src="assets/cards/10022.webp" alt=""></div>
      </header>
      <label class="lobby-field">我方牌组 <select id="match-deck">${options}</select></label>
      <fieldset class="opponent-picker"><legend>AI 对手</legend>${opponents.map(o => `
        <label class="opponent-choice">
          <input type="radio" name="opponent" value="${o.id}" ${o.id === setup.opponentId ? "checked" : ""} ${o.id === "saved" && !red.length ? "disabled" : ""}>
          <span><b>${esc(o.name)}</b><small>${esc(o.description)}</small></span>
        </label>`).join("")}</fieldset>
      ${message ? `<p class="lobby-error" role="status">${esc(message)}</p>` : ""}
      <div class="lobby-buttons">
        <button class="quiet-button" id="open-deck-library">管理牌组</button>
        <button class="detail-action" id="start-match">开始战斗</button>
      </div>
    </div>`);
}

function showDeckLibrary() {
  deckDraft = null;
  const decks = readLibrary();
  const group = (color) => {
    const cards = decks.filter(d => d.color === color);
    return `<section class="library-group identity-${color}">
      <div class="library-heading"><h3>${deckColors[color]}牌组</h3><button class="quiet-button" data-new-deck="${color}">新建</button></div>
      ${cards.length ? cards.map(d => `<button class="library-entry" data-edit-deck="${esc(d.id)}"><span>${esc(d.name)}</span><small>编辑</small></button>`).join("") : '<p class="sheet-note">还没有保存的牌组。</p>'}
    </section>`;
  };
  openDetail(`<h2 id="detail-title" class="detail-heading">我的牌组</h2>${group("green")}${group("red")}
    ${deckBackToSetup || !view ? '<button class="quiet-button" id="deck-to-lobby">返回开局</button>' : ""}`);
}

function showDeckBuilder() {
  const {color, name} = deckDraft;
  const ordinary = cardCounts(deckDraft.ordinary), items = cardCounts(deckDraft.items);
  const roster = (expansion ? growthCatalog.expansionRosters : growthCatalog.rosters)[color === "green" ? 0 : 1];
  const signatureCount = expansion ? 8 : 9;
  const rows = (isItem) => growthCatalog.cards.filter(c =>
    isItem ? c.card_type === "Item" : canBuild(c, color)).map(c => {
      const id = c.card_id, count = (isItem ? items : ordinary)[id] || 0;
      const limit = isItem ? deckDraft.items.length >= 10 : deckDraft.ordinary.length >= 21;
      const label = isItem ? `${c.gold_cost} 金 · ${SLOT_NAMES[c.sub_type] || "消耗品"}`
        : `${c.mana_cost} 费 · ${cardTypeLabel(c)}`;
      return `<div class="deck-row"><img src="${image(id)}" alt="" loading="lazy"><span><b>${esc(cardName(id))}</b><small>${esc(label)} · ${esc(c.card_text.schinese)}</small></span>
        <button data-deck-id="${id}" data-deck-item="${isItem}" data-delta="-1" ${count ? "" : "disabled"} aria-label="减少${esc(cardName(id))}">−</button>
        <b>${count}</b><button data-deck-id="${id}" data-deck-item="${isItem}" data-delta="1" ${count >= 3 || limit ? "disabled" : ""} aria-label="增加${esc(cardName(id))}">+</button></div>`;
    }).join("");
  openDetail(`<div class="deck-editor">
    <h2 id="detail-title" class="detail-heading">${deckColors[color]}牌组构筑</h2>
    <label class="lobby-field">牌组名称 <input id="deck-name" type="text" maxlength="40" value="${esc(name)}"></label>
    <div class="deck-edit-summary"><span>普通 ${deckDraft.ordinary.length + signatureCount}/${21 + signatureCount}</span><span>物品 ${deckDraft.items.length}/10</span></div>
    <details id="ordinary-deck" open><summary>普通自选牌 ${deckDraft.ordinary.length}/21</summary>${rows(false)}</details>
    <details id="item-deck"><summary>物品牌 ${deckDraft.items.length}/10</summary>${rows(true)}</details>
    <details id="signature-deck"><summary>固定专属 ${signatureCount} 张</summary>
      ${roster.map(h => `<p>${esc(cardName(h))} · ${esc(cardName(Number(growthCatalog.signatures[h])))} ×${[10022,10032].includes(h) ? 2 : 3}</p>`).join("")}
    </details>
    <div class="deck-editor-actions">
      <p class="detail-muted" id="deck-save-status" role="status"></p>
      <div class="lobby-buttons">
        <button class="quiet-button" id="back-to-decks">我的牌组</button>
        <button class="quiet-button" id="copy-deck">复制</button>
        <button class="detail-action" id="save-deck" ${name.trim() && validPiles(deckDraft,color) ? "" : "disabled"}>保存牌组</button>
      </div>
    </div>
  </div>`);
}

function saveDeckDraft() {
  if (!deckDraft.name.trim() || !validPiles(deckDraft,deckDraft.color)) return;
  const deck = {...deckDraft, ...copyPile(deckDraft), name:deckDraft.name.trim()};
  const decks = readLibrary();
  const old = decks.findIndex(d => d.id === deck.id);
  if (old >= 0) decks[old] = deck;
  else {
    deck.id = Array.from(crypto.getRandomValues(new Uint32Array(4)), n => n.toString(16).padStart(8,"0")).join("");
    decks.push(deck);
  }
  try {
    localStorage.setItem(savedLibraryKey,JSON.stringify(decks));
    deckDraft.id = deck.id;
    if (deck.color === "green") setup.deckId = deck.id;
    $("#deck-save-status").textContent = `已保存「${deck.name}」`;
  } catch {
    $("#deck-save-status").textContent = "浏览器无法保存牌组，请检查存储设置。";
  }
}

$("#detail-body").addEventListener("input", ({target}) => {
  if (target.id === "deck-name" && deckDraft) {
    deckDraft.name = target.value;
    $("#save-deck").disabled = !deckDraft.name.trim() || !validPiles(deckDraft,deckDraft.color);
  }
  if (target.id === "match-deck") setup.deckId = target.value;
  if (target.name === "opponent" && target.checked) setup.opponentId = target.value;
});

$("#detail-body").addEventListener("click", (event) => {
  const element = event.target.closest("button");
  if (!element || element.disabled) return;
  if (element.id === "open-deck-library") { deckBackToSetup = true; showDeckLibrary(); }
  if (element.id === "deck-to-lobby") showMatchSetup();
  if (element.id === "back-to-decks") showDeckLibrary();
  if (element.id === "start-match") createGame();
  if (element.id === "save-deck") saveDeckDraft();
  if (element.id === "copy-deck" && deckDraft) {
    deckDraft = {...deckDraft, id:null, name:`${deckDraft.name.slice(0,37)} 副本`};
    showDeckBuilder();
    $("#deck-name").focus();
    $("#deck-name").select();
  }
  if (element.dataset.newDeck) {
    const color = element.dataset.newDeck;
    deckDraft = {id:null, name:`${deckColors[color]}牌组`, color, ...copyPile(defaultDeck(color))};
    showDeckBuilder();
    $("#deck-name").focus();
    $("#deck-name").select();
  }
  if (element.dataset.editDeck) {
    const saved = readLibrary().find(d => d.id === element.dataset.editDeck);
    if (saved) { deckDraft = {...saved, ...copyPile(saved)}; showDeckBuilder(); }
  }
  if (element.dataset.deckId && deckDraft) {
    const {deckItem,deckId,delta} = element.dataset;
    const list = deckItem === "true" ? deckDraft.items : deckDraft.ordinary;
    const id = Number(deckId);
    const dialog = $("#detail-dialog");
    const scroll = dialog.scrollTop;
    const open = ["ordinary-deck","item-deck","signature-deck"].filter(key => $(`#${key}`).open);
    if (delta === "1") list.push(id);
    else list.splice(list.indexOf(id),1);
    showDeckBuilder();
    for (const key of ["ordinary-deck","item-deck","signature-deck"]) $(`#${key}`).open = open.includes(key);
    dialog.scrollTop = scroll;
    document.querySelector(`[data-deck-id="${id}"][data-delta="${delta}"]`)?.focus({preventScroll:true});
  }
});

async function createGame() {
  if (busy) return;
  const decks = readLibrary();
  const yours = decks.find(d => d.id === setup.deckId && d.color === "green");
  const presets = opponentPresets();
  const preset = presets.find(p => p.id === setup.opponentId) || presets[0];
  let opponent = {...copyPile(preset.deck),name:preset.name};
  if (setup.opponentId === "saved") {
    const pool = decks.filter(d => d.color === "red");
    if (!pool.length) { showMatchSetup("请先保存一副红色牌组。"); return; }
    const drawn = pool[Math.floor(Math.random() * pool.length)];
    opponent = {...copyPile(drawn),name:drawn.name};
  }
  const deck = {...copyPile(yours || defaultDeck()), name:yours?.name || starterName, opponent};
  if (expansion) deck.experiment = "combined";
  busy = true;
  const start = $("#start-match");
  if (start) { start.disabled = true; start.textContent = "准备战场…"; }
  try {
    const packet = await api("/api/games", {deck_config:deck});
    selected = null;
    reviewingAction = null;
    mode = null;
    tab = "cards";
    $("#hand").scrollLeft = 0;
    closeDetail();
    await applyPacket(packet);
    toast(`对手使用「${opponent.name}」`);
  } catch (error) {
    busy = false;
    showMatchSetup(error.message);
  }
}

async function bootstrap() {
  busy = true;
  gameId = savedId();
  try {
    if (!growthCatalog) {
      growthCatalog = await api("/api/catalog");
      for (const card of growthCatalog.cards) CARDS[card.card_id] = card;
      Object.assign(HEROES, {
        10014:{text:"八邻其他友军获得1/1/2攻击，随狼人等级变化。"},
        10017:{kind:"chen",skill:"劝化",text:"主动CD4：控制距离2内敌方非英雄单位。正交射程2。"},
        10022:{text:CARDS[10022]?.card_text.schinese},
        10032:{text:CARDS[10032]?.card_text.schinese},
        10044:{kind:"purify",skill:"洗礼",text:"主动CD2：自己或八邻友军恢复1/2/3生命。"},
        10054:{text:"固定分裂1/2/2，攻击目标两侧敌人；攻击提高不影响分裂。"},
        10069:{text:"二级起反伤2：受到普攻并实际掉血时触发，受护甲减免。"}
      });
    }
    if (gameId) await applyPacket(await api(`/api/games/${gameId}`));
    else { busy = false; showMatchSetup(); }
  } catch (error) {
    if (error.status === 404 || error.status === 409) {
      gameId = null;
      rememberId(null);
      view = null;
      busy = false;
      showMatchSetup("旧对局已到期，可以开始一局新对局。");
    } else showReconnect(error);
  }
}
$("#board").addEventListener("click", (e) => {
  const cell = e.target.closest(".cell");
  if (cell) cellClick(Number(cell.dataset.row), Number(cell.dataset.col));
});
$("#unit-panel").addEventListener("click", (e) => {
  const button = e.target.closest("[data-action]");
  if (button && !button.disabled) unitAction(button.dataset.action);
});
$("#target-prompt").addEventListener("click", (e) => {
  if (e.target.closest("[data-action=cancel]")) cancelMode();
  if (e.target.closest("[data-action=confirm-march]") && mode?.kind === "march" && !mode.marchUnit) {
    const choice = mode.choices.find(a => a.march.length === mode.moves.length);
    if (choice) perform(choice.id);
  }
});
let holdTimer = null, heldCell = null, suppressCellClick = false, holdOrigin = null;
function cancelHold() { clearTimeout(holdTimer); holdTimer = null; }
$("#board").addEventListener("pointerdown", (e) => {
  const cell = e.target.closest(".cell[data-unit]");
  if (!cell || busy) return;
  heldCell = cell.dataset.unit;
  suppressCellClick = false;
  holdOrigin = { x: e.clientX, y: e.clientY };
  holdTimer = setTimeout(() => {
    suppressCellClick = true;
    showUnit(view.units.find((u) => u.key === heldCell));
  }, 450);
});
$("#board").addEventListener("pointermove", (e) => { if (holdOrigin && Math.hypot(e.clientX-holdOrigin.x, e.clientY-holdOrigin.y) > 8) cancelHold(); });
for (const event of ["pointerup", "pointercancel", "pointerleave"]) $("#board").addEventListener(event, cancelHold);
$("#board").addEventListener("contextmenu", (e) => {
  const cell = e.target.closest(".cell[data-unit]");
  if (cell) { e.preventDefault(); cancelHold(); showUnit(view.units.find((u) => u.key === cell.dataset.unit)); }
});
$("#board").addEventListener("click", (e) => { if (suppressCellClick) { suppressCellClick = false; e.stopImmediatePropagation(); } }, true);
$("#hand").addEventListener("click", (e) => {
  const button = e.target.closest("[data-card]");
  if (button)
    showCard(
      Number(button.dataset.card),
      Number(button.dataset.index),
      button.dataset.item === "true",
    );
});
document.querySelectorAll(".hand-tab").forEach((b) => {
  b.addEventListener("click", () => {
    tab = b.dataset.tab;
    mode = null;
    renderBoard();
    renderUnit();
    renderHand();
    $("#hand").scrollLeft = 0;
  });
  b.addEventListener("keydown", (e) => {
    if (["ArrowLeft", "ArrowRight"].includes(e.key)) {
      e.preventDefault();
      const other = $(
        `.hand-tab[data-tab="${tab === "cards" ? "items" : "cards"}"]`,
      );
      other.click();
      other.focus();
    }
  });
});
$("#detail-body").addEventListener("click", (e) => {
  const logToggle = e.target.closest("#log-toggle");
  if (logToggle) showLog(logToggle.dataset.enemyOnly === "true");
  if (e.target.closest('[data-action="roster"]')) showRoster();
  const history = e.target.closest("[data-history]");
  if (history) {
    reviewingAction = view.history[Number(history.dataset.history)];
    closeDetail(); mode = null; selected = null; render();
    toast(reviewingAction.label);
  }
  const reforge = e.target.closest("#reforge-card");
  if (reforge && !reforge.disabled) {
    const action = actions().find(a => a.kind === "reforge" && a.actor === reforge.dataset.index);
    if (action) { closeDetail(); perform(action.id); }
  }
  const play = e.target.closest("#play-card");
  if (play && !play.disabled)
    chooseCard(Number(play.dataset.index), play.dataset.item === "true");
  const gear = e.target.closest("[data-gear-kind]");
  if (gear && !gear.disabled) {
    const choices = actionFor(gear.dataset.gearKind, selected);
    closeDetail();
    if (gear.dataset.gearKind === "horn")
      setMode("item", choices, "领袖号角 · 选择召唤空格");
    else if (choices[0]?.target === "self") perform(choices[0].id);
    else if (choices.length) setMode("item", choices, "装备主动 · 选择高亮目标");
  }
  const hero = e.target.closest("[data-hero]");
  if (hero) {
    selected = hero.dataset.hero;
    closeDetail();
    render();
    showUnit(selectedUnit());
  }
  if (e.target.closest("#open-item-hand")) {
    closeDetail();
    tab = "items";
    renderHand();
  }
  if (e.target.closest("#result-new")) showMatchSetup();
  if (e.target.closest("#confirm-concede")) {
    closeDetail();
    perform("concede");
  }
  if (e.target.closest("#keep-playing")) closeDetail();
  if (e.target.closest("#result-export")) exportMatch();
  if (e.target.closest("#retry-connect")) {
    closeDetail();
    bootstrap();
  }
  if (e.target.closest("#recover-new")) {
    busy = false;
    view = null;
    if (growthCatalog) showMatchSetup();
    else bootstrap();
  }
});
$("#pass-button").addEventListener("click", () => {
  if (!view || busy) return;
  if (view.phase === "finished") showResult();
  else if (view.phase === "round_end") showShop();
  else perform("pass");
});
$("#global-skill").addEventListener("click", () => {
  const { kind, name, cost } = view.globalSkill;
  if (mode?.kind === kind) {
    cancelMode();
    return;
  }
  selected = null;
  const hint = kind === "rally_swap" ? "选择要调位的友军" : "选择要集火的敌军";
  setMode(kind, actions().filter(a => a.kind === kind), `${name} · ${cost} 费 · ${hint}`);
});
$("#close-detail").addEventListener("click", () => { if (!busy) closeDetail(); });
$("#detail-dialog").addEventListener("cancel", (event) => { if (!view || busy) event.preventDefault(); });
$("#detail-dialog").addEventListener("close", () => {
  if (returnFocus?.isConnected) returnFocus.focus({ preventScroll: true });
});
$("#menu-button").addEventListener("click", () => {
  if (!view) return;
  $("#match-summary").textContent =
    view.matchup ? `${view.matchup.player} 对 ${view.matchup.opponent}` : `已进行 ${view.version} 次操作`;
  $("#menu-button").setAttribute("aria-expanded", "true");
  $("#scene-dialog").showModal();
});
$("#close-scene").addEventListener("click", () => $("#scene-dialog").close());
$("#scene-dialog").addEventListener("close", () => {
  $("#menu-button").setAttribute("aria-expanded", "false");
  $("#menu-button").focus({ preventScroll: true });
});
document.querySelectorAll("[data-menu]").forEach((b) =>
  b.addEventListener("click", () => {
    $("#scene-dialog").close();
    ({ roster: showRoster, log: showLog, help: showHelp, export: exportMatch, deck: () => { deckBackToSetup = false; showDeckLibrary(); },
       playtests: showPlaytests, import: () => $("#replay-file").click() })[
      b.dataset.menu
    ]();
  }),
);
$(`[data-menu="${window.ArtifactAPI.browserMode ? "playtests" : "import"}"]`).hidden = false;
$("#replay-file").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  try {
    if (file.size > 2 * 1024 * 1024) throw new Error("对局文件超过 2 MB。");
    const result = await api("/api/replays/import", JSON.parse(await file.text()));
    toast(result.duplicate ? "电脑已有这份对局记录" : result.verified ? "已保存到电脑并验证复演" : "原始记录已保存，规则版本待核对");
  } catch (error) {
    toast(error instanceof SyntaxError ? "请选择有效的 JSON 对局文件" : error.message);
  } finally {
    event.target.value = "";
  }
});
$("#new-game-button").addEventListener("click", () => {
  if (busy) {
    toast("请等当前行动完成");
    return;
  }
  $("#scene-dialog").close();
  showMatchSetup();
});
$("#concede-button").addEventListener("click", () => {
  if (busy) return;
  $("#scene-dialog").close();
  confirmConcede();
});
$("#enemy-info").addEventListener("click", () => {
  if (view) showLog(true);
});
function showFort(f) {
  const prediction = view.phase === "action" ? view.forecast?.forts.find((p) => p.team === f.team) : null;
  openDetail(`<h2 id="detail-title" class="detail-heading">${f.team === 0 ? "我方" : "敌方"}${f.stage === "tower" ? "防御塔" : "基地"}</h2><p class="sheet-note">生命 ${f.hp}/${f.maxHp} · 攻击 ${f.attack} · 每轮攻击一个目标</p><p class="help-copy">位于第 ${f.row + 1} 排中央，占一格，不可通行或部署单位。单位按四正向射程攻击建筑。建筑攻击周围 ${f.reach ?? 2} 格内的一名敌军，含斜角。</p><p class="help-copy">摧毁敌方防御塔即可获胜；双方塔同时被摧毁则平局。泉水本身不能被攻击。</p>${prediction ? `<p class="forecast-detail">当前直接交战：${prediction.destroyed ? f.stage === "tower" ? "预计破塔" : "预计摧毁基地" : `预计剩余 ${prediction.hp} 生命`}。</p>` : ""}`);
}
document.querySelectorAll(".fort").forEach((el) => {
  el.tabIndex = 0;
  el.setAttribute("role", "button");
  const show = () => {
    if (!view) return;
    const f = view.forts.find((f) => f.team === 1);
    showFort(f);
  };
  el.addEventListener("click", show);
  el.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      show();
    }
  });
});
document.querySelectorAll("dialog").forEach((d) =>
  d.addEventListener("click", (e) => {
    if (e.target !== d) return;
    const r = d.getBoundingClientRect();
    if (
      e.clientX < r.left ||
      e.clientX > r.right ||
      e.clientY < r.top ||
      e.clientY > r.bottom
    )
      d.close();
  }),
);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && mode) cancelMode();
});
if (window.ArtifactAPI.browserMode) {
  $("#board").innerHTML = Array.from(
    { length: 40 },
    () => '<span class="cell" aria-hidden="true"></span>',
  ).join("");
}
function fitBoard() {
  const field = $(".battlefield"), frame = $(".board-frame");
  const side = Math.max(1, Math.min((field.clientWidth - 16 - 12 - ((view?.columns || 5)-1)*2)/(view?.columns || 5), (field.clientHeight - 11 - 26)/8));
  frame.style.width = `${side*(view?.columns || 5) + ((view?.columns || 5)-1)*2 + 12}px`;
  frame.style.height = `${side*8 + 26}px`;
  renderUnit();
}
new ResizeObserver(fitBoard).observe($(".battlefield"));
bootstrap();
