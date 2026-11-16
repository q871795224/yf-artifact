#!/usr/bin/env python3
"""Create small WebP copies for the mobile game, preserving the original art."""

import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'references/artifact-classic/assets'


def main():
    encoder = shutil.which('cwebp')
    if not encoder:
        raise SystemExit('Install the WebP cwebp encoder to regenerate mobile art.')
    entries = []
    for kind, width, quality in [('mini_image', 128, 72), ('ingame_image', 96, 75), ('large_image', 352, 76)]:
        output = ASSETS / 'mobile' / kind
        output.mkdir(parents=True, exist_ok=True)
        for source in sorted((ASSETS / kind).glob('*.png')):
            original = source.read_bytes()
            original_width, _ = struct.unpack('>II', original[16:24])
            target = output / (source.stem + '.webp')
            subprocess.run([encoder, '-quiet', '-q', str(quality), '-m', '6',
                            '-resize', str(min(width, original_width)), '0', str(source), '-o', str(target)], check=True)
            compressed = target.read_bytes()
            entries.append({'source': str(source.relative_to(ASSETS)),
                            'path': str(target.relative_to(ASSETS / 'mobile')),
                            'source_bytes': len(original), 'bytes': len(compressed),
                            'sha256': hashlib.sha256(compressed).hexdigest()})
    manifest = {'encoder': 'cwebp', 'files': entries,
                'source_bytes': sum(e['source_bytes'] for e in entries),
                'bytes': sum(e['bytes'] for e in entries)}
    (ASSETS / 'mobile/manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k: v for k, v in manifest.items() if k != 'files'}))


if __name__ == '__main__':
    main()
