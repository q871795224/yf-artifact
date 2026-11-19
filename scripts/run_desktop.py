#!/usr/bin/env python3
"""Launch the Godot source client and its local Python rules service."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

from build_pages import ROOT, engine_sources


DEFAULT_PORT = 8786
HTTP = build_opener(ProxyHandler({}))


def check_service(url):
    try:
        with HTTP.open(url + "/api/health", timeout=0.7) as response:
            return json.load(response)
    except (OSError, ValueError, URLError):
        return {}


def locate_godot(explicit):
    if explicit:
        return shutil.which(explicit)
    for command in ("godot", "godot4", "Godot"):
        executable = shutil.which(command)
        if executable:
            return executable
    cache = Path.home() / ".local/share/yf-artifact/tools"
    if cache.is_dir():
        return next((str(path) for path in sorted(cache.glob("Godot*"), reverse=True)
                     if path.is_file() and os.access(path, os.X_OK)), None)
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--godot", default=os.getenv("GODOT_BIN"))
    parser.add_argument("--lan", action="store_true", help="Let phones on the same local network use this service")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--seed", type=int, help="Seed for newly created playtests")
    parser.add_argument("--service-only", action="store_true", help="Keep the phone browser available without a Godot window")
    args = parser.parse_args()
    godot = locate_godot(args.godot) if not args.service_only else None
    if not args.service_only and not godot:
        parser.error("找不到 Godot 4。请安装 Godot，或传入 --godot /path/to/Godot。")

    service = None
    url = f"http://127.0.0.1:{args.port}"
    archive = ROOT / "output/playtests"
    engine_version = engine_sources()[1]
    existing = check_service(url)
    try:
        if not existing:
            service = subprocess.Popen([sys.executable, str(ROOT / "scripts/serve_prototype.py"),
                "--host", "0.0.0.0" if args.lan else "127.0.0.1",
                "--port", str(args.port), "--archive-dir", str(archive)], cwd=ROOT)
            for _ in range(36):
                existing = check_service(url)
                if existing or service.poll() is not None:
                    break
                time.sleep(0.1)
        if existing.get("engine_version") != engine_version or not existing.get("archive"):
            parser.error("该端口的服务不可用或规则版本不同。请改用 --port 启动。")
        if args.service_only:
            if service is None:
                print(f"归档服务已运行：{url}/prototype/", flush=True)
                return 0
            return service.wait()
        env = {**os.environ, "ARTIFACT_SERVER": url, "ARTIFACT_ROOT": str(ROOT),
               "ARTIFACT_ARCHIVE": str(archive)}
        if args.seed is not None:
            env["ARTIFACT_SEED"] = str(args.seed)
        return subprocess.call([godot, "--path", str(ROOT / "desktop")], cwd=ROOT, env=env)
    except KeyboardInterrupt:
        return 0
    finally:
        if service is not None and service.poll() is None:
            service.terminate()
            try:
                service.wait(timeout=5)
            except subprocess.TimeoutExpired:
                service.kill()
                service.wait()


if __name__ == "__main__":
    sys.exit(main())
