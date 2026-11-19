"use strict";
(() => {
  const browserMode = window.ARTIFACT_RUNTIME === "browser";
  const saveKey = "yf-artifact-browser-save-v1";
  const pending = new Map();
  const cacheReady = browserMode && "serviceWorker" in navigator
    ? Promise.race([
        navigator.serviceWorker.register(new URL("../runtime-cache.js?v=0.4", document.baseURI))
          .then(() => navigator.serviceWorker.ready)
          .then(() => navigator.serviceWorker.controller || new Promise((resolve) => {
            const done = () => { navigator.serviceWorker.removeEventListener("controllerchange", done); resolve(); };
            navigator.serviceWorker.addEventListener("controllerchange", done);
            setTimeout(done, 1000);
          })).catch(() => {}),
        new Promise((resolve) => setTimeout(resolve, 1500)),
      ])
    : Promise.resolve();
  let worker,
    archiveDatabase,
    sequence = 0,
    memorySave = null,
    storageWarning = false;
  function playtestDatabase() {
    if (!archiveDatabase) archiveDatabase = new Promise((resolve, reject) => {
      const request = indexedDB.open("yf-artifact-playtests", 1);
      request.onupgradeneeded = () => request.result.createObjectStore("matches", { keyPath: "game_id" });
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
    return archiveDatabase;
  }
  async function listPlaytests() {
    const database = await playtestDatabase();
    return new Promise((resolve, reject) => {
      const request = database.transaction("matches").objectStore("matches").getAll();
      request.onsuccess = () => resolve(request.result.sort((a, b) => b.updated_at.localeCompare(a.updated_at)));
      request.onerror = () => reject(request.error);
    });
  }
  async function archivePlaytest(record) {
    const database = await playtestDatabase();
    const transaction = database.transaction("matches", "readwrite");
    const store = transaction.objectStore("matches"), request = store.get(record.game_id);
    return new Promise((resolve, reject) => {
      request.onsuccess = () => {
        const old = request.result;
        if (!old || old.commands.length <= record.commands.length) {
          store.put({ ...record, created_at: old?.created_at || record.updated_at });
        }
      };
      transaction.oncomplete = resolve;
      transaction.onabort = () => reject(transaction.error);
    });
  }
  function getSave() {
    try {
      return memorySave || JSON.parse(localStorage.getItem(saveKey));
    } catch {
      return memorySave;
    }
  }
  function save(record) {
    memorySave = record;
    try {
      localStorage.setItem(saveKey, JSON.stringify(record));
    } catch {
      if (!storageWarning) {
        storageWarning = true;
        window.dispatchEvent(new CustomEvent("artifact-save-warning"));
      }
    }
  }
  function engineWorker() {
    if (worker) return worker;
    const url = new URL("engine-worker.js?v=0.4", document.baseURI);
    url.searchParams.set("engine", window.ARTIFACT_ENGINE_VERSION || "local");
    worker = new Worker(url, {
      type: "module",
    });
    worker.onmessage = ({ data }) => {
      if (data.type === "progress") {
        window.dispatchEvent(
          new CustomEvent("artifact-engine-progress", { detail: data.message }),
        );
        return;
      }
      const job = pending.get(data.id);
      if (!job) return;
      clearTimeout(job.timer);
      pending.delete(data.id);
      if (data.save) {
        save(data.save);
        const { round, phase, winner, endReason, stats, forts, release } = data.data.state;
        archivePlaytest({ ...data.save, round, phase, winner, reason: endReason, stats, forts, release,
          source: "pages-browser", updated_at: new Date().toISOString() }).catch(() => {
          if (!storageWarning) {
            storageWarning = true;
            window.dispatchEvent(new CustomEvent("artifact-save-warning"));
          }
        });
      }
      if (data.status >= 400) {
        const error = new Error(
          data.data?.error || "游戏载入未完成，请重新载入。",
        );
        error.status = data.status;
        job.reject(error);
      } else job.resolve(data.data);
    };
    worker.onerror = () => {
      for (const job of pending.values()) {
        clearTimeout(job.timer);
        job.reject(new Error("游戏文件未能加载，请检查网络后重试。"));
      }
      pending.clear();
      worker.terminate();
      worker = null;
    };
    return worker;
  }
  async function request(path, body) {
    if (!browserMode) {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 15000);
      try {
        const response = await fetch(path, {
          method: body ? "POST" : "GET",
          headers: body ? { "Content-Type": "application/json" } : {},
          body: body ? JSON.stringify(body) : undefined,
          signal: controller.signal,
          cache: "no-store",
        });
        const data = await response.json();
        if (!response.ok) {
          const error = new Error(data.error || "连接未完成，请重试。");
          error.status = response.status;
          throw error;
        }
        return data;
      } finally {
        clearTimeout(timer);
      }
    }
    await cacheReady;
    const id = ++sequence;
    const random = crypto.getRandomValues(new Uint32Array(1))[0];
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    const newId = Array.from(bytes, (b) =>
      b.toString(16).padStart(2, "0"),
    ).join("");
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        pending.delete(id);
        reject(new Error("载入时间较长，请保持网络连接后重试。"));
      }, 120000);
      pending.set(id, { resolve, reject, timer });
      engineWorker().postMessage({
        id,
        path,
        body: body || null,
        record: getSave(),
        new_id: newId,
        seed: (random % 1000000) * 3 + 1,
      });
    });
  }
  window.ArtifactAPI = { request, browserMode, listPlaytests };
})();
