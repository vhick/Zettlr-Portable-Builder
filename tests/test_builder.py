"""Pure Python structural and fake-payload tests; safe to run offline."""
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import download_official
import locate_zettlr
import package_app
import verify_package


class BuilderTests(unittest.TestCase):
    def test_release_asset_exact_64bit(self):
        r = {'tag_name':'v4.8.0', 'draft':False,'prerelease':False,'assets':[
            {'name':'Zettlr-4.8.0-x64.exe','browser_download_url':'https://example.test/x'},
            {'name':'Zettlr-4.8.0-arm64.exe','browser_download_url':'https://example.test/arm'},
            {'name':'SHA256SUMS.txt','browser_download_url':'https://example.test/sha'}]}
        self.assertEqual(download_official.choose_asset(r)[1], 'Zettlr-4.8.0-x64.exe')

    def test_reject_prerelease(self):
        with self.assertRaises(RuntimeError):
            download_official.choose_asset({'tag_name':'v4.8.0','prerelease':True})

    def test_reject_wrong_architecture(self):
        with self.assertRaises(RuntimeError):
            download_official.choose_asset({'tag_name':'v4.8.0','assets':[{'name':'Zettlr-4.8.0-arm64.exe','browser_download_url':'https://x'}]})

    def test_checksum_parsing(self):
        self.assertEqual(download_official.checksums('a'*64+'  Zettlr-4.8.0-x64.exe\n')['Zettlr-4.8.0-x64.exe'], 'a'*64)

    def test_locate_complete_payload_only(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)
            (p/'Zettlr.exe').write_bytes(b'x')
            self.assertIsNone(locate_zettlr.select(p))
            (p/'resources').mkdir()
            (p/'resources'/'app.asar').write_bytes(b'y')
            self.assertEqual(locate_zettlr.select(p), p)

    def test_appinfo_menu_location(self):
        info = package_app.appinfo('4.8.0')
        self.assertIn('AppID=ZettlrPortable', info)
        self.assertIn('Start=ZettlrPortable.exe', info)
        self.assertIn('PackageVersion=4.8.0.0', info)

    def test_no_live_installer_execution_in_workflow(self):
        content = (ROOT/'.github/workflows/build-portable.yml').read_text(encoding='utf8')
        self.assertIn("'7z.exe'", content)
        self.assertIn('workflow_dispatch',content)
        self.assertIn('retention-days: 1',content)
        self.assertIn('actions/upload-artifact@v6',content)
        self.assertIn('WaitForExit(15000)',content)
        self.assertIn('Get-AuthenticodeSignature', content)

    def test_headless_test_first(self):
        code = (ROOT/'launcher/ZettlrPortable.cs').read_text(encoding='utf8')
        self.assertLess(code.index('--portable-self-test'), code.index('Launch(args)'))
        self.assertIn('"--data-dir=" + profile', code)
        self.assertIn('EnvironmentVariables["TEMP"] = temp', code)
        self.assertIn('Directory.CreateDirectory(profile)',code)

    def test_file_traceguard_conservative(self):
        code = (ROOT/'launcher/TraceGuard.cs').read_text(encoding='utf8')
        self.assertIn('only NEW empty Zettlr AppData folders', code)
        self.assertIn('before.Contains(path)', code)
        self.assertIn('Reparse(dir)', code)
        self.assertIn('Directory.GetFileSystemEntries(dir).Length != 0',code)
        self.assertNotIn('Directory.Delete(dir, true)',code)

    def test_registry_traceguard_conservative(self):
        code = (ROOT/'launcher/RegistryTraceGuard.cs').read_text(encoding='utf8')
        self.assertIn('Registry.CurrentUser', code)
        self.assertIn('IsLinked', code)
        self.assertNotIn('DeleteSubKeyTree(',code.split('internal static int SelfTest()')[0])
        self.assertIn('AUDIT ONLY', code)
        self.assertIn('ZettlrStillRunning()', code)

    def test_offline_simulated_full_package(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)
            source = p/'source'
            (source/'resources').mkdir(parents=True)
            (source/'resources'/'app.asar').write_bytes(b'asar')
            (source/'Zettlr.exe').write_bytes(b'MZ-not-real')
            (source/'lib.dll').write_bytes(b'dll')
            (source/'uninstall.exe').write_bytes(b'not-needed')
            work = p/'work'
            (work/'icons').mkdir(parents=True)
            (work/'ZettlrPortable.exe').write_bytes(b'MZ-launcher')
            (work/'appicon.ico').write_bytes(b'icon-original')
            for size in [16,32,128]: (work/'icons'/f'appicon_{size}.png').write_bytes(b'png')
            final = package_app.build(source, work, p/'dist', '4.8.0')
            verify_package.verify(final)
            with ZipFile(final) as z:
                self.assertIn('ZettlrPortable/Data/profile/',z.namelist())
                self.assertIn('ZettlrPortable/App/Zettlr/lib.dll',z.namelist())
                self.assertNotIn('ZettlrPortable/App/Zettlr/uninstall.exe',z.namelist())
                self.assertIn('ZettlrPortable/Other/PORTABLE-README.txt',z.namelist())


if __name__ == '__main__': unittest.main()
