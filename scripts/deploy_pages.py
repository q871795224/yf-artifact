#!/usr/bin/env python3
"""Build and publish the static game to a repository's gh-pages branch."""

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from build_pages import build, ROOT


def run(args, cwd=ROOT, capture=False, check=True):
    return subprocess.run(args, cwd=cwd, check=check, text=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', default='q871795224/yf-artifact')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', args.repo):
        parser.error('Expected --repo owner/name')
    site = ROOT / 'dist/gh-pages'
    print(json.dumps(build(site), ensure_ascii=False), flush=True)
    url = f'https://github.com/{args.repo}.git'
    existing = run(['git', 'ls-remote', '--heads', url, 'gh-pages'], capture=True).stdout.strip()
    with tempfile.TemporaryDirectory(prefix='yf-artifact-pages-') as temp:
        checkout = Path(temp) / 'checkout'
        if existing:
            run(['git', 'clone', '--quiet', '--depth', '1', '--single-branch', '--branch', 'gh-pages', url, str(checkout)])
            for path in checkout.iterdir():
                if path.name == '.git':
                    continue
                shutil.rmtree(path) if path.is_dir() else path.unlink()
        else:
            checkout.mkdir()
            run(['git', 'init', '--quiet', '-b', 'gh-pages'], checkout)
            run(['git', 'remote', 'add', 'origin', url], checkout)
        shutil.copytree(site, checkout, dirs_exist_ok=True)
        name = run(['git', 'config', 'user.name'], capture=True).stdout.strip()
        email = run(['git', 'config', 'user.email'], capture=True).stdout.strip()
        run(['git', 'config', 'user.name', name], checkout)
        run(['git', 'config', 'user.email', email], checkout)
        run(['git', 'add', '--all'], checkout)
        changes = run(['git', 'diff', '--cached', '--quiet'], checkout, check=False).returncode
        if changes:
            run(['git', 'commit', '--quiet', '-m', 'Deploy playable static game'], checkout)
            run(['git', '-c', 'http.postBuffer=157286400', '-c', 'http.version=HTTP/1.1',
                 '-c', 'credential.helper=', '-c', 'credential.helper=!gh auth git-credential',
                 'push', 'origin', 'gh-pages'], checkout)
        else:
            print('Published files already match this build.', flush=True)
    settings = run(['gh', 'api', f'repos/{args.repo}/pages'], capture=True, check=False)
    if settings.returncode:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json') as body:
            json.dump({'build_type': 'legacy', 'source': {'branch': 'gh-pages', 'path': '/'}}, body)
            body.flush()
            created = run(['gh', 'api', '--method', 'POST', f'repos/{args.repo}/pages', '--input', body.name], capture=True, check=False)
            # A failed response can still mean GitHub accepted the request.
            # Read the resulting state before reporting failure or retrying.
            settings = created if not created.returncode else run(
                ['gh', 'api', f'repos/{args.repo}/pages'], capture=True, check=False)
            if settings.returncode:
                raise RuntimeError(created.stderr or settings.stderr)
    published = json.loads(settings.stdout)
    print(f"GitHub Pages: {published['html_url']}", flush=True)
    print('The Pages build may take a few minutes; check gh run list for deployment status.', flush=True)


if __name__ == '__main__':
    main()
