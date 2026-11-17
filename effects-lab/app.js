"use strict";
(() => {
  const $ = (s) => document.querySelector(s);
  const FX = window.ArtifactFX;
  const storageKey = "yf-artifact-effects-lab-v1";
  const directions = { N: [-1, 0, "上"], NE: [-1, 1, "右上"], E: [0, 1, "右"], SE: [1, 1, "右下"], S: [1, 0, "下"], SW: [1, -1, "左下"], W: [0, -1, "左"], NW: [-1, -1, "左上"] };
  const icons = {
    fissure: '<path d="m12 2-3 6 5 3-5 5 3 6M3 12h3m12 0h3"/>',
    melee: '<path d="m6 19 14-15-1 7L8 21zM4 14l7 6M3 21l4-4"/>',
    projectile: '<path d="M3 17 19 5m-6-1 8-2-2 8M3 9l4-3M8 21l4-3"/>',
    impact: '<path d="m12 2 2 6 6-2-4 6 6 3-7 1-3 6-2-7-7 1 5-5-4-5 6 2z"/>',
    heal: '<path d="M12 4v16M4 12h16"/><circle cx="12" cy="12" r="10" opacity=".3"/>',
    summon: '<ellipse cx="12" cy="18" rx="10" ry="4"/><path d="M6 13V6m12 7V6M12 15V2m-4 4 4-4 4 4"/>',
    lightning: '<path d="m14 2-9 12h7l-2 8 9-13h-7z"/>',
    stun: '<ellipse cx="12" cy="14" rx="10" ry="4"/><path d="m7 2 1 3 3 1-3 1-1 3-1-3-3-1 3-1zM17 4v6m-3-3h6"/>',
    shield: '<path d="m12 2 9 4c0 8-3 12-9 16C6 18 3 14 3 6zM12 7v10m-5-5h10"/>',
    aura: '<circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="10" stroke-dasharray="3 3"/><path d="M12 1v3m0 16v3M1 12h3m16 0h3"/>',
    death: '<path d="M5 21V9a7 7 0 0 1 14 0v12l-4-3-3 3-3-3zM8 10h1m6 0h1m-6 4h4"/>',
    tower: '<path d="M5 22h14M7 22V11L4 8V3h4v3h4V3h4v3h4V3h1v5l-4 3v11M10 22v-6h4v6"/>',
  };
  let kind = "fissure", params = FX.defaults(kind), sceneSettings = { direction: "N", distance: 2, columns: 6 };
  let saved = [], controller = null, playing = false, raf = null;
  const notice = (text) => { $("#notice").textContent = text; };
  function validateProject(value) {
    if (!value || value.schemaVersion !== 1 || !Object.hasOwn(FX.catalog, value.kind) || !value.parameters || typeof value.parameters !== "object" || Array.isArray(value.parameters)) throw new Error("这不是受支持的特效预设");
    const parameters = FX.parameters(value.kind, value.parameters);
    if (!value.scene || !Object.hasOwn(directions, value.scene.direction) || ![1, 2].includes(value.scene.distance)) throw new Error("预览方向或距离不正确");
    const columns = value.scene.columns === undefined ? 6 : value.scene.columns;
    if (![5, 6].includes(columns)) throw new Error("地图需要为五列或六列");
    if (typeof value.name !== "string" || !value.name.trim() || value.name.length > 64) throw new Error("预设名称需要为 1–64 个字符");
    return { schemaVersion: 1, name: value.name.trim(), kind: value.kind, parameters, scene: { direction: value.scene.direction, distance: value.kind === "fissure" ? 2 : value.scene.distance, columns } };
  }
  const project = () => ({ schemaVersion: 1, name: $("#preset-name").value.trim() || FX.catalog[kind].name + " · 自定义", kind, parameters: { ...params }, scene: { ...sceneSettings } });
  function persist() {
    try { localStorage.setItem(storageKey, JSON.stringify({ schemaVersion: 1, current: project(), saved })); }
    catch { notice("浏览器未能保存，请导出 JSON 备份当前预设。"); }
  }
  function updateJSON() {
    $("#preset-json").textContent = JSON.stringify(project(), null, 2);
  }
  function updateSaved(selected = "") {
    const select = $("#saved-presets"); select.replaceChildren();
    select.add(new Option(saved.length ? "选择已保存的预设" : "暂无已保存的预设", ""));
    saved.forEach((p, i) => select.add(new Option(p.name, String(i))));
    select.value = selected;
    $("#load-preset").disabled = $("#delete-preset").disabled = !select.value;
  }
  function updatePlayback() {
    const time = controller?.time || 0;
    $("#timeline").max = params.duration;
    $("#timeline").value = time;
    $("#time-readout").textContent = `${Math.round(time)} / ${params.duration} ms`;
    $("#play").textContent = playing ? "暂停" : "播放";
    $("#play").setAttribute("aria-label", playing ? "暂停特效" : "播放特效");
  }
  function tick() {
    if (!playing) return;
    if (controller.time >= controller.duration - 0.1) {
      if ($("#loop").checked) { controller.seek(0); controller.play(); }
      else { playing = false; controller.pause(); }
    }
    updatePlayback();
    if (playing) raf = requestAnimationFrame(tick);
  }
  function pause() {
    playing = false; cancelAnimationFrame(raf); controller?.pause(); updatePlayback();
  }
  function play() {
    cancelAnimationFrame(raf); playing = true; controller.play(); updatePlayback(); raf = requestAnimationFrame(tick);
  }
  function seek(ms) {
    pause(); controller.seek(ms); updatePlayback();
  }
  function buildScene() {
    const columns = sceneSettings.columns;
    $(".preview").style.setProperty("--board-columns", columns);
    $("#effect-layer").setAttribute("viewBox", `0 0 ${columns * 100} 800`);
    $("#board-grid").setAttribute("aria-label", `${columns}列八排预览棋盘`);
    const source = { row: 4, col: 2 };
    const [dr, dc, directionName] = directions[sceneSettings.direction];
    const distance = kind === "fissure" ? 2 : sceneSettings.distance;
    const target = { row: source.row + dr * distance, col: source.col + dc * distance };
    const cells = [1, 2].map((n) => ({ row: source.row + dr * n, col: source.col + dc * n }));
    const actor = { id: { melee: 10020, projectile: 10064, heal: 10036, summon: 10017, lightning: 10065, shield: 10017, aura: 10036, death: 10020, tower: 1000 }[kind] || 10033, attack: kind === "tower" ? 4 : 2, hp: kind === "tower" ? 40 : 7 };
    const friendly = ["heal", "summon", "shield", "aura"].includes(kind);
    const actorName = { 10020: "斧王", 10064: "冰晶圣女", 10036: "魅惑魔女", 10017: "陈", 10033: "撼地者", 10065: "宙斯", 1000: "防御塔" }[actor.id];
    const areaCells = [];
    for (let r = -1; r <= 1; r++) for (let c = -1; c <= 1; c++) {
      const row = target.row + r, col = target.col + c;
      if ((r || c) && row >= 0 && row < 8 && col >= 0 && col < columns) areaCells.push({ row, col });
    }
    const tiles = [];
    for (let row = 0; row < 8; row++) for (let col = 0; col < columns; col++) {
      const isSource = row === source.row && col === source.col;
      const isTarget = row === target.row && col === target.col;
      const secondary = kind === "fissure" && row === cells[0].row && col === cells[0].col;
      const auraAlly = kind === "aura" && row === target.row && Math.abs(col - target.col) === 1;
      const unit = isSource ? actor : isTarget ? { id: friendly ? 10014 : 10069, attack: 6, hp: 8 } : secondary || auraAlly ? { id: 1006, attack: 2, hp: 4 } : null;
      tiles.push(`<div class="preview-cell ${row === 0 || row === 7 ? "fountain" : ""} ${row === 7 ? "home-fountain" : ""} ${row === 3 ? "front" : ""} ${unit ? "occupied" : ""}" ${isSource ? 'id="source-unit"' : isTarget ? 'id="target-unit"' : ""} title="第${row + 1}排第${col + 1}列${isSource ? "，" + actorName : isTarget ? "，预览目标" : ""}">${unit ? `<img src="../references/artifact-classic/assets/mobile/mini_image/${unit.id}.webp" alt=""><i class="team-key ${isSource || friendly ? "ally" : "enemy"}"></i><span class="cell-stats"><span>⚔ ${unit.attack}</span><span>♥ ${unit.hp}</span></span>` : ""}</div>`);
    }
    $("#board-grid").innerHTML = tiles.join("");
    $("#scene-caption").textContent = `向${directionName}${distance === 1 ? "一" : "两"}格`;
    const point = (p) => ({ x: (p.col + 0.5) * 100, y: (p.row + 0.5) * 100 });
    return { from: point(source), to: point(target), cells, areaCells, actorElement: $("#source-unit"), targetElement: $("#target-unit") };
  }
  function rebuild(progress = 0.5, resume = false) {
    cancelAnimationFrame(raf); controller?.dispose();
    controller = FX.create($("#effect-layer"), kind, buildScene(), params);
    controller.setRate(Number($("#rate").value));
    controller.seek(progress * params.duration);
    playing = false;
    if (resume) play(); else updatePlayback();
  }
  function updateControls() {
    $("#effect-name").textContent = FX.catalog[kind].name;
    $("#effect-description").textContent = FX.catalog[kind].description;
    for (const key of [...Object.keys(FX.limits), "color"]) {
      $(`#${key}`).value = params[key];
      const output = $(`#${key}-output`);
      if (output) output.textContent = params[key] + (key === "duration" ? " ms" : key === "strength" ? "×" : "");
    }
    $("#direction").value = sceneSettings.direction;
    $("#columns").value = sceneSettings.columns;
    $("#distance").value = kind === "fissure" ? 2 : sceneSettings.distance;
    $("#distance").disabled = kind === "fissure";
    document.querySelectorAll(".effect-option").forEach((b) => { b.classList.toggle("active", b.dataset.kind === kind); b.setAttribute("aria-pressed", b.dataset.kind === kind); });
    updateJSON();
  }
  function loadProject(value) {
    const p = validateProject(value);
    kind = p.kind; params = p.parameters; sceneSettings = p.scene;
    $("#preset-name").value = p.name;
    updateControls(); rebuild(); persist();
  }
  $("#effect-count").textContent = Object.keys(FX.catalog).length;
  for (const [key, entry] of Object.entries(FX.catalog)) {
    const b = document.createElement("button"); b.className = "effect-option"; b.dataset.kind = key;
    b.style.setProperty("--effect-color", entry.color);
    b.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true">${icons[key]}</svg><span><b>${entry.name}</b><small>${entry.category}</small></span>`;
    b.addEventListener("click", () => {
      kind = key; params = FX.defaults(kind); sceneSettings.distance = kind === "melee" ? 1 : 2;
      $("#preset-name").value = entry.name + " · 自定义";
      updateControls(); rebuild(); persist();
    });
    $("#effect-list").append(b);
  }
  for (const key of [...Object.keys(FX.limits), "color"]) {
    $(`#${key}`).addEventListener("input", (event) => {
      const progress = controller.time / controller.duration, resume = playing;
      try {
        params = FX.parameters(kind, { ...params, [key]: key === "color" ? event.target.value : Number(event.target.value) });
        updateControls(); rebuild(progress, resume); persist();
      } catch (error) { notice(error.message); }
    });
    $(`#${key}`).addEventListener("change", () => updateControls());
  }
  for (const key of ["direction", "distance", "columns"]) $("#" + key).addEventListener("change", (event) => {
    const resume = playing, progress = controller.time / controller.duration;
    sceneSettings[key] = key === "direction" ? event.target.value : Number(event.target.value);
    updateJSON(); rebuild(progress, resume); persist();
  });
  $("#reset").addEventListener("click", () => { params = FX.defaults(kind); updateControls(); rebuild(); persist(); notice("已恢复此效果的默认参数。"); });
  $("#play").addEventListener("click", () => playing ? pause() : play());
  $("#replay").addEventListener("click", () => { seek(0); play(); });
  $("#previous-frame").addEventListener("click", () => seek(controller.time - 1000 / 60));
  $("#next-frame").addEventListener("click", () => seek(controller.time + 1000 / 60));
  $("#timeline").addEventListener("input", (event) => seek(Number(event.target.value)));
  $("#rate").addEventListener("change", (event) => controller.setRate(Number(event.target.value)));
  $("#preview-size").addEventListener("change", (event) => $("#preview-board").style.setProperty("--preview-width", event.target.value + "px"));
  $("#preset-name").addEventListener("input", () => { updateJSON(); persist(); });
  $("#save-preset").addEventListener("click", () => {
    try {
      const p = validateProject(project());
      const index = saved.findIndex((entry) => entry.name === p.name);
      if (index < 0) saved.push(p); else saved[index] = p;
      updateSaved(String(index < 0 ? saved.length - 1 : index)); persist(); notice(`已保存「${p.name}」。同名保存会更新参数。`);
    } catch (error) { notice(error.message); }
  });
  $("#saved-presets").addEventListener("change", (event) => { $("#load-preset").disabled = $("#delete-preset").disabled = !event.target.value; });
  $("#load-preset").addEventListener("click", () => { if ($("#saved-presets").value !== "") loadProject(saved[Number($("#saved-presets").value)]); });
  $("#delete-preset").addEventListener("click", () => {
    if ($("#saved-presets").value === "") return;
    saved.splice(Number($("#saved-presets").value), 1); updateSaved(); persist(); notice("已删除选中的预设，当前预览参数仍然保留。");
  });
  $("#export-preset").addEventListener("click", () => {
    const blob = new Blob([JSON.stringify(project(), null, 2) + "\n"], { type: "application/json" });
    const url = URL.createObjectURL(blob), a = document.createElement("a");
    a.href = url; a.download = `artifact-fx-${kind}.json`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    notice("已导出当前预设，可用“导入预设”重新打开。");
  });
  $("#import-button").addEventListener("click", () => $("#import-file").click());
  $("#import-file").addEventListener("change", async (event) => {
    const file = event.target.files[0]; if (!file) return;
    try {
      if (file.size > 65536) throw new Error("预设文件过大，请选择单个特效的 JSON 文件");
      loadProject(JSON.parse(await file.text())); notice("已载入导入的参数。点击保存预设可加入“我的预设”。");
    } catch (error) { notice("导入失败：" + error.message); }
    finally { event.target.value = ""; }
  });
  document.addEventListener("keydown", (event) => {
    if (event.target.closest("input,select,button,summary")) return;
    if (event.code === "Space") { event.preventDefault(); playing ? pause() : play(); }
    if (["ArrowLeft", "ArrowRight"].includes(event.code)) { event.preventDefault(); seek(controller.time + (event.code === "ArrowRight" ? 1 : -1) * 1000 / 60); }
  });
  try {
    const stored = JSON.parse(localStorage.getItem(storageKey));
    if (stored?.schemaVersion === 1) {
      saved = (stored.saved || []).map(validateProject);
      const current = validateProject(stored.current);
      kind = current.kind; params = current.parameters; sceneSettings = current.scene; $("#preset-name").value = current.name;
    }
  } catch { notice("没有读到有效的本地记录，已使用默认参数。可通过 JSON 导入备份。"); }
  updateSaved(); updateControls(); rebuild();
})();
