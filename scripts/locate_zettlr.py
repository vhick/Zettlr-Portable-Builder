"""Locate a *complete* upstream Electron payload after extracting an NSIS installer.

7z sometimes exposes an embedded app-64.7z rather than app files directly.
Never invoke the installer. Always choose a matching Zettlr.exe + resources/app.asar.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def candidates(folder):
    for exe in folder.rglob('Zettlr.exe'):
        parent = exe.parent
        if (parent / 'resources' / 'app.asar').is_file():
            yield parent


def select(folder):
    found = list(candidates(folder))
    if not found: return None
    return min(found, key=lambda p: (len(p.parts), len(str(p))))


def locate(folder, sevenzip='7z'):
    result = select(folder)
    if result: return result
    nested = sorted(folder.rglob('app-64.7z')) + sorted(folder.rglob('app-64.7z.001'))
    # NSIS Electron-builder package: 7-Zip may leave app-64.7z nested.
    if len(nested) > 8: raise RuntimeError('Too many embedded payload archives.')
    for index, archive in enumerate(nested):
        nested_dest = folder.parent / ('payload-' + str(index))
        nested_dest.mkdir(parents=True, exist_ok=True)
        subprocess.run([sevenzip, 'x', '-y', '-o' + str(nested_dest), str(archive)], check=True, timeout=600)
        result = select(nested_dest)
        if result: return result
    raise RuntimeError('Zettlr.exe and resources/app.asar not found. Upstream installer extraction changed.')


if __name__ == '__main__':
    exe = locate(ROOT / 'work' / 'extracted', sys.argv[1] if len(sys.argv) > 1 else '7z') / 'Zettlr.exe'
    (ROOT / 'work' / 'source_path.txt').write_text(str(exe.resolve()), encoding='utf-8')
    print('Complete Zettlr application payload:', exe)
