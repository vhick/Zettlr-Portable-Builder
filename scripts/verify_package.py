"""Verify the Windows artifact ZIP layout and mandatory portable assets."""
from pathlib import Path
import zipfile
from package_app import ROOT, NAME


def verify(path):
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        mandatory = [
            f'{NAME}/{NAME}.exe',
            f'{NAME}/App/Zettlr/Zettlr.exe',
            f'{NAME}/App/Zettlr/resources/app.asar',
            f'{NAME}/App/AppInfo/appinfo.ini',
            f'{NAME}/App/AppInfo/appicon.ico',
            f'{NAME}/App/AppInfo/appicon_16.png',
            f'{NAME}/App/AppInfo/appicon_32.png',
            f'{NAME}/App/AppInfo/appicon_128.png',
            f'{NAME}/Data/profile/',
            f'{NAME}/Data/TraceGuard/',
            f'{NAME}/Other/Source/ZettlrPortable.cs',
        ]
        missing = [item for item in mandatory if item not in names]
        if missing: raise AssertionError('Missing required ZIP items: ' + repr(missing))
        if any('/uninstall' in n.lower() for n in names): raise AssertionError('Uninstaller packaged')
        if any(n.startswith(NAME+'/AppData/') for n in names): raise AssertionError('Host data accidentally packaged')
        ini = z.read(f'{NAME}/App/AppInfo/appinfo.ini').decode('utf-8')
        if 'Start=ZettlrPortable.exe' not in ini or 'AppID=ZettlrPortable' not in ini:
            raise AssertionError('PortableApps metadata invalid')
    print('PASS: complete official program + portable launcher + profile + metadata + source')


if __name__ == '__main__':
    archives = sorted((ROOT / 'dist').glob('*.zip'))
    if len(archives) != 1: raise RuntimeError('Expected exactly one ZIP in dist')
    verify(archives[0])
