"""Package official Zettlr binaries with preserved-by-upgrades Data, original icon."""
from pathlib import Path
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAME = 'ZettlrPortable'


def appinfo(version):
    normalized = '.'.join((version.split('.') + ['0', '0', '0', '0'])[:4])
    return f'''[Format]
Type=PortableApps.comFormat
Version=3.8

[Details]
Name=Zettlr Portable
AppID=ZettlrPortable
Publisher=Zettlr contributors
Homepage=https://www.zettlr.com/
Category=Office
Description=Zettlr Markdown editor with supported --data-dir portable profile
Language=Multilingual

[License]
Shareable=true
OpenSource=true
Freeware=true
CommercialUse=true

[Version]
PackageVersion={normalized}
DisplayVersion={version}

[Control]
Icons=1
Start=ZettlrPortable.exe
'''


def copy_program(source, dest):
    if not (source / 'Zettlr.exe').is_file() or not (source / 'resources' / 'app.asar').is_file():
        raise ValueError('Upstream Electron payload missing Zettlr.exe or resources/app.asar')
    for item in source.iterdir():
        if item.is_symlink(): raise ValueError('Symlink in upstream application payload: ' + str(item))
        if item.name.lower().startswith('uninstall') or item.name.lower() in {'unins000.exe', 'unins000.dat'}:
            continue
        target = dest / item.name
        if item.is_dir(): shutil.copytree(item, target, symlinks=False)
        elif item.is_file(): shutil.copy2(item, target)


def build(source, work, out, version):
    if not re.fullmatch(r'\d+\.\d+\.\d+', version): raise ValueError('Unexpected version')
    root = work / NAME
    if root.exists(): shutil.rmtree(root)
    program = root / 'App' / 'Zettlr'
    meta = root / 'App' / 'AppInfo'
    others = root / 'Other' / 'Source'
    for folder in [program, meta, others, root / 'Data' / 'profile', root / 'Data' / 'Temp', root / 'Data' / 'TraceGuard']:
        folder.mkdir(parents=True, exist_ok=True)
    copy_program(source, program)
    launcher = work / 'ZettlrPortable.exe'
    icon = work / 'appicon.ico'
    if not launcher.is_file() or not icon.is_file(): raise FileNotFoundError('Launcher or original icon missing')
    shutil.copy2(launcher, root / 'ZettlrPortable.exe')
    shutil.copy2(icon, meta / 'appicon.ico')
    for size in (16, 32, 128):
        shutil.copy2(work / 'icons' / f'appicon_{size}.png', meta / f'appicon_{size}.png')
    (meta / 'appinfo.ini').write_text(appinfo(version), encoding='utf-8')
    for source_name in ['ZettlrPortable.cs', 'TraceGuard.cs', 'RegistryTraceGuard.cs']:
        shutil.copy2(ROOT / 'launcher' / source_name, others / source_name)
    (root / 'Other' / 'PORTABLE-README.txt').write_text(
        f'Zettlr Portable {version} — Windows x64\n\n'
        'START: Double-click ZettlrPortable.exe at the root of the portable folder.\n'
        'Do not run App\\Zettlr\\Zettlr.exe directly (it would use Windows AppData).\n\n'
        'DATA: Data\\profile keeps configuration, caches, snippets, dictionaries, etc.\n'
        'Data\\Temp receives temporary files from processes inheriting the environment.\n'
        'Data\\TraceGuard logs after each launch.\n\n'
        'DOCUMENTS: Markdown files/workspaces live wherever YOU save them.\n'
        'Zettlr may store ABSOLUTE paths to these files, and to external programs\n'
        '(Pandoc, LaTeX, Zotero). Moving between PCs may require relinking.\n\n'
        'UPGRADE: Close Zettlr. Back up Data. Replace App, Other and the root EXE.\n'
        'NEVER overwrite your existing Data folder with a new package.\n\n'
        'TRACEGUARD: Captures snapshots before launch and after exit; deletes ONLY\n'
        'newly created EMPTY subfolders in AppData\\Roaming\\Zettlr or\n'
        'AppData\\Local\\Zettlr, including the documented Electron Dictionaries\n'
        'remnant. Preserves old items, symlinks/junctions and populated directories.\n'
        'Registry changes are logged under Data\\TraceGuard\\registry.log.\n'
        'Only new exact portable-path-linked values under HKCU\\Software\\Zettlr\n'
        'may be cleaned; Windows associations and HKLM are AUDIT-ONLY.\n\n'
        'LIMITS: Windows caches, recent file lists, shell integration, file dialogs,\n'
        'and external export tools can leave traces. This is not a sandbox.\n'
        'Do not enable file associations/default-app integration for strict portability.\n\n'
        'LICENSE: Zettlr is distributed under its original upstream license.\n'
        'Source: https://github.com/Zettlr/Zettlr\n'
        'Custom builder launcher and TraceGuard source: Other\\Source.\n', encoding='utf-8')
    (others / 'SOURCE-NOTICE.txt').write_text(
        'Original Zettlr binaries, embedded app resources, and original icon remain upstream-owned.\n'
        'https://github.com/Zettlr/Zettlr\n'
        'Custom launcher and TraceGuard code: MIT License; see builder license.\n', encoding='utf-8')
    out.mkdir(parents=True, exist_ok=True)
    result = out / f'Zettlr-Portable-{version}-Windows-x64.zip'
    with zipfile.ZipFile(result, 'w', zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
        for item in sorted(root.rglob('*')):
            name = item.relative_to(root.parent).as_posix()
            if item.is_dir(): z.writestr(name + '/', b'')
            else: z.write(item, name)
    return result


def main():
    version = (ROOT / 'work' / 'version.txt').read_text(encoding='utf-8').strip()
    exe = Path((ROOT / 'work' / 'source_path.txt').read_text(encoding='utf-8').strip())
    package = build(exe.parent, ROOT / 'work', ROOT / 'dist', version)
    print('Created', package, package.stat().st_size)


if __name__ == '__main__': main()
