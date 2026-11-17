"use strict";
(() => {
  const $ = (s) => document.querySelector(s);
  const root = "../references/artifact-classic/";
  const escape = (s) => String(s).replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[c]);
  const types = { Hero: "英雄", Creep: "小兵／召唤单位", Spell: "法术", Item: "物品", Improvement: "改良", Stronghold: "建筑", Pathing: "攻击路径" };
  let cards = [], selected = null, returnFocus = null;
  const local = new Set(), originals = new Map();
  const name = (c) => c.card_name.schinese || c.card_name.english;
  const remote = (c, kind) => c.custom_images?.[kind] || c[kind]?.schinese || c[kind]?.def || c[kind]?.english || Object.values(c[kind] || {})[0];
  const source = (c, kind) => c.custom_images?.[kind] || (local.has(`${c.card_id}:${kind}`) ? `${root}assets/mobile/${kind}/${c.card_id}.webp` : remote(c, kind));
  function preview() {
    if (!selected) return;
    const kind = $("#asset-kind").value, url = source(selected, kind);
    $("#asset-preview").hidden = !url;
    $("#asset-open").hidden = !url;
    $("#asset-image-status").textContent = url ? (local.has(`${selected.card_id}:${kind}`) ? "本地图片" : "远程图片 · 需要联网") : "这张卡牌没有此版本图片";
    if (url) { $("#asset-preview").src = url; $("#asset-open").href = originals.get(`${selected.card_id}:${kind}`) || url; }
    else $("#asset-preview").removeAttribute("src");
  }
  function select(id) {
    selected = cards.find((c) => String(c.card_id) === String(id));
    returnFocus = document.activeElement;
    $("#asset-title").textContent = name(selected);
    $("#asset-description").textContent = `${selected.card_name.english || ""} · ${types[selected.card_type] || selected.card_type} · ID ${id}${selected.custom_images ? " · 自制素材" : ""}`;
    $("#asset-kind").value = $("#asset-view").value;
    $("#asset-preview").alt = `${name(selected)}素材`;
    preview();
    $("#asset-dialog").showModal();
  }
  function render() {
    const query = $("#asset-search").value.trim().toLowerCase(), type = $("#asset-type").value, kind = $("#asset-view").value;
    const filtered = cards.filter((c) => remote(c, kind) && (!type || c.card_type === type) && (!query || `${name(c)} ${c.card_name.english} ${c.card_id}`.toLowerCase().includes(query)) && ($("#asset-source").value !== "local" || local.has(`${c.card_id}:${kind}`)));
    $("#asset-status").textContent = `${filtered.length} 张素材 · 点击卡牌放大查看`;
    $("#asset-grid").dataset.kind = kind;
    $("#asset-grid").innerHTML = filtered.map((c) => `<button class="asset-tile" data-id="${c.card_id}" aria-label="查看${escape(name(c))}，ID ${c.card_id}"><span class="asset-image"><img loading="lazy" src="${escape(source(c, kind))}" alt="${escape(name(c))}"><span class="asset-image-missing" hidden>图片暂不可用<br>点击查看素材信息</span></span><span class="asset-tile-copy"><b>${escape(name(c))}</b><small>${escape(types[c.card_type] || c.card_type)} · ${c.card_id} · ${c.custom_images ? "自制" : local.has(`${c.card_id}:${kind}`) ? "本地" : "远程"}</small></span></button>`).join("") || '<p class="asset-empty">没有符合条件的素材</p>';
  }
  $("#asset-grid").addEventListener("click", (e) => { const tile = e.target.closest("[data-id]"); if (tile) select(tile.dataset.id); });
  $("#asset-grid").addEventListener("error", (e) => { if (e.target.tagName === "IMG") { e.target.hidden = true; e.target.nextElementSibling.hidden = false; } }, true);
  $("#asset-preview").addEventListener("error", () => { $("#asset-preview").hidden = true; $("#asset-image-status").textContent = "图片未能加载，远程链接可能已失效。卡牌名称和 ID 仍可复制。"; });
  for (const id of ["asset-search", "asset-type", "asset-source", "asset-view"]) $("#" + id).addEventListener("input", render);
  $("#asset-kind").addEventListener("change", preview);
  $("#asset-close").addEventListener("click", () => $("#asset-dialog").close());
  $("#asset-dialog").addEventListener("close", () => { if (returnFocus?.isConnected) returnFocus.focus({ preventScroll: true }); });
  $("#asset-dialog").addEventListener("click", (e) => { if (e.target !== $("#asset-dialog")) return; const r = e.target.getBoundingClientRect(); if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) e.target.close(); });
  $("#asset-copy").addEventListener("click", async () => { const text = `${name(selected)}（ID ${selected.card_id}）`; try { await navigator.clipboard.writeText(text); $("#asset-image-status").textContent = `已复制：${text}`; } catch { $("#asset-image-status").textContent = text; } });
  Promise.all([fetch(`${root}cards.json`).then((r) => { if (!r.ok) throw Error("索引加载失败"); return r.json(); }), fetch(`${root}assets/manifest.json`).then((r) => { if (!r.ok) throw Error("本地清单加载失败"); return r.json(); }), fetch("../assets/custom/manifest.json").then((r) => { if (!r.ok) throw Error("自制素材清单加载失败"); return r.json(); })]).then(([index, manifest, custom]) => {
    for (const entry of manifest.assets) { local.add(`${entry.card_id}:${entry.kind}`); originals.set(`${entry.card_id}:${entry.kind}`, `${root}assets/${entry.path}`); }
    cards = index.cards;
    for (const entry of custom.assets) {
      const custom_images = Object.fromEntries(Object.entries(entry.images).map(([kind, path]) => [kind, `../${path}`]));
      cards.push({ card_id: entry.id, card_name: entry.name, card_type: entry.card_type, custom_images });
      for (const kind of Object.keys(custom_images)) {
        local.add(`${entry.id}:${kind}`);
        originals.set(`${entry.id}:${kind}`, `../${entry.source.path}`);
      }
    }
    render();
  }).catch((e) => { $("#asset-status").textContent = `${e.message}。请通过本地特效库服务访问此页面。`; });
})();
