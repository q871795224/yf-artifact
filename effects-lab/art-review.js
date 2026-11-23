"use strict";

const $ = (selector) => document.querySelector(selector);
const types = {
  Hero: "英雄", Creep: "单位", Spell: "法术", Signature: "英雄专属", Item: "装备",
  Consumable: "消耗品", Improvement: "改良", Stronghold: "建筑", Pathing: "攻击路径",
  Ability: "主动能力", "Passive Ability": "被动能力", Artwork: "原画",
};
const colors = {red: "红色", green: "绿色", blue: "蓝色", black: "黑色"};
const reviewNames = {revise: "需要修改", keep: "保留"};
const collectionNames = {current: "当前卡池", candidate: "项目候选", classic: "Artifact Classic"};
const storageKey = "yf-artifact-art-review-v1";
const pageSize = 42;
let collections;
let collection = "current";
let entriesByKey;
let filtered = [];
let limit = pageSize;
let selected;
let reviewChanged = false;
let returnFocus;
const comparison = new Map();
let reviews = {};
try {
  reviews = JSON.parse(localStorage.getItem(storageKey) || "{}") || {};
} catch {
  reviews = {};
}

function element(tag, className, content) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (content) node.textContent = content;
  return node;
}

function fillOptions(select, options) {
  select.replaceChildren(...options.map(([value, label]) => new Option(label, value)));
}

function picture(container, image, name, {thumbnail = false, lazy = false} = {}) {
  const src = thumbnail ? image?.thumb : image?.src;
  const missing = element("span", "", src ? "图片暂不可用" : "暂无图片");
  container.replaceChildren(missing);
  if (!src) return;
  missing.hidden = true;
  const img = element("img");
  img.alt = name;
  img.decoding = "async";
  if (lazy) img.loading = "lazy";
  img.addEventListener("error", () => {
    img.hidden = true;
    missing.hidden = false;
  }, {once: true});
  img.src = src;
  container.prepend(img);
}

function cover(entry) {
  if (collection === "classic" && $("#source").value === "unframed") {
    return entry.images.find((image) => image.label === "Classic 无框原画");
  }
  return entry.images[0];
}

function shortInfo(entry) {
  return [types[entry.kind] || entry.kind, ...entry.colors.map((color) => colors[color]),
    entry.batch || (collection === "current" ? (entry.own ? "项目用图" : "沿用 Classic") : ""),
    typeof entry.id === "number" ? `#${entry.id}` : ""].filter(Boolean).join(" / ");
}

function tile(entry) {
  const article = element("article", "tile");
  article.dataset.color = entry.colors[0] || "";
  const open = element("button", "tile-open");
  open.dataset.open = entry.key;
  open.setAttribute("aria-label", `查看 ${entry.name}`);
  const image = element("div", "tile-image");
  picture(image, cover(entry), entry.name, {thumbnail: true, lazy: true});
  const caption = element("div", "tile-caption");
  caption.append(element("h3", "", entry.name), element("p", "", shortInfo(entry)));
  const marker = reviewNames[reviews[entry.key]?.status];
  if (marker) caption.append(element("p", "marker", marker));
  open.append(image, caption);

  const pin = element("button", "compare-pin", "＋");
  pin.dataset.pin = entry.key;
  pin.setAttribute("aria-label", `${entry.name}，选择对照`);
  article.append(open, pin);
  return article;
}

function synchronizePins() {
  for (const button of document.querySelectorAll("[data-pin]")) {
    const pinned = comparison.has(button.dataset.pin);
    button.setAttribute("aria-pressed", String(pinned));
    button.textContent = pinned ? "✓" : "＋";
    button.title = pinned ? "移出对照" : "加入对照";
  }
  const count = comparison.size;
  $("#compare-count").textContent = `${count}/2`;
  $("#compare-open").disabled = count !== 2;
  if (selected) {
    const pinned = comparison.has(selected.key);
    $("#detail-compare").setAttribute("aria-pressed", String(pinned));
    $("#detail-compare").textContent = pinned ? "移出对照" : "加入对照";
  }
}

function renderGallery(append = false) {
  const gallery = $("#gallery");
  if (!append) gallery.replaceChildren();
  if (!filtered.length) {
    gallery.append(element("p", "empty", "没有符合条件的素材。试试调整搜索或筛选。"));
  } else {
    const start = append ? gallery.children.length : 0;
    gallery.append(...filtered.slice(start, limit).map(tile));
  }
  $("#result-status").textContent = `${filtered.length} 条素材`;
  $("#load-more").hidden = filtered.length <= limit;
  synchronizePins();
}

function applyFilters() {
  if (!collections) return;
  const query = $("#search").value.trim().toLowerCase();
  const kind = $("#type").value;
  const color = $("#color").value;
  const source = $("#source").value;
  const review = $("#review").value;
  filtered = collections[collection].filter((entry) => {
    const status = reviews[entry.key]?.status || "new";
    const searchable = [entry.name, entry.english, entry.id, entry.hero, entry.inspiration,
      ...entry.images.map((image) => image.label)].join(" ").toLowerCase();
    return (!query || searchable.includes(query))
      && (!kind || kind === entry.kind)
      && (!color || (color === "neutral" ? !entry.colors.length : entry.colors.includes(color)))
      && (!review || review === status)
      && (!source || (collection === "current" && (source === "own" ? entry.own : !entry.own))
        || (collection === "candidate" && source === entry.batch)
        || (collection === "classic" && (source === "unframed"
          ? entry.images.some((image) => image.label === "Classic 无框原画")
          : entry.images[0]?.src.startsWith("../"))));
  });
  limit = pageSize;
  renderGallery();
}

function switchCollection(key) {
  collection = key;
  for (const button of document.querySelectorAll("[data-collection]")) {
    button.setAttribute("aria-pressed", String(button.dataset.collection === key));
  }
  const kinds = new Set(collections[key].map((entry) => entry.kind));
  fillOptions($("#type"), [["", "全部类型"], ...Object.entries(types).filter(([kind]) => kinds.has(kind))]);
  const label = $("#source-label");
  label.firstChild.textContent = {current: "用图", candidate: "批次", classic: "版本"}[key];
  const sources = {
    current: [["", "所有图片"], ["own", "有项目立绘"], ["classic", "沿用 Classic"]],
    candidate: [["", "全部批次"], ...[...new Set(collections.candidate.map((entry) => entry.batch))]
      .map((batch) => [batch, batch])],
    classic: [["", "全部版本"], ["unframed", "无框原画"], ["local", "本地可看"]],
  };
  fillOptions($("#source"), sources[key]);
  applyFilters();
}

function detailPicture() {
  const image = selected.images[Number($("#detail-version").value)];
  picture($("#detail-picture"), image, selected.name);
  const link = $("#open-image");
  link.hidden = !image?.src;
  if (image?.src) link.href = image.src;
  else link.removeAttribute("href");
}

function openDetail(entry, trigger) {
  selected = entry;
  returnFocus = trigger;
  reviewChanged = false;
  const owner = entry.key.split(":")[0];
  $("#detail-title").textContent = entry.name;
  $("#detail-meta").textContent = [collectionNames[owner] || collectionNames.candidate,
    types[entry.kind] || entry.kind, ...entry.colors.map((color) => colors[color]),
    entry.english, `ID ${entry.id}`].filter(Boolean).join(" / ");
  const stats = [];
  if (entry.mana_cost) stats.push(`${entry.mana_cost} 法力`);
  if (entry.gold_cost) stats.push(`${entry.gold_cost} 金币`);
  if (entry.hit_points > 0) stats.push(`攻击 ${entry.attack ?? 0} / 护甲 ${entry.armor ?? 0} / 生命 ${entry.hit_points}`);
  if (entry.hero) stats.push(`${entry.hero}的专属`);
  const levels = entry.levels?.map((level, i) => `Lv${i + 1} ${level.join("/")}`).join("　");
  const copy = [stats.join("　"), entry.text, levels ? `成长（攻／甲／血）${levels}` : "",
    entry.inspiration ? `题材灵感 ${entry.inspiration}` : ""];
  $("#card-copy").replaceChildren(...copy.filter(Boolean).map((text) => element("p", "card-copy", text)));
  fillOptions($("#detail-version"), entry.images.map((image, index) => [index, image.label]));
  if (entry.images.includes(cover(entry))) $("#detail-version").value = entry.images.indexOf(cover(entry));
  $("#detail-version").disabled = entry.images.length < 2;
  $("#detail-review").value = reviews[entry.key]?.status || "";
  $("#detail-note").value = reviews[entry.key]?.note || "";
  $("#note-status").textContent = "意见保存在当前浏览器。";
  detailPicture();
  synchronizePins();
  $("#detail").showModal();
}

function saveReview() {
  reviewChanged = true;
  const status = $("#detail-review").value;
  const note = $("#detail-note").value;
  if (status || note) reviews[selected.key] = {status, note};
  else delete reviews[selected.key];
  try {
    localStorage.setItem(storageKey, JSON.stringify(reviews));
    $("#note-status").textContent = "已保存到当前浏览器。";
  } catch {
    $("#note-status").textContent = "当前浏览器无法保存意见。";
  }
}

function pinEntry(entry, image = cover(entry)) {
  if (comparison.has(entry.key)) comparison.delete(entry.key);
  else if (comparison.size === 2) {
    // Replace the earliest selection to keep comparing across collections quick.
    comparison.delete(comparison.keys().next().value);
    comparison.set(entry.key, {entry, image});
    $("#compare-status").textContent = `已将第一张替换为${entry.name}。`;
  } else comparison.set(entry.key, {entry, image});
  synchronizePins();
}

function showComparison() {
  const images = [...comparison.values()].map(({entry, image}) => {
    const figure = element("figure");
    const panel = element("div", "comparison-picture");
    const caption = element("figcaption");
    const version = element("select");
    version.setAttribute("aria-label", `${entry.name}的图片版本`);
    fillOptions(version, entry.images.map((art, index) => [index, art.label]));
    version.value = entry.images.indexOf(image);
    version.disabled = entry.images.length < 2;
    version.addEventListener("change", () => picture(panel, entry.images[Number(version.value)], entry.name));
    caption.append(element("b", "", entry.name), version);
    figure.append(panel, caption);
    picture(panel, image, entry.name);
    return figure;
  });
  $("#compare-images").replaceChildren(...images);
  $("#compare").showModal();
}

document.addEventListener("click", (event) => {
  const tab = event.target.closest("[data-collection]");
  const open = event.target.closest("[data-open]");
  const pin = event.target.closest("[data-pin]");
  const close = event.target.closest("[data-close]");
  if (tab && collections) switchCollection(tab.dataset.collection);
  if (open) openDetail(entriesByKey.get(open.dataset.open), open);
  if (pin) pinEntry(entriesByKey.get(pin.dataset.pin));
  if (close) close.closest("dialog").close();
});
for (const id of ["search", "type", "color", "source", "review"]) {
  $(`#${id}`).addEventListener("input", applyFilters);
}
$("#load-more").addEventListener("click", () => {
  limit += pageSize;
  renderGallery(true);
});
$("#small-view").addEventListener("click", () => {
  const small = $("#small-view").getAttribute("aria-pressed") !== "true";
  $("#small-view").setAttribute("aria-pressed", String(small));
  $("#gallery").dataset.small = small;
});
$("#compare-open").addEventListener("click", showComparison);
$("#detail-version").addEventListener("change", detailPicture);
$("#detail-review").addEventListener("change", saveReview);
$("#detail-note").addEventListener("input", saveReview);
$("#detail-compare").addEventListener("click", () => pinEntry(selected, selected.images[Number($("#detail-version").value)]));
$("#detail").addEventListener("close", () => {
  if (reviewChanged) {
    const scroll = window.scrollY;
    const shown = limit;
    applyFilters();
    if (shown > limit) {
      limit = shown;
      renderGallery(true);
    }
    window.scrollTo(0, scroll);
  }
  if (!returnFocus.isConnected) {
    returnFocus = document.querySelector(`[data-open="${CSS.escape(returnFocus.dataset.open)}"]`) || $("#search");
  }
  returnFocus.focus({preventScroll: true});
});

fetch("../output/art-review/index.json", {cache: "no-cache"})
  .then((response) => {
    if (!response.ok) throw new Error("素材索引未就绪");
    return response.json();
  })
  .then((data) => {
    collections = data.collections;
    entriesByKey = new Map(Object.values(collections).flat().map((entry) => [entry.key, entry]));
    for (const button of document.querySelectorAll("[data-collection]")) {
      button.querySelector("span").textContent = collections[button.dataset.collection].length;
    }
    for (const id of ["porcelain-roll-champion", "dawn-rekindling-crane", "five-point-lightning"]) {
      const entry = collections.candidate.find((item) => item.id === id);
      if (!entry) continue;
      const button = element("button");
      button.setAttribute("aria-label", `查看候选插画 ${entry.name}`);
      button.dataset.open = entry.key;
      picture(button, entry.images[0], entry.name, {thumbnail: true});
      $("#featured").append(button);
    }
    switchCollection("current");
  })
  .catch((error) => {
    console.error(error);
    $("#result-status").textContent = "素材加载失败。请运行 python3 scripts/build_art_review.py 后刷新。";
  });
