"use strict";
(() => {
  const browserMode = window.ARTIFACT_RUNTIME === "browser";
  const saveKey = "yf-artifact-browser-save-v1";
  const pending = new Map();
  let worker,
    sequence = 0,
    memorySave = null,
    storageWarning = false;
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
    worker = new Worker(new URL("engine-worker.js", document.baseURI), {
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
      if (data.save) save(data.save);
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
  window.ArtifactAPI = { request, browserMode };
})();
