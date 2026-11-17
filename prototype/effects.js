/* Local visual effects library. It never calculates game rules or damage. */
"use strict";
(() => {
  const ns = "http://www.w3.org/2000/svg";
  const catalog = {
    fissure: { name: "沟壑", category: "英雄技能", description: "逐格裂地、碎石与命中", color: "#edbd72", duration: 900 },
    melee: { name: "近战挥砍", category: "普通攻击", description: "前冲、刀光与回位", color: "#f0dfb4", duration: 620 },
    projectile: { name: "远程弹道", category: "普通攻击", description: "拖尾、飞行与碰撞", color: "#8ed9ee", duration: 800 },
    impact: { name: "受击", category: "战斗反馈", description: "冲击环、火星与伤害数字", color: "#eea17e", duration: 750 },
    heal: { name: "治疗", category: "战斗反馈", description: "上升光点与恢复数字", color: "#b3d79d", duration: 1200 },
    summon: { name: "召唤", category: "出场", description: "法阵展开、聚光与显形", color: "#baafed", duration: 1100 },
    lightning: { name: "雷击", category: "法术伤害", description: "落雷、分叉电弧与二次闪击", color: "#acdfff", duration: 950 },
    stun: { name: "眩晕", category: "控制状态", description: "头顶星环与绕行星芒", color: "#f3d583", duration: 1800, damage: 0 },
    shield: { name: "护盾", category: "防御状态", description: "护盾展开、受击波纹与消散", color: "#87cfed", duration: 1600, damage: 0 },
    aura: { name: "增益光环", category: "范围增益", description: "邻格亮起、符文扩散与上升光点", color: "#b6d68c", duration: 2000, damage: 0 },
    death: { name: "阵亡", category: "退场", description: "失色、碎光与灵魂升起", color: "#b8b0d4", duration: 1400, damage: 0 },
    tower: { name: "防御塔炮击", category: "建筑攻击", description: "炮口蓄力、抛物线飞行与落点爆炸", color: "#f5ad6e", duration: 1250, damage: 4 },
  };
  const limits = { duration: [200, 3000], width: [1, 10], glow: [0, 16], strength: [0.25, 2], damage: [0, 999] };
  function defaults(kind) {
    if (!Object.hasOwn(catalog, kind)) throw new Error("未知特效类型");
    const entry = catalog[kind];
    return { duration: entry.duration, color: entry.color, width: 3, glow: 4, strength: 1, damage: entry.damage ?? 2 };
  }
  function parameters(kind, input = {}) {
    const value = { ...defaults(kind) };
    for (const [key, [min, max]] of Object.entries(limits)) {
      if (input[key] !== undefined) {
        if (typeof input[key] !== "number" || !Number.isFinite(input[key]) || input[key] < min || input[key] > max) throw new Error(`${key} 超出允许范围 ${min}–${max}`);
        value[key] = input[key];
      }
    }
    if (input.color !== undefined) {
      if (!/^#[0-9a-f]{6}$/i.test(input.color)) throw new Error("颜色需要使用六位十六进制值");
      value.color = input.color;
    }
    return value;
  }
  function create(layer, kind, scene, input = {}) {
    const p = parameters(kind, input), animations = [];
    const root = document.createElementNS(ns, "g");
    root.dataset.effect = kind;
    layer.append(root);
    const add = (tag, attrs, parent = root) => {
      const node = document.createElementNS(ns, tag);
      for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
      parent.append(node);
      return node;
    };
    const animate = (node, keys, easing = "linear") => {
      const animation = node.animate(keys, { duration: p.duration, fill: "both", easing });
      animation.pause(); animation.currentTime = 0;
      animations.push(animation);
      return animation;
    };
    // A shared clock makes pause/seek deterministic across all particles.
    animate(root, [{ opacity: 1 }, { opacity: 1 }]);
    const glow = (node) => {
      if (p.glow) node.style.filter = `drop-shadow(0 0 ${p.glow * 1.5}px ${p.color})`;
      return node;
    };
    const line = (d, width = p.width * 1.7, color = p.color) => glow(add("path", { d, fill: "none", stroke: color, "stroke-width": width, "stroke-linecap": "round", "stroke-linejoin": "round" }));
    const { from, to } = scene;
    const dx = to.x - from.x, dy = to.y - from.y, length = Math.hypot(dx, dy) || 1;
    const fade = (node, start = 0, end = 1) => animate(node, [
      { opacity: 0, offset: 0 }, { opacity: 0, offset: start },
      { opacity: 1, offset: Math.min(end, start + 0.15) }, { opacity: 0, offset: end },
      { opacity: 0, offset: 1 },
    ]);
    const burst = (at, begin = 0.45) => {
      const group = glow(add("g", { fill: p.color }));
      for (let i = 0; i < 10; i++) {
        const angle = i * Math.PI * 2 / 10;
        const r = (24 + (i % 3) * 10) * p.strength;
        const dot = add("circle", { cx: at.x, cy: at.y, r: 2 + i % 3 }, group);
        animate(dot, [
          { opacity: 0, transform: "translate(0,0)", offset: 0 },
          { opacity: 0, transform: "translate(0,0)", offset: begin },
          { opacity: 1, transform: `translate(${Math.cos(angle) * r * 0.25}px,${Math.sin(angle) * r * 0.25}px)`, offset: Math.min(0.95, begin + 0.08) },
          { opacity: 0, transform: `translate(${Math.cos(angle) * r}px,${Math.sin(angle) * r}px)`, offset: 1 },
        ]);
      }
    };
    const ring = (at, begin = 0.3, healing = false) => {
      const circle = glow(add("circle", { cx: at.x, cy: at.y, r: 25, fill: "none", stroke: p.color, "stroke-width": p.width * 1.2 }));
      circle.style.transformOrigin = `${at.x}px ${at.y}px`;
      animate(circle, [
        { opacity: 0, transform: "scale(0.2)", offset: 0 },
        { opacity: 0, transform: "scale(0.2)", offset: begin },
        { opacity: 0.9, transform: "scale(0.55)", offset: begin + 0.1 },
        { opacity: 0, transform: `scale(${(healing ? 1.2 : 1.9) * p.strength})`, offset: 1 },
      ]);
    };
    const number = (healing = false, start = 0.35) => {
      if (!p.damage) return;
      const text = add("text", { x: to.x, y: to.y - 18, fill: healing ? p.color : "#fff0d1", "text-anchor": "middle", "font-size": 30, "font-weight": 700, "font-family": "Georgia,serif", stroke: "#111719", "stroke-width": 3, "paint-order": "stroke" });
      text.textContent = `${healing ? "+" : "−"}${p.damage}`;
      animate(text, [
        { opacity: 0, transform: "translateY(0)", offset: 0 },
        { opacity: 0, transform: "translateY(0)", offset: start },
        { opacity: 1, transform: "translateY(-8px)", offset: start + 0.1 },
        { opacity: 1, transform: "translateY(-32px)", offset: 0.8 },
        { opacity: 0, transform: "translateY(-48px)", offset: 1 },
      ]);
    };
    const flash = (element, start = 0.4) => {
      if (element) animate(element, [
        { filter: "brightness(1)", offset: 0 }, { filter: "brightness(1)", offset: start },
        { filter: `brightness(${1 + p.strength})`, offset: start + 0.08 }, { filter: "brightness(1)", offset: 1 },
      ]);
    };
    if (kind === "fissure") {
      const points = Array.from({ length: 15 }, (_, i) => {
        const offset = i === 0 || i === 14 ? 0 : (i % 2 ? 9 : -9) * p.strength;
        return `${i ? "L" : "M"}${from.x + dx * i / 14 - dy / length * offset},${from.y + dy * i / 14 + dx / length * offset}`;
      }).join(" ");
      for (const [i, cell] of (scene.cells || []).entries()) {
        const tile = add("rect", { x: cell.col * 100 + 3, y: cell.row * 100 + 3, width: 94, height: 94, rx: 5, fill: p.color, "fill-opacity": 0.17, stroke: p.color, "stroke-width": 1 });
        fade(tile, 0.08 + i * 0.13);
      }
      const ridge = line(points, p.width * 4, "#38291e"), crack = line(points);
      const pathLength = crack.getTotalLength();
      for (const path of [ridge, crack]) {
        path.setAttribute("stroke-dasharray", pathLength);
        animate(path, [{ strokeDashoffset: pathLength, opacity: 0.6, offset: 0 }, { strokeDashoffset: 0, opacity: 1, offset: 0.6 }, { strokeDashoffset: 0, opacity: 0, offset: 1 }]);
      }
      burst(to, 0.5); number(); flash(scene.targetElement);
    } else if (kind === "melee") {
      const slash = line(`M${to.x - 26},${to.y + 24} Q${to.x + 3},${to.y + 4} ${to.x + 24},${to.y - 25} M${to.x - 9},${to.y + 25} L${to.x + 28},${to.y - 8}`);
      slash.style.transformOrigin = `${to.x}px ${to.y}px`;
      animate(slash, [{ opacity: 0, transform: "scale(0.4) rotate(-12deg)", offset: 0 }, { opacity: 0, transform: "scale(0.4) rotate(-12deg)", offset: 0.18 }, { opacity: 1, transform: `scale(${p.strength}) rotate(0deg)`, offset: 0.43 }, { opacity: 0, transform: `scale(${p.strength * 1.1})`, offset: 0.85 }, { opacity: 0, offset: 1 }]);
      if (scene.actorElement) animate(scene.actorElement, [{ transform: "translate(0,0)", offset: 0 }, { transform: `translate(${dx / length * 10 * p.strength}px,${dy / length * 10 * p.strength}px)`, offset: 0.38 }, { transform: "translate(0,0)", offset: 0.72 }, { transform: "translate(0,0)", offset: 1 }]);
      burst(to, 0.4); number(false, 0.4); flash(scene.targetElement);
    } else if (kind === "projectile") {
      const trail = line(`M${from.x},${from.y} L${to.x},${to.y}`, p.width);
      trail.setAttribute("stroke-dasharray", "4 7"); fade(trail, 0.05, 0.85);
      const projectile = glow(add("circle", { cx: 0, cy: 0, r: 5 * p.strength, fill: p.color }));
      animate(projectile, [{ transform: `translate(${from.x}px,${from.y}px)`, opacity: 0, offset: 0 }, { transform: `translate(${from.x}px,${from.y}px)`, opacity: 1, offset: 0.08 }, { transform: `translate(${to.x}px,${to.y}px)`, opacity: 1, offset: 0.65 }, { transform: `translate(${to.x}px,${to.y}px)`, opacity: 0, offset: 0.7 }, { opacity: 0, offset: 1 }]);
      burst(to, 0.65); ring(to, 0.65); number(false, 0.65); flash(scene.targetElement, 0.65);
    } else if (kind === "impact") {
      burst(to, 0.15); ring(to, 0.1); number(false, 0.15); flash(scene.targetElement, 0.15);
    } else if (kind === "heal") {
      ring(to, 0.15, true);
      for (let i = 0; i < 7; i++) {
        const x = to.x + (i % 3 - 1) * 19, y = to.y + 25 + i % 2 * 12;
        const mote = glow(add("path", { d: `M${x - 5},${y} h10 M${x},${y - 5} v10`, fill: "none", stroke: p.color, "stroke-width": p.width }));
        animate(mote, [{ opacity: 0, transform: "translateY(0)", offset: 0 }, { opacity: 0, transform: "translateY(0)", offset: i * 0.06 }, { opacity: 0.9, transform: "translateY(-10px)", offset: 0.2 + i * 0.06 }, { opacity: 0, transform: `translateY(${-70 * p.strength}px)`, offset: 1 }]);
      }
      number(true, 0.2);
    } else if (kind === "summon") {
      const column = add("rect", { x: to.x - 29, y: to.y - 92, width: 58, height: 122, fill: p.color, "fill-opacity": 0.12 });
      fade(column, 0.1, 0.9);
      for (let i = 0; i < 2; i++) {
        const circle = line(`M${to.x - 42},${to.y + 25} a42,17 0 1,0 84,0 a42,17 0 1,0 -84,0`, p.width * (i ? 0.7 : 1.3));
        circle.style.transformOrigin = `${to.x}px ${to.y + 25}px`;
        animate(circle, [{ opacity: 0, transform: "scale(0.1)", offset: 0 }, { opacity: 1, transform: `scale(${(i ? 0.7 : 1) * p.strength})`, offset: 0.4 }, { opacity: 0, transform: `scale(${(i ? 0.85 : 1.2) * p.strength})`, offset: 1 }]);
      }
      if (scene.targetElement) animate(scene.targetElement, [{ opacity: 0, transform: "translateY(12px)", offset: 0 }, { opacity: 0, transform: "translateY(12px)", offset: 0.2 }, { opacity: 1, transform: "translateY(0)", offset: 0.75 }, { opacity: 1, offset: 1 }]);
      burst(to, 0.5);
    } else if (kind === "lightning") {
      const start = { x: to.x - 18, y: to.y - 155 };
      const bolt = `M${start.x},${start.y} l-13,42 27,-9 -21,51 24,-10 L${to.x},${to.y}`;
      const flashes = [
        { opacity: 0, offset: 0 }, { opacity: 0, offset: 0.16 },
        { opacity: 1, offset: 0.2 }, { opacity: 0.15, offset: 0.27 },
        { opacity: 0.9, offset: 0.34 }, { opacity: 0.3, offset: 0.42 },
        { opacity: 1, offset: 0.48 }, { opacity: 0, offset: 0.68 }, { opacity: 0, offset: 1 },
      ];
      animate(line(bolt, p.width * 3), flashes);
      animate(line(bolt, p.width * 0.8, "#f5fcff"), flashes);
      for (const side of [-1, 1]) {
        const branch = line(`M${to.x - 7},${to.y - 65} l${side * 34},-15 ${side * -10},31 ${side * 23},5`, p.width);
        animate(branch, flashes);
      }
      const light = add("ellipse", { cx: to.x, cy: to.y, rx: 42, ry: 28, fill: p.color, "fill-opacity": 0.35 });
      fade(light, 0.18, 0.75); burst(to, 0.23); ring(to, 0.25); number(false, 0.25); flash(scene.targetElement, 0.2);
    } else if (kind === "stun") {
      const halo = glow(add("ellipse", { cx: to.x, cy: to.y - 43, rx: 31 * p.strength, ry: 10, fill: "none", stroke: p.color, "stroke-width": p.width, "stroke-dasharray": "5 5" }));
      fade(halo, 0.03);
      for (let i = 0; i < 3; i++) {
        const star = glow(add("path", { d: "M0,-8 2,-2 8,0 2,2 0,8 -2,2 -8,0 -2,-2Z", fill: p.color }));
        animate(star, Array.from({ length: 25 }, (_, n) => {
          const angle = n / 24 * Math.PI * 2 + i * Math.PI * 2 / 3;
          return { transform: `translate(${to.x + Math.cos(angle) * 31 * p.strength}px,${to.y - 43 + Math.sin(angle) * 10}px) rotate(${n * 15}deg)`, opacity: n === 0 || n === 24 ? 0 : 1, offset: n / 24 };
        }));
      }
      if (scene.targetElement) animate(scene.targetElement, [
        { filter: "saturate(1)", offset: 0 }, { filter: "saturate(0.25)", offset: 0.15 },
        { filter: "saturate(0.25)", offset: 0.85 }, { filter: "saturate(1)", offset: 1 },
      ]);
    } else if (kind === "shield") {
      const shape = `M${to.x},${to.y - 49} L${to.x + 40},${to.y - 32} Q${to.x + 43},${to.y + 25} ${to.x},${to.y + 47} Q${to.x - 43},${to.y + 25} ${to.x - 40},${to.y - 32}Z`;
      const shield = glow(add("path", { d: shape, stroke: p.color, "stroke-width": p.width, fill: p.color, "fill-opacity": 0.12 }));
      shield.style.transformOrigin = `${to.x}px ${to.y}px`;
      animate(shield, [
        { opacity: 0, transform: "scale(0.4)", offset: 0 }, { opacity: 0.85, transform: "scale(1)", offset: 0.2 },
        { opacity: 0.6, transform: "scale(1)", offset: 0.4 }, { opacity: 1, transform: `scale(${1 + 0.08 * p.strength})`, offset: 0.48 },
        { opacity: 0.75, transform: "scale(1)", offset: 0.6 }, { opacity: 0.7, transform: "scale(1)", offset: 0.82 },
        { opacity: 0, transform: "scale(1.15)", offset: 1 },
      ]);
      const sigil = line(`M${to.x},${to.y - 24} v42 M${to.x - 14},${to.y - 3} h28`, p.width);
      fade(sigil, 0.12, 0.94);
      const strike = line(`M${to.x + 64},${to.y - 52} L${to.x + 31},${to.y - 19}`, p.width * 2, "#fff1d3");
      fade(strike, 0.37, 0.56);
      ring({ x: to.x + 31, y: to.y - 19 }, 0.45);
    } else if (kind === "aura") {
      for (const [i, cell] of (scene.areaCells || []).entries()) {
        const tile = add("rect", { x: cell.col * 100 + 5, y: cell.row * 100 + 5, width: 90, height: 90, rx: 4, fill: p.color, "fill-opacity": 0.1, stroke: p.color, "stroke-opacity": 0.55, "stroke-width": p.width * 0.4 });
        fade(tile, 0.04 + i * 0.015, 0.98);
      }
      for (let i = 0; i < 2; i++) {
        const circle = glow(add("circle", { cx: to.x, cy: to.y, r: 145, fill: "none", stroke: p.color, "stroke-width": p.width * (i ? 0.5 : 1), "stroke-dasharray": i ? "3 17" : "55 14" }));
        circle.style.transformOrigin = `${to.x}px ${to.y}px`;
        animate(circle, [
          { opacity: 0, transform: "scale(0.1) rotate(0deg)", offset: 0 },
          { opacity: 0.7, transform: `scale(${i ? 0.88 : 1}) rotate(${i ? -15 : 15}deg)`, offset: 0.3 },
          { opacity: 0.5, transform: `scale(${i ? 0.88 : 1}) rotate(${i ? -40 : 40}deg)`, offset: 0.8 },
          { opacity: 0, transform: `scale(1.05) rotate(${i ? -50 : 50}deg)`, offset: 1 },
        ]);
      }
      for (let i = 0; i < 8; i++) {
        const angle = i * Math.PI / 4, x = to.x + Math.cos(angle) * 104, y = to.y + Math.sin(angle) * 104;
        const mote = glow(add("path", { d: `M${x - 5},${y + 4} l5,-8 5,8 M${x},${y - 4} v17`, fill: "none", stroke: p.color, "stroke-width": p.width }));
        animate(mote, [{ opacity: 0, transform: "translateY(10px)", offset: 0 }, { opacity: 0, transform: "translateY(10px)", offset: 0.15 + i * 0.025 }, { opacity: 0.9, transform: "translateY(0)", offset: 0.4 + i * 0.025 }, { opacity: 0, transform: `translateY(${-30 * p.strength}px)`, offset: 1 }]);
      }
    } else if (kind === "death") {
      if (scene.targetElement) animate(scene.targetElement, [
        { opacity: 1, filter: "grayscale(0)", transform: "translateY(0)", offset: 0 },
        { opacity: 1, filter: "grayscale(1)", transform: "translateY(0)", offset: 0.18 },
        { opacity: 0.35, filter: "grayscale(1)", transform: "translateY(7px)", offset: 0.5 },
        { opacity: 0, filter: "grayscale(1)", transform: "translateY(12px)", offset: 0.72 },
        { opacity: 0, offset: 1 },
      ]);
      ring(to, 0.12);
      const soul = glow(add("path", { d: `M${to.x},${to.y - 24} C${to.x - 25},${to.y - 5} ${to.x - 16},${to.y + 19} ${to.x},${to.y + 23} C${to.x + 16},${to.y + 19} ${to.x + 25},${to.y - 5} ${to.x},${to.y - 24}Z`, fill: p.color, "fill-opacity": 0.55 }));
      animate(soul, [{ opacity: 0, transform: "translateY(0)", offset: 0 }, { opacity: 0, transform: "translateY(0)", offset: 0.2 }, { opacity: 0.85, transform: "translateY(-15px)", offset: 0.45 }, { opacity: 0, transform: `translateY(${-100 * p.strength}px)`, offset: 1 }]);
      for (let i = 0; i < 8; i++) {
        const mote = glow(add("rect", { x: to.x + (i % 4 - 1.5) * 15, y: to.y + Math.floor(i / 4) * 18, width: 4, height: 4, fill: p.color }));
        animate(mote, [{ opacity: 0, transform: "translateY(0)", offset: 0 }, { opacity: 0, transform: "translateY(0)", offset: 0.2 + i * 0.03 }, { opacity: 0.9, transform: "translateY(-8px)", offset: 0.3 + i * 0.03 }, { opacity: 0, transform: `translate(${(i % 2 ? 1 : -1) * 25}px,${-70 * p.strength}px)`, offset: 1 }]);
      }
    } else if (kind === "tower") {
      const arc = (t) => ({ x: from.x + dx * t, y: from.y + dy * t - Math.sin(Math.PI * t) * 62 });
      const points = Array.from({ length: 21 }, (_, n) => { const at = arc(n / 20); return `${n ? "L" : "M"}${at.x},${at.y}`; }).join(" ");
      const trail = line(points, p.width, p.color);
      trail.setAttribute("stroke-dasharray", "3 8"); fade(trail, 0.15, 0.82);
      const charge = glow(add("circle", { cx: from.x, cy: from.y, r: 16 * p.strength, fill: p.color }));
      charge.style.transformOrigin = `${from.x}px ${from.y}px`;
      animate(charge, [{ opacity: 0, transform: "scale(0.2)", offset: 0 }, { opacity: 0.9, transform: "scale(1)", offset: 0.18 }, { opacity: 0, transform: "scale(1.4)", offset: 0.27 }, { opacity: 0, offset: 1 }]);
      const shell = glow(add("circle", { cx: 0, cy: 0, r: 8 * p.strength, fill: "#fff0cb", stroke: p.color, "stroke-width": p.width }));
      const flight = Array.from({ length: 21 }, (_, n) => {
        const at = arc(n / 20); return { transform: `translate(${at.x}px,${at.y}px)`, opacity: n === 20 ? 0 : 1, offset: 0.2 + n / 20 * 0.48 };
      });
      animate(shell, [{ transform: `translate(${from.x}px,${from.y}px)`, opacity: 0, offset: 0 }, { transform: `translate(${from.x}px,${from.y}px)`, opacity: 0, offset: 0.19 }, ...flight, { opacity: 0, offset: 1 }]);
      ring(to, 0.67); burst(to, 0.68); number(false, 0.68); flash(scene.targetElement, 0.68);
    }
    return {
      duration: p.duration, root,
      get time() { return Number(animations[0].currentTime) || 0; },
      get playing() { return animations[0].playState === "running"; },
      play() { if (this.time >= p.duration) this.seek(0); animations.forEach((a) => a.play()); },
      pause() { const time = this.time; animations.forEach((a) => { a.pause(); a.currentTime = time; }); },
      seek(ms) { this.pause(); animations.forEach((a) => { a.currentTime = Math.max(0, Math.min(p.duration, ms)); }); },
      setRate(rate) { if (![0.25, 0.5, 1, 2].includes(rate)) throw new Error("不支持的播放速度"); animations.forEach((a) => { a.playbackRate = rate; }); },
      dispose() { animations.forEach((a) => a.cancel()); root.remove(); },
    };
  }
  window.ArtifactFX = Object.freeze({ catalog, limits, defaults, parameters, create });
})();
