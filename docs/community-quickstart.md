# Build and run the community-patch branch on Windows

The fork's experimental branch is `feature/community-performance-intel`.
It keeps the original FPS/resolution and live graphics controls. Community
patches are separate, off by default, and require a restart after toggling.

## Get a Windows build through GitHub Actions

1. Open your fork's **Actions** tab. If GitHub says workflows are disabled in
   the fork, enable them for this repository.
2. Select **release**, then **Run workflow**. Choose
   `feature/community-performance-intel` from the branch selector and run it.
   A manual run builds packages as downloadable artifacts; it does not publish
   a GitHub release or require the upstream release-signing secret.
3. Wait for **package-windows** to succeed. Open the run's summary and download
   the **windows** artifact. A cold dependency build can take a while; the job
   timeout is 90 minutes. If it fails, open that job's failing step and log.
4. Extract the downloaded artifact ZIP. Inside it, extract `bbhost-win-*.zip`
   too. Keep `bbhost.exe` with its `patches`, `plugins` and other packaged files.
   The `.debug.exe` is for debugging; run `bbhost.exe`.

The separate **build** workflow builds Linux and runs tests; it does not
produce the Windows package. A green build job is not proof the Windows ZIP
has been produced. Build success also does not prove the game works on your
hardware.

For a local build, use the Linux/Windows cross-build instructions in
[building.md](building.md). Windows uses Clang plus mingw-w64 on Linux;
opening the project in Visual Studio/MSVC is not the supported build path.
The existing `tools/ci_windows.sh` can build and package it in an Arch Linux
environment. You do not need this local toolchain to download an Actions build.

## Run a baseline first

You need your own Bloodborne dump with the 1.09 update applied and its decrypted
1.09 `eboot.bin` (ELF). The game folder is the one containing `dvdroot_ps4`.
A sibling `CUSA00900-UPDATE` folder is supported when your base folder is
`CUSA00900`. No game files need to be uploaded to GitHub.

You can check the executable in Windows PowerShell:

```powershell
Get-FileHash "D:\Games\Bloodborne\eboot.bin" -Algorithm SHA256
```

The expected hash is:

```text
941f887a562aae054fac35af8cc8f27cf075f3d4cc2e029fb5ae2a663aaa5ae7
```

Start `bbhost.exe`, choose the game folder and decrypted executable in the
setup window, and press Play. First run it with all imported patches off.
You need an x86-64 Windows 10/11 PC and a Vulkan 1.3 graphics driver. Upstream
recommends 16 GB RAM and 8 GB VRAM. First-run shader compilation can cause
hitches; let the "Building shaders" queue finish before comparing performance.

To reopen setup, run `bbhost.exe --setup`. F10 opens PC settings in game.
Configuration is normally in `%APPDATA%\bbhost`; game saves and caches are
normally under `%LOCALAPPDATA%\bbhost\data`. See [running.md](running.md)
for log locations, controls, saves, and troubleshooting.

## Add optional community patches

Download the feature branch's source (**Code > Download ZIP**) and extract it.
You only need Python and `tools/import_community_patches.py` to generate
manifests; you do not need to compile the source locally. The importer uses
Python's standard library. Python 3.11 or later is suitable.

In PowerShell, navigate to the extracted source folder. Replace these example
paths with the paths on your PC:

```powershell
py tools\import_community_patches.py --list
py tools\import_community_patches.py --xml "D:\Patches\Bloodborne.xml" --eboot "D:\Games\Bloodborne\eboot.bin" --output "D:\Patches\bbhost-imported-new" --patch performance-fast-rsqrt --patch intel-black-tonemap
```

The output folder must not exist yet. The importer reads the executable and
XML but never modifies them. It checks the executable hash, exact reviewed XML
sites and executable-segment bounds, then includes the original bytes in every
manifest so the loader can refuse mismatches.

Copy the resulting `.toml` files into the default mods patch directory:

```text
%LOCALAPPDATA%\bbhost\data\mods\patches
```

Create that folder if needed. If you have customized `paths.data` or
`paths.mods`, use `<your mods folder>\patches` instead. Reopen setup and enable
one imported option at a time in **Patches**, then restart the game. **All on**
does not enable these default-off experiments. Check `patch: <name>` in the
log to confirm application or refusal.

`performance-fast-rsqrt` is only seven fast-math sites from the large bundle:
it changes numerical precision and may affect visuals or gameplay. No measured
speedup is promised. `intel-black-tonemap` is for the black-tonemap symptom,
especially in DLC areas. Compare the same scene, resolution and FPS cap.

The effect-removing `intel-sfx-fallback` is not imported by the example. bbhost
already fixes the underlying Windows ribbon red-zone issue without disabling
those effects. Import it explicitly only when diagnosing a remaining SFX crash:

```powershell
py tools\import_community_patches.py --xml "D:\Patches\Bloodborne.xml" --eboot "D:\Games\Bloodborne\eboot.bin" --output "D:\Patches\bbhost-sfx-new" --patch intel-sfx-fallback
```

To undo an imported option, uncheck it and restart. To start with all manifest
patches disabled from the current PowerShell session:

```powershell
$env:BBHOST_PATCHES = "0"
.\bbhost.exe --setup
```

After testing, remove that session override:

```powershell
Remove-Item Env:BBHOST_PATCHES
```

See [modding.md](modding.md#importing-reviewed-community-patches) for the
compatibility choices and the excluded timing, resolution and other sites.
