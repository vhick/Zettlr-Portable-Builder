# Zettlr True Portable Builder v1.0 (Windows x64)

A **manual GitHub Actions** project that downloads **official Zettlr** for Windows x64, extracts it **without installing**, and packages a PortableApps.com Menu-compatible, **ZIP-only** portable folder with an original-icon launcher.

Zettlr's own official guide documents `--data-dir` for a portable profile. The developer explicitly does not provide full support for portable setups; this builder is independent and unofficial.

## Quick setup for beginners

1. **Download and extract this builder ZIP** to your computer.
2. Create a new GitHub repository named `Zettlr-Portable-Builder` (public or private).
3. Upload **all the extracted files and folders** into the **root of that repository**. Keep `.github/workflows/build-portable.yml` in its existing folder. Commit the changes.
4. Open **Actions** on GitHub. Click **Build Zettlr Portable (Manual)**.
5. Select **Run workflow**, leave `version` as `latest`, and click **Run workflow** again.
6. On success, open the completed run and download the **Zettlr-Portable-Windows-x64** artifact.
7. Extract that artifact to obtain `Zettlr-Portable-VERSION-Windows-x64.zip`. Extract the **application ZIP** into your preferred location.
8. Open the `ZettlrPortable` folder and run **`ZettlrPortable.exe`**. Do not run the internal `App\Zettlr\Zettlr.exe` directly.

No setup installer, administrator permission, or PowerShell script is needed on your own computer. Windows may show a warning about the custom **unsigned launcher**; the official Zettlr.exe remains unmodified.

### Version selection

`latest` downloads the stable official GitHub release. You can instead type `v4.8.0` to build a specific existing stable release. The workflow selects only the official `Zettlr-VERSION-x64.exe` asset and checks the upstream checksum file when available, plus the Windows Authenticode signature. Pre-release assets are refused.

### Portable application structure

```text
ZettlrPortable/
├── ZettlrPortable.exe         <-- start here (original Zettlr icon)
├── App/
│   ├── Zettlr/               <-- upstream Windows app, replace on upgrades
│   │   ├── Zettlr.exe
│   │   ├── resources/app.asar
│   │   └── ...
│   └── AppInfo/              <-- PortableApps.com Menu metadata + original icons
├── Data/
│   ├── profile/              <-- all Zettlr-managed configuration, snippets, caches
│   ├── Temp/                 <-- subprocess temporary storage, where supported
│   └── TraceGuard/           <-- cleanup logs
└── Other/
    ├── Source/              <-- launcher source provided
    └── PORTABLE-README.txt
```

### Portable data and workspaces

- **Zettlr settings, snippets, internal caches, import/export profiles, dictionaries, etc.** are redirected into `Data\profile` using Zettlr's supported `--data-dir=ABSOLUTE_PATH` switch.
- **Markdown files, research notes, pictures, and projects** remain in their original storage location (you choose where to save them). They are **not automatically copied into Data**. For the entire project to travel together, store your project directory alongside your portable application and reopen it after moving PCs.
- The program may remember absolute file, workspace, Pandoc, LaTeX, or Zotero paths; you may need to update these if your drive letters change.
- Extensions and external converters need to be separately portable to work across PCs.
- The builder does **not** import any installed Zettlr settings from your PC. To migrate an existing profile, copy `%APPDATA%\Zettlr` into `Data\profile` yourself *before first launch*, with Zettlr closed.

### Dynamic TraceGuard: filesystem + registry

When the root launcher starts it records the contents of `%APPDATA%\Zettlr`, `%LOCALAPPDATA%\Zettlr`, and narrowly scoped Windows Registry locations. Once Zettlr completely exits, it compares them. It can remove **only new, empty folders** created by the session in those Zettlr AppData locations. The main documented case is `%APPDATA%\Zettlr\Dictionaries` (an Electron bug).

Registry TraceGuard logs changes under `HKCU\Software\Zettlr`, and relevant user-level file associations. It automatically removes **only newly added string values that explicitly reference the portable binary's full path within `HKCU\Software\Zettlr`**, and newly created empty keys there. Windows file associations, default programs, `HKLM`, and unrelated registry entries are **never modified**. Pre-existing entries, populated folders, and reparse points (junctions/symlinks) are preserved. No administrator permission is requested.

Logs appear after exit:

- `Data\TraceGuard\last-run.log` — file remnants/cleanups/skips.
- `Data\TraceGuard\registry.log` — registry audit and safely removed items.

If an installed Zettlr process is running, the launcher refuses to start. Other Zettlr processes still running after portable exit cause file cleanup to be skipped. This protects other sessions but means some new empty remnants can legitimately remain for safety. The launcher doesn't claim system-wide sandboxing. Windows-managed recent-files lists, shell histories, caches, network logs and changes made by Pandoc, LaTeX or Zotero are outside its cleanup scope.

### Upgrading without losing Data

1. Close Zettlr fully; ensure no `Zettlr.exe` remains running.
2. **Back up the entire `Data` folder** to a safe location.
3. Run the builder again at a newer version and extract its ZIP.
4. In the **existing portable folder**, replace **only** `App`, `Other`, and `ZettlrPortable.exe` with the new copies.
5. Keep your original `Data` folder completely untouched. Open the portable launcher and check your settings.

Do not overwrite the entire folder using a new ZIP and accidentally delete the `Data` folder.

### GitHub Actions safeguards

- Windows x64 runner; manually triggered workflow only.
- Official release selection + checksum verification if provided + Authenticode verification.
- Upstream installer **extracted, never executed**.
- Original application icon extracted as a multi-resolution ICO, plus menu PNGs.
- Compiled `ZettlrPortable.exe` uses explicit absolute source paths to avoid C# compilation path errors.
- Three headless Windows tests (`--portable-self-test`, `--traceguard-self-test`, `--registrytrace-self-test`) have a **15-second timeout per test**.
- Package validation checks executable, Electron resources, metadata, original icon, and empty profile folder.
- **Only the final ZIP** is uploaded; **1-day** artifact retention.

### Licensing, security, and status

Zettlr is © upstream contributors and distributed subject to its original licenses. This builder and its MIT-licensed launcher are separate third-party contributions. Retain upstream attribution; do not distribute a modified application as an official Zettlr release.

**Local tests are not a substitute for a complete Windows runtime test.** The compiled launcher, actual official installer extraction, and real-world host cleanup must pass GitHub Actions and your PC before the result can be called verified true portable.

**References:**

- Original project: https://github.com/Zettlr/Zettlr
- Official portable guide: https://docs.zettlr.com/en/guides/portable.html
- Official documentation on `--data-dir` and `Dictionaries` remnant: https://github.com/Zettlr/Zettlr/blob/develop/README.md
- Latest official releases: https://github.com/Zettlr/Zettlr/releases
