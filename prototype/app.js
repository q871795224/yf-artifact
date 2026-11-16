/* The Python match engine is authoritative. This file only presents its state. */
"use strict";
const ASSETS = "../references/artifact-classic/assets/";
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
const image = (id, kind = "mini_image") => `${ASSETS}${kind}/${id}.png`;
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
    text: "八个方向中选择一个，眩晕该直线前两格敌人，持续本回合。冷却 4 回合，不花费法力。",
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
  10352: "对敌方当前防御塔或基地造成 6 点伤害。新出现的基地在下回合才能受伤。",
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
const storageKey = "yf-artifact-match-v1";
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
function toast(text) {
  clearTimeout(toastTimer);
  $("#toast").textContent = text;
  $("#toast").hidden = false;
  toastTimer = setTimeout(() => ($("#toast").hidden = true), 3000);
}
async function api(path, body) {
  return window.ArtifactAPI.request(path, body);
}
function stats(u) {
  return `<span class="stat atk ${u.attack > (CARDS[u.id]?.attack || 0) ? "buffed" : ""}">${icon("sword")}${u.attack}</span><span class="stat hp">${icon("heart")}${u.hp}</span>`;
}
function targetAt(row, col) {
  if (!mode) return [];
  const unit = view.units.find((u) => u.row === row && u.col === col);
  return mode.choices.filter((a) => {
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
    if (a.row !== undefined) return a.row === row && a.col === col;
    return unit && a.target === unit.key;
  });
}
function renderBoard(previous) {
  if (!view) return;
  const cells = [];
  const focus = selectedUnit();
  for (let row = 0; row < 8; row++)
    for (let col = 0; col < 6; col++) {
      const u = view.units.find((u) => u.row === row && u.col === col);
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
        classes.push(
          "occupied",
          u.hero ? "hero" : "creep",
          u.key === selected ? "selected" : "",
          u.stunned ? "stunned" : "",
          focus?.target === u.key ? "current-target" : "",
        );
        content = `<img class="unit-art" src="${image(u.id)}" alt=""><span class="unit-vignette"></span><span class="allegiance"></span>${u.hero ? pip(u.id) : ""}<span class="unit-stats">${stats(u)}</span>${u.armor ? `<span class="armor-badge">${icon("shield")}${u.armor}</span>` : ""}${u.stunned ? '<span class="stun-badge">✦</span>' : ""}`;
        if (u.key === selected && u.arrow && !mode) {
          const rotations = { "↑": 0, "↓": 180, "←": -90, "→": 90 };
          const positions = {
            "↑": "left:calc(50% - 5px);top:-10px",
            "↓": "left:calc(50% - 5px);top:calc(100% - 7px)",
            "←": "left:-9px;top:calc(50% - 9px)",
            "→": "left:calc(100% - 1px);top:calc(50% - 9px)",
          };
          content += `<span class="intent" style="${positions[u.arrow]};transform:rotate(${rotations[u.arrow]}deg)">${icon("arrow")}</span>`;
        }
      }
      const possible = targetAt(row, col);
      if (possible.length)
        classes.push(
          mode.kind === "move"
            ? "reachable"
            : mode.kind === "skill"
              ? "skill-range"
              : "targetable",
        );
      const old = previous?.units.find((p) => p.key === u?.key);
      if (u && previous) {
        if (!old) classes.push("unit-arrived");
        else if (old.hp !== u.hp) {
          classes.push(u.hp < old.hp ? "unit-hit" : "unit-healed");
          content += `<span class="hp-change ${u.hp < old.hp ? "loss" : "gain"}">${u.hp > old.hp ? "+" : ""}${u.hp - old.hp}</span>`;
        }
      }
      if (!u && previous) {
        const dead = previous.units.find(
          (p) =>
            p.row === row &&
            p.col === col &&
            !view.units.some((n) => n.key === p.key),
        );
        if (dead)
          content += `<span class="death-marker"><img src="${image(dead.id)}" alt=""><b>阵亡</b></span>`;
      }
      const label = `第${row + 1}排第${col + 1}列${u ? `，${u.team === "ally" ? "我方" : "敌方"}${cardName(u.id)}，攻击${u.attack}，生命${u.hp}${u.stunned ? "，眩晕" : ""}` : "，空位"}`;
      cells.push(
        `<button class="${classes.filter(Boolean).join(" ")}" data-row="${row}" data-col="${col}" ${u ? `data-unit="${u.key}" data-team="${u.team}" aria-pressed="${u.key === selected}"` : ""} aria-label="${label}">${content}</button>`,
      );
    }
  $("#board").innerHTML = cells.join("");
}
function renderUnit() {
  const u = selectedUnit();
  if (mode) {
    const id = mode.choices[0].card_id || u?.id || 10020;
    $("#unit-panel").innerHTML =
      `<img class="selected-portrait" src="${image(id)}" alt=""><div class="target-instructions" role="status"><b>选择${mode.kind === "move" ? "移动位置" : "目标"}</b><span>${esc(mode.hint)}</span></div><button class="cancel-target" data-action="cancel">取消</button>`;
    return;
  }
  if (!u) {
    $("#unit-panel").innerHTML =
      `<span class="idle-panel">点选棋子查看状态，或让过进入交战。</span><button class="view-unit-button" data-action="roster">阵容</button>`;
    return;
  }
  const meta = HEROES[u.id];
  const mine = u.team === "ally" && u.hero && u.row !== null;
  const move = actionFor("move", u.key),
    skill = meta?.kind ? actionFor(meta.kind, u.key) : [];
  let controls =
    '<button class="view-unit-button" data-action="detail">查看详情</button>';
  if (mine)
    controls = `<div class="unit-actions"><button class="action-button ${mode?.kind === "move" ? "active" : ""}" data-action="move" ${move.length ? "" : "disabled"} aria-label="${u.moved ? "本回合已移动" : "移动"}">${icon("move")}<span>${u.moved ? "已移动" : "移动"}</span></button><button class="action-button ${mode?.kind === "skill" ? "active" : ""}" data-action="skill" ${skill.length ? "" : "disabled"} aria-label="${meta?.skill || "无主动技能"}">${u.cooldown ? `<small class="cooldown">${u.cooldown}</small>` : ""}${icon("fissure")}<span>${meta?.skill || "被动"}</span></button><button class="action-button" data-action="equipment">${icon("shield")}<span>装备${u.equipment.length ? ` ${u.equipment.length}` : ""}</span></button></div>`;
  $("#unit-panel").innerHTML =
    `<button class="selected-portrait ${u.row === null ? "dead-portrait" : ""}" data-action="detail" aria-label="查看${cardName(u.id)}详情"><img src="${image(u.id)}" alt=""></button><div class="unit-summary"><div class="unit-name">${u.hero ? pip(u.id) : ""}${cardName(u.id)}</div><div class="summary-stats">${u.row === null ? `<span class="return-label">第 ${u.due} 回合登场</span>` : stats(u)}</div></div>${controls}`;
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
    if (c.mana_cost > view.mana)
      return `需要 ${c.mana_cost} 法力，当前 ${view.mana}`;
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
          cost = item ? (paid ? 0 : c.gold_cost) : c.mana_cost;
        const usable = actions().some(
          (a) => a.kind === (item ? "item" : "card") && a.index === index,
        );
        return `<button class="hand-card identity-${identity(id)} ${item ? "item-card" : ""} ${usable ? "" : "unavailable"}" data-card="${id}" data-index="${index}" data-item="${item}" aria-label="${cardName(id)}，${cost}${item ? "金币" : "法力"}，查看详情"><span class="card-art"><img src="${image(id)}" alt=""></span><span class="card-cost">${cost}</span><span class="hand-card-title">${cardName(id)}</span>${item ? "" : pip(id)}<span class="card-kind">${paid ? "已付费" : item ? (c.sub_type === "Consumable" ? "消耗品" : "装备") : c.card_type === "Creep" ? "单位" : "法术"}</span></button>`;
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
    selected = view.units.find((u) => u.team === "ally" && u.hero)?.key || null;
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
  $("#gold-value").textContent = view.gold;
  view.forts.forEach((f) => {
    const el = $(f.team === 0 ? ".ally-fort" : ".enemy-fort");
    el.querySelector("b").innerHTML = `${f.hp}<span>/${f.maxHp}</span>`;
    el.querySelector("i").style.width =
      `${Math.max(0, (f.hp / f.maxHp) * 100)}%`;
    el.querySelector(".fort-caption").textContent =
      `${f.team === 0 ? "我" : "敌"}${f.stage === "tower" ? "塔" : "基地"}`;
    el.classList.toggle("fort-immune", !f.ready);
    el.setAttribute(
      "aria-label",
      `${f.team === 0 ? "我方" : "敌方"}${f.stage === "tower" ? "防御塔" : "基地"}，生命${f.hp}，攻击${f.attack}${f.ready ? "" : "，下回合激活"}`,
    );
  });
  const footer = $("#pass-button");
  footer.disabled = busy;
  footer.innerHTML = `${busy ? "请稍候" : view.phase === "round_end" ? "下一回合" : view.phase === "finished" ? "查看结果" : "让过"}${icon("arrow")}`;
  footer.classList.toggle("next-round", view.phase === "round_end");
  footer.classList.toggle(
    "long-label",
    ["round_end", "finished"].includes(view.phase),
  );
  $("#concede-button").hidden = view.phase === "finished";
  const dead = view.heroes.filter((h) => h.team === "ally" && h.row === null);
  $("#enemy-info").setAttribute(
    "aria-label",
    `阵容与返场${dead.length ? `，${dead.length}名英雄等待登场` : ""}`,
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
  if (!$("#detail-dialog").open) returnFocus = document.activeElement;
  $("#detail-body").innerHTML = content;
  if (!$("#detail-dialog").open) $("#detail-dialog").showModal();
}
function closeDetail() {
  $("#detail-dialog").close();
}
function targetDescription(u) {
  if (u.stunned) return "眩晕，本回合无法普攻";
  if (!u.target) return "射程内暂无普攻目标";
  if (u.target === "AF" || u.target === "BF")
    return `普攻${u.team === "ally" ? "敌方" : "我方"}建筑`;
  return `普攻目标：${cardName(view.units.find((x) => x.key === u.target)?.id)}`;
}
function showUnit(u) {
  if (!u) return;
  const gear = u.equipment.map((e) => cardName(e.id)).join("、");
  openDetail(
    `<h2 id="detail-title" class="detail-heading">${u.hero ? pip(u.id) : ""}${cardName(u.id)}</h2><p class="detail-subtitle">${u.team === "ally" ? "我方" : "敌方"}${u.hero ? "英雄" : "单位"} · ${u.row === null ? `等待第 ${u.due} 回合登场` : `第 ${u.row + 1} 排，第 ${u.col + 1} 列`}</p><div class="detail-layout"><img class="detail-art" src="${image(u.id, "large_image")}" alt="${cardName(u.id)}原版卡面"><div class="detail-copy"><div class="detail-stats">${stats(u)}${u.armor ? `<span class="stat">${icon("shield")}${u.armor}</span>` : ""}</div><p>${esc(HEROES[u.id]?.text || CARDS[u.id].card_text.schinese || "近战一格，自动移动与交战。")}</p><p class="detail-muted">射程 ${u.range} 格${u.siege ? ` · 攻城 ${u.siege}` : ""}${u.cleave ? ` · 顺势 ${u.cleave}` : ""}${u.regeneration ? ` · 恢复 ${u.regeneration}` : ""}</p>${u.row !== null ? `<p class="detail-muted">${esc(targetDescription(u))}</p>` : ""}${gear ? `<p class="detail-muted">装备：${esc(gear)}</p>` : ""}${u.cooldown ? `<p class="detail-muted">技能冷却 ${u.cooldown} 回合</p>` : ""}</div></div><p class="detail-note">原版完整卡面供参考，当前能力和攻血以战场数值为准。</p>`,
  );
}
function showEquipment(u) {
  const entries = u.equipment
    .map((e) => {
      const kind = e.id === 10260 ? "horn" : e.id === 10263 ? "blade" : null;
      const choices = kind ? actionFor(kind, u.key) : [];
      return `<div class="gear-row"><img src="${image(e.id)}" alt=""><span><b>${cardName(e.id)}</b><small>${SLOT_NAMES[e.slot] || e.slot}${e.cooldown !== null ? ` · ${e.cooldown ? `冷却 ${e.cooldown}` : "主动就绪"}` : ""}</small></span>${kind ? `<button class="gear-active" data-gear-kind="${kind}" ${choices.length ? "" : "disabled"}>使用</button>` : ""}</div>`;
    })
    .join("");
  openDetail(
    `<h2 id="detail-title" class="detail-heading">${cardName(u.id)}的装备</h2><p class="sheet-note">每类槽位一件，新装备替换同槽旧装备。阵亡后保留。</p>${entries || '<p class="sheet-note">暂未穿戴装备。</p>'}<button class="detail-action" id="open-item-hand">查看物品手牌</button>`,
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
    cost = item ? (view.items[index].paid ? 0 : c.gold_cost) : c.mana_cost;
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
    `<h2 id="detail-title" class="detail-heading">${item ? "" : pip(id)}${cardName(id)}</h2><p class="detail-subtitle">${item ? "物品 · 金币支付" : "普通牌 · 法力支付"}</p><div class="detail-layout"><img class="detail-art" src="${image(id, "large_image")}" alt="${cardName(id)}原版卡面"><div class="detail-copy"><div class="detail-cost ${item ? "item" : ""}">${icon(item ? "coin" : "mana")}${cost}</div><p>${esc(RULES[id] || c.card_text.schinese).replace(/\n+/g, "<br>")}</p>${item && c.sub_type !== "Consumable" ? '<p class="detail-muted">穿戴占一次行动；替换同槽旧装备。</p>' : ""}${c.card_type === "Creep" ? `<div class="detail-stats">${icon("sword")}${c.attack}${icon("heart")}${c.hit_points}</div>` : ""}</div></div><button class="detail-action" id="play-card" data-id="${id}" data-index="${index}" data-item="${item}" ${choices.length ? "" : "disabled"}>${esc(label)}</button>`,
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
      ? `${cardName(id)} · 选择部署空格`
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
    const choices = actionFor(HEROES[u.id]?.kind, u.key);
    if (choices.length)
      setMode(
        "skill",
        choices,
        u.id === 10033
          ? "沟壑 · 八向选一，直线前两格"
          : `${HEROES[u.id].skill} · 选择目标`,
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
  if (mode) {
    const choices = targetAt(row, col);
    if (choices.length) {
      mode = null;
      perform(choices[0].id);
    } else toast("请选择高亮位置，或点取消");
    return;
  }
  if (u) {
    selected = u.key;
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
              `<button class="roster-unit ${h.row === null ? "waiting" : ""}" data-hero="${h.key}"><img src="${image(h.id)}" alt=""><span>${pip(h.id)}${cardName(h.id)}<small>${h.row === null ? `第 ${h.due} 回合登场` : h.stunned ? "眩晕，仍提供出牌颜色" : `在场 · ${h.hp}/${h.maxHp} 生命`}${h.cooldown ? ` · CD ${h.cooldown}` : ""}</small></span></button>`,
          )
          .join("")}</div>`,
    )
    .join("");
  openDetail(
    `<h2 id="detail-title" class="detail-heading">阵容与返场</h2>${groups}<p class="detail-note">死亡后跳过下一回合，再下一回合从泉水返场。泉水可用空位不足时，自动替换己方生命最低的小兵。</p>`,
  );
}
function showLog() {
  openDetail(
    `<h2 id="detail-title" class="detail-heading">行动记录</h2><p class="sheet-note">最近 ${view.log.length} 条记录 · 第 ${view.round} 回合</p><div class="action-log">${
      view.log
        .slice()
        .reverse()
        .map((e) => `<p><span>${e.round}</span>${esc(e.text)}</p>`)
        .join("") || "暂无记录"
    }</div>`,
  );
}
function showHelp() {
  openDetail(
    `<h2 id="detail-title" class="detail-heading">单路战场</h2><div class="help-copy"><p><b>行动：</b>打牌、移动英雄、使用技能、穿戴或使用装备，每次占一个行动，随后由对手回应。普通攻击自动进行，无需手动选择攻击。</p><p><b>交战：</b>双方连续让过后，所有单位与建筑同时结算攻击。交战后可查看损伤，点击“下一回合”继续。</p><p><b>移动：</b>英雄每回合移动一次，平时八邻一格；从泉水出生／返场后的首次移动最多两格，不能穿过单位。小兵自动向前推进。</p><p><b>出牌：</b>普通牌需要对应颜色英雄在场；眩晕仍提供颜色。法力每回合刷新并增加一点，最高 10。</p><p><b>金币：</b>无工资，敌方小兵死亡 +1，英雄死亡 +5。物品花金币；开局发一张，此后每三回合再发一张。</p><p><b>装备：</b>武器、护甲、饰品各一件，同类替换。主动效果不花资源，有冷却，阵亡后装备保留。</p><p><b>胜负：</b>先摧毁 40 血防御塔，再摧毁同位置的 80 血基地。基地下一回合激活。塔攻击 4，基地攻击 8；进入敌方泉水会受到 10 点范围伤害。</p><p>当前固定阵容与候选牌池，双方交替获得每回合先手。右上角可查看记录和导出本局。</p></div>`,
  );
}
function showResult() {
  const won = view.winner === 0,
    draw = view.winner === null;
  const title = draw
    ? "同归于尽"
    : won
      ? "基地已摧毁 · 胜利"
      : view.endReason === "conceded"
        ? "本局认输"
        : "基地失守 · 失利";
  const stats = view.stats[0];
  openDetail(
    `<div class="result-mark">${icon("tower")}</div><h2 id="detail-title" class="result-title">${title}</h2><p class="result-subtitle">${view.endReason === "conceded" ? "你结束了这场对局" : draw ? "双方基地同时被摧毁" : won ? "敌方基地已被摧毁" : "我方基地已被摧毁"}</p><div class="result-stats"><span><b>${view.round}</b>回合</span><span><b>${stats.hero_kills || 0}</b>英雄击杀</span><span><b>${stats.gold_spent || 0}</b>花费金币</span></div><button class="detail-action" id="result-new">再来一局</button><button class="quiet-button" id="result-export">导出本局记录</button>`,
  );
}
async function exportMatch() {
  try {
    const data = await api(`/api/games/${gameId}/export`);
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob),
      link = document.createElement("a");
    link.href = url;
    link.download = `artifact-${data.seed}-round-${data.round}.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast("对局记录已导出");
  } catch (e) {
    toast(e.message);
  }
}
function confirmNew() {
  openDetail(
    `<h2 id="detail-title" class="detail-heading">开始新一局？</h2><p class="sheet-note">当前浏览器将切换到新对局。需要保留这局时，可以先导出记录。</p><button class="detail-action" id="confirm-new">开始新一局</button><button class="quiet-button" id="keep-playing">继续当前对局</button>`,
  );
}
function confirmConcede() {
  openDetail(
    `<h2 id="detail-title" class="detail-heading">认输并结束本局？</h2><p class="sheet-note">本局会记为失利，仍可查看和导出对局记录。</p><button class="detail-action" id="confirm-concede">确认认输</button><button class="quiet-button" id="keep-playing">继续战斗</button>`,
  );
}
async function applyPacket(packet, animate = false) {
  gameId = packet.game_id;
  rememberId(gameId);
  mode = null;
  if (animate)
    for (const frame of packet.frames) {
      const previous = view;
      view = { ...packet.state, ...frame, actions: [] };
      render(previous);
      toast(frame.label);
      await delay(frame.phase === "combat" ? 700 : 330);
    }
  const previous = view;
  view = packet.state;
  busy = false;
  render(previous);
  if (view.phase === "finished") showResult();
  else if (view.phase === "round_end") toast("交战结束 · 点击下一回合继续");
  else if (animate && !packet.frames.length) toast(view.label);
}
async function perform(id) {
  if (busy || !view) return;
  clearTimeout(toastTimer);
  $("#toast").hidden = true;
  busy = true;
  mode = null;
  render();
  const sequence = ++requestSequence;
  try {
    const packet = await api(`/api/games/${gameId}/actions`, {
      version: view.version,
      action_id: id,
    });
    if (sequence === requestSequence) await applyPacket(packet, true);
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
    `<h2 id="detail-title" class="detail-heading">重新载入战场</h2><p class="sheet-note">${esc(window.ArtifactAPI.browserMode ? error.message : error.status === 404 ? "服务重启后，上一局记录已清空。你可以开始新一局。" : "请确认电脑上的游戏服务仍在运行，手机和电脑处于同一网络。")}</p><button class="detail-action" id="retry-connect">重试</button><button class="quiet-button" id="recover-new">开始新一局</button>`,
  );
}
async function createGame() {
  if (busy && view) return;
  busy = true;
  mode = null;
  selected = null;
  tab = "cards";
  $("#hand").scrollLeft = 0;
  closeDetail();
  $("#scene-dialog").close();
  if (view) render();
  try {
    await applyPacket(await api("/api/games", {}));
    toast("对局开始 · 双方每次行动后交替操作");
  } catch (error) {
    showReconnect(error);
  }
}
async function bootstrap() {
  busy = true;
  gameId = savedId();
  try {
    if (gameId) await applyPacket(await api(`/api/games/${gameId}`));
    else await createGame();
  } catch (error) {
    if (error.status === 404) {
      gameId = null;
      rememberId(null);
      view = null;
      await createGame();
      toast(
        window.ArtifactAPI.browserMode
          ? "已开始一场新的浏览器对局"
          : "服务已重新启动，已开始一场新对局",
      );
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
  const play = e.target.closest("#play-card");
  if (play && !play.disabled)
    chooseCard(Number(play.dataset.index), play.dataset.item === "true");
  const gear = e.target.closest("[data-gear-kind]");
  if (gear && !gear.disabled) {
    const choices = actionFor(gear.dataset.gearKind, selected);
    closeDetail();
    if (gear.dataset.gearKind === "horn")
      setMode("item", choices, "领袖号角 · 选择召唤空格");
    else perform(choices[0].id);
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
  if (e.target.closest("#confirm-new") || e.target.closest("#result-new")) {
    busy = false;
    createGame();
  }
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
    createGame();
  }
});
$("#pass-button").addEventListener("click", () => {
  if (!view || busy) return;
  if (view.phase === "finished") showResult();
  else perform(view.phase === "round_end" ? "next_round" : "pass");
});
$("#close-detail").addEventListener("click", closeDetail);
$("#detail-dialog").addEventListener("close", () => {
  if (returnFocus?.isConnected) returnFocus.focus({ preventScroll: true });
});
$("#menu-button").addEventListener("click", () => {
  if (!view) return;
  $("#match-summary").textContent =
    `第 ${view.round} 回合 · 已进行 ${view.version} 次操作`;
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
    ({ roster: showRoster, log: showLog, help: showHelp, export: exportMatch })[
      b.dataset.menu
    ]();
  }),
);
$("#new-game-button").addEventListener("click", () => {
  if (busy) {
    toast("请等当前行动完成");
    return;
  }
  $("#scene-dialog").close();
  confirmNew();
});
$("#concede-button").addEventListener("click", () => {
  if (busy) return;
  $("#scene-dialog").close();
  confirmConcede();
});
$("#enemy-info").addEventListener("click", () => {
  if (view) showRoster();
});
document.querySelectorAll(".fort").forEach((el) => {
  el.tabIndex = 0;
  el.setAttribute("role", "button");
  const show = () => {
    if (!view) return;
    const f = view.forts[el.classList.contains("ally-fort") ? 0 : 1];
    openDetail(
      `<h2 id="detail-title" class="detail-heading">${f.team === 0 ? "我方" : "敌方"}${f.stage === "tower" ? "防御塔" : "基地"}</h2><p class="sheet-note">生命 ${f.hp}/${f.maxHp} · 攻击 ${f.attack} · 每轮攻击一个目标</p><p class="help-copy">${f.ready ? "优先保持合法仇恨，范围内敌方英雄攻击我方英雄时会保护转火。" : "刚出现的基地将在下回合开始后激活，本回合不会攻击或受到伤害。"}</p>`,
    );
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
    { length: 48 },
    () => '<span class="cell" aria-hidden="true"></span>',
  ).join("");
}
bootstrap();
