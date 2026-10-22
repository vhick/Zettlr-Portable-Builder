"""Download a Zettlr Windows x64 installer from the official GitHub Release.

Only a stable (not draft/prerelease) release and an exact expected filename is accepted.
If official SHA256SUMS.txt is included, its SHA256 is mandatory.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://api.github.com/repos/Zettlr/Zettlr/releases'
VERSION = re.compile(r'^v?(\d+\.\d+\.\d+)$')


def request(url, headers=None, attempts=3):
    hdr = {'User-Agent': 'Zettlr-Portable-Builder/1.0', 'Accept': 'application/vnd.github+json'}
    if headers: hdr.update(headers)
    for attempt in range(attempts):
        try:
            return urlopen(Request(url, headers=hdr), timeout=90)
        except (HTTPError, URLError, TimeoutError):
            if attempt + 1 == attempts: raise
            time.sleep(2 ** attempt)


def asset_map(release):
    assets = release.get('assets') or []
    return {a['name']: a['browser_download_url'] for a in assets if a.get('browser_download_url')}


def choose_asset(release):
    if release.get('draft') or release.get('prerelease'):
        raise RuntimeError('Draft and prerelease builds are not permitted.')
    match = VERSION.fullmatch(release.get('tag_name', ''))
    if not match: raise RuntimeError('Unexpected stable release tag: ' + str(release.get('tag_name')))
    version = match.group(1)
    wanted = f'Zettlr-{version}-x64.exe'
    assets = asset_map(release)
    if wanted not in assets:
        raise RuntimeError('No official Windows x64 installer named ' + wanted + '. Found: ' + ', '.join(assets))
    return version, wanted, assets[wanted], assets.get('SHA256SUMS.txt')


def checksums(text):
    result = {}
    for line in text.splitlines():
        match = re.fullmatch(r'([0-9a-fA-F]{64})\s+\*?(.+)', line.strip())
        if match: result[match.group(2).strip()] = match.group(1).lower()
    return result


def run(tag, destination):
    if tag != 'latest':
        match = VERSION.fullmatch(tag)
        if not match: raise ValueError('Version must be latest or vMAJOR.MINOR.PATCH')
        tag = 'v' + match.group(1)
    endpoint = BASE + ('/latest' if tag == 'latest' else '/tags/' + tag)
    with request(endpoint) as source: release = json.load(source)
    version, name, installer_url, hash_url = choose_asset(release)
    destination.mkdir(parents=True, exist_ok=True)
    installer = destination / 'ZettlrSetup.exe'
    digest = hashlib.sha256()
    count = 0
    with request(installer_url, {'Accept': 'application/octet-stream'}) as response, installer.open('wb') as output:
        while True:
            buf = response.read(1024 * 1024)
            if not buf: break
            count += len(buf)
            if count > 800 * 1024 * 1024: raise RuntimeError('Unexpectedly large upstream asset')
            digest.update(buf)
            output.write(buf)
            if count % (16 * 1024 * 1024) == 0: print('Downloaded', count // (1024 * 1024), 'MiB', flush=True)
    if count < 10 * 1024 * 1024: raise RuntimeError('Installer unexpectedly small.')
    actual = digest.hexdigest()
    if hash_url:
        with request(hash_url, {'Accept': 'application/octet-stream'}) as response:
            sums = checksums(response.read(250000).decode('utf-8-sig'))
        if name not in sums: raise RuntimeError('Official checksum file omitted the Windows asset')
        if sums[name] != actual: raise RuntimeError('SHA256 checksum mismatch; refusing to package')
        print('PASS official release SHA256 checksum:', actual)
    else:
        print('WARNING: No SHA256SUMS asset; Windows Authenticode signature must pass in workflow.', actual)
    (destination.parent / 'version.txt').write_text(version, encoding='utf-8')
    print('Official Windows release:', version, name, 'size:', count)
    return version


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--version', default='latest')
    args = p.parse_args()
    run(args.version, ROOT / 'work' / 'download')
