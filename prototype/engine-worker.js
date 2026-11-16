import { loadPyodide } from "../vendor/pyodide/pyodide.mjs";

const progress = (message) => self.postMessage({ type: "progress", message });
let runtimePromise;
async function runtime() {
  if (!runtimePromise)
    runtimePromise = (async () => {
      progress("正在加载战场，首次打开需要片刻…");
      const pyodide = await loadPyodide({
        indexURL: new URL("../vendor/pyodide/", import.meta.url).href,
      });
      progress("正在准备英雄与牌库…");
      const response = await fetch(
        new URL("engine-files.json", import.meta.url),
      );
      if (!response.ok) throw new Error("游戏资料没有加载完成，请重试。");
      const bundle = await response.json();
      for (const file of bundle.files) {
        const path = "/artifact/" + file.path;
        pyodide.FS.mkdirTree(path.slice(0, path.lastIndexOf("/")));
        pyodide.FS.writeFile(path, file.content);
      }
      pyodide.globals.set("_engine_version", bundle.engine_version);
      await pyodide.runPythonAsync(`
import sys
sys.path.insert(0, '/artifact/scripts')
from browser_bridge import BrowserBridge, handle_json
_bridge = BrowserBridge(_engine_version)
`);
      return pyodide;
    })().catch((error) => {
      runtimePromise = null;
      throw error;
    });
  return runtimePromise;
}
let queue = Promise.resolve();
self.onmessage = ({ data }) => {
  queue = queue.then(async () => {
    try {
      const pyodide = await runtime();
      if (data.record?.commands.length) progress("正在恢复上次的对局…");
      const { id, ...request } = data;
      pyodide.globals.set("_browser_request", JSON.stringify(request));
      const result = JSON.parse(
        await pyodide.runPythonAsync("handle_json(_bridge, _browser_request)"),
      );
      self.postMessage({ id, ...result });
    } catch (error) {
      self.postMessage({
        id: data.id,
        status: 500,
        data: { error: error.message || "游戏暂时无法载入，请重试。" },
      });
    }
  });
};
