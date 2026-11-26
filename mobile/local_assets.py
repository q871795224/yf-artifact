"""Transfer this checkout's existing local assets between development machines."""
import argparse
from pathlib import Path
import shutil
import zipfile

MOBILE = Path(__file__).resolve().parent
ROOT = MOBILE.parent
DEFAULT_BUNDLE = ROOT / "output" / "mobile-local-assets.zip"


def asset_paths():
    return (MOBILE / "local-assets.txt").read_text(encoding="utf-8").splitlines()


def pack(bundle, art_project, effects_project):
    effects_folders = {"selection_assets", "cast_fx", "source2_fx", "shatter"}
    files = {}
    for name in asset_paths():
        effects_file = effects_project / name
        if name.split("/", 1)[0] in effects_folders and effects_file.is_file():
            files[name] = effects_file
        else:
            files[name] = art_project / name
    missing = [str(path) for path in files.values() if not path.is_file()]
    if missing:
        raise ValueError("本地预览缺少以下资源：\n" + "\n".join(missing))
    bundle.parent.mkdir(parents=True, exist_ok=True)
    temporary = bundle.with_suffix(".tmp")
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, path in files.items():
                archive.write(path, name)
        temporary.replace(bundle)
    finally:
        temporary.unlink(missing_ok=True)


def install(bundle, project):
    if not bundle.is_file():
        raise ValueError(f"找不到本地素材包 {bundle}，参见 mobile/README.md。")
    with zipfile.ZipFile(bundle) as archive:
        required = asset_paths()
        missing = set(required) - set(archive.namelist())
        if missing:
            raise ValueError("素材包缺少以下文件：\n" + "\n".join(sorted(missing)))
        for name in required:
            target = project / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(name) as source, target.open("wb") as dest:
                shutil.copyfileobj(source, dest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--art-project", type=Path, default=ROOT/"output/research/mobile-terrain-lite/project")
    parser.add_argument("--effects-project", type=Path, default=ROOT/"output/research/clash-study/player")
    args = parser.parse_args()
    try:
        pack(args.out, args.art_project, args.effects_project)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")
    print(args.out.resolve())
