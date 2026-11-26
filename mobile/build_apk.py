"""Assemble the local Godot art study, signed Android template and offline CPython runtime.

Stages the tracked Godot source and the developer’s local asset bundle. Supply
an extracted python.org 3.14 Android distribution per ABI and the matching Godot
template for APK export. No web service or runtime downloads are required by the installed game.
"""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

from local_assets import DEFAULT_BUNDLE, install

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_pages import ENGINE_FILES


def run(args, **kwargs):
    subprocess.run([str(x) for x in args], check=True, **kwargs)


def run_godot(args):
    result = subprocess.run([str(x) for x in args], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    print(result.stdout, flush=True)
    if result.returncode or any(line.startswith(("SCRIPT ERROR:", "ERROR:"))
                                for line in result.stdout.splitlines()):
        raise RuntimeError("Godot reported a project or export error")


def stage_copy(src, dst):
    dst = Path(dst)
    if dst.exists():
        dst.chmod(dst.stat().st_mode | 0o200)
    return shutil.copy2(src, dst)


def stage(a):
    project = a.work / "project"
    if not a.assets.is_file():
        raise ValueError(f"找不到本地素材包 {a.assets}，参见 mobile/README.md。")
    for source, target in [(HERE/"project", project), (HERE/"game", project/"game")]:
        shutil.copytree(source, target, dirs_exist_ok=True, copy_function=stage_copy,
                        ignore=shutil.ignore_patterns(".godot", "*.uid", "*.import"))
    install(a.assets, project)
    art = project / "game/art"
    for source, dest in [(ROOT/"references/artifact-classic/assets/mobile/large_image", "classic"),
                         (ROOT/"references/artifact-classic/assets/mobile/mini_image", "icons"),
                         (ROOT/"prototype/assets/cards", "cards"), (ROOT/"prototype/assets/units", "units")]:
        shutil.copytree(source, art/dest, dirs_exist_ok=True, copy_function=stage_copy)
    if a.template:
        preset_path = project/"export_presets.cfg"
        preset = preset_path.read_text(encoding="utf-8")
        template = str(a.template.resolve()).replace(os.sep, "/")
        preset = preset.replace('custom_template/debug=""', f'custom_template/debug="{template}"')
        if a.x86:
            preset = preset.replace("architectures/x86_64=false", "architectures/x86_64=true")
        preset_path.write_text(preset, encoding="utf-8")
    return project


def runtime_zip(archive, prefix):
    std = prefix/"lib/python3.14"
    with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED,compresslevel=5) as z:
        for f in sorted(std.rglob("*")):
            if not f.is_file() or set(f.relative_to(std).parts) & {"test","tests","__pycache__","ensurepip","idlelib","tkinter","turtledemo"}:
                continue
            z.write(f, str(f.relative_to(prefix)))
        z.write(HERE/"yf_match.py", "lib/python3.14/yf_match.py")
        for name in ENGINE_FILES:
            z.write(ROOT/name,"game/"+name)
        license_file = std/"LICENSE.txt"
        if license_file.exists():
            z.write(license_file,"PYTHON-LICENSE.txt")


def assemble(a):
    project=stage(a)
    run_godot([a.godot, "--headless", "--editor", "--path", project, "--import"])
    if a.stage_only:
        return
    base=a.work/"godot.apk"
    run_godot([a.godot,"--headless","--path",project,"--export-debug","Android",base])
    bt=a.sdk/"build-tools"/a.build_tools
    android=a.sdk/"platforms/android-36/android.jar"
    javaclasses=a.work/"java"
    dex=a.work/"dex"
    for d in (javaclasses,dex): d.mkdir(exist_ok=True)
    run([a.jdk/"bin/javac","--release","8","-classpath",android,"-d",javaclasses,HERE/"android/OfflineRules.java"])
    run([bt/"d8","--min-api","24","--lib",android,"--output",dex,*javaclasses.rglob("*.class")])
    additions={}
    shim_include=a.work/"jni-headers"
    shim_include.mkdir(exist_ok=True)
    # jni.h includes stdio.h without using it. The bridge uses no libc calls.
    (shim_include/"stdio.h").write_text("")
    (shim_include/"stdarg.h").write_text("typedef __builtin_va_list va_list;\n")
    for abi, dist, target in [("arm64-v8a",a.arm,"aarch64"),("x86_64",a.x86,"x86_64")]:
        if not dist: continue
        prefix=dist/"prefix"
        so=a.work/f"{abi}-libyfrules.so"
        run([a.zig,"cc","-target",target+"-linux-android","-ffreestanding","-fPIC","-nostdinc",
             "-I"+str(shim_include),"-I"+str(a.jdk/"include"),"-I"+str(a.jdk/"include/linux"),
             "-nostdlib","-shared",HERE/"android/bridge.c",prefix/"lib/libpython3.14.so",
             "-Wl,-soname,libyfrules.so,-z,max-page-size=16384","-o",so])
        archive=a.work/f"yf_runtime-{abi}.zip"
        runtime_zip(archive,prefix)
        additions["assets/"+archive.name]=archive
        additions[f"lib/{abi}/libyfrules.so"]=so
        for lib in [prefix/"lib/libpython3.14.so",*(prefix/"lib").glob("lib*_python.so")]:
            additions[f"lib/{abi}/{lib.name}"]=lib
    unsigned=a.work/"unsigned.apk"
    with zipfile.ZipFile(base) as src, zipfile.ZipFile(unsigned,"w") as dst:
        for info in src.infolist():
            if not info.filename.startswith("META-INF/"):
                dst.writestr(info,src.read(info))
        n=2
        while f"classes{n}.dex" in src.namelist(): n+=1
        additions[f"classes{n}.dex"]=dex/"classes.dex"
        for name,f in additions.items(): dst.write(f,name,zipfile.ZIP_STORED)
    aligned=a.work/"aligned.apk"
    run([bt/"zipalign","-f","-P","16","4",unsigned,aligned])
    a.apk.parent.mkdir(exist_ok=True,parents=True)
    run([bt/"apksigner","sign","--ks",a.keystore,"--ks-pass","pass:android","--out",a.apk,aligned])
    run([bt/"apksigner","verify","--verbose",a.apk])
    print(a.apk, hashlib.sha256(a.apk.read_bytes()).hexdigest())


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--work",type=Path,default=ROOT/"output/mobile-match")
    p.add_argument("--assets",type=Path,default=DEFAULT_BUNDLE)
    p.add_argument("--apk",type=Path,default=ROOT/"output/mobile-match/Riverbank-Match.apk")
    for key in ["godot","template","jdk","sdk","zig","arm","x86"]:
        p.add_argument("--"+key,type=Path,required=key=="godot")
    p.add_argument("--keystore",type=Path,default=Path.home()/".android/debug.keystore")
    p.add_argument("--build-tools",default="36.0.0")
    p.add_argument("--stage-only",action="store_true")
    args=p.parse_args()
    args.work.mkdir(parents=True,exist_ok=True)
    if not args.stage_only:
        required = ("template", "jdk", "sdk", "zig", "arm")
        missing = [f"--{key}" for key in required if getattr(args,key) is None]
        if missing:
            p.error("APK export requires " + ", ".join(missing))
        os.environ["JAVA_HOME"] = str(args.jdk.resolve())
        os.environ["PATH"] = os.pathsep.join((str(args.jdk.resolve()/"bin"), os.environ["PATH"]))
    try:
        assemble(args)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        p.exit(1, f"{exc}\n")
