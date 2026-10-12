# Run an already merged dvdroot_ps4 without changing the game install

Use the `feature/merged-asset-overlay` branch, which includes the earlier
community performance/Intel patch options. Build it through Actions > release >
Run workflow with this branch selected, then download the windows artifact.

In `bbhost.exe --setup`, on the Game tab:

1. Keep **Game folder** pointed at your original install, and keep the original
   decrypted 1.09 **Eboot** selected.
2. Set **Modded dvdroot_ps4 folder** to the merged folder itself, for example
   `D:/Games/Bloodborne/CUSA00900-mods/dvdroot_ps4`.
3. Check **Use merged asset mods (restart required)** and press Play.

Select the active merged output, not BB_Launcher's `Mods` library containing
individual unmerged mods. Do not select the parent of dvdroot_ps4, or put another
dvdroot_ps4 inside it. A partial tree is fine: missing files fall back to the
existing bbhost overlay, plugin/generated layers, update, and original install.
The selected tree wins over all of those for matching asset files.

To return to the previous setup, uncheck the switch and restart. The selected
path is remembered. Community patch manifests remain in the existing
`paths.mods/patches` folder, and their switches are unaffected. FPS/resolution
code is unchanged. The merged folder does not supply eboot.bin or code patches.

Equivalent settings in your user bbhost.toml (merge these keys into existing
sections rather than adding duplicate section headers):

```toml
[paths]
asset_mods = "D:/Games/Bloodborne/CUSA00900-mods/dvdroot_ps4"

[mods]
asset_overlay = true
```

Relative paths resolve against the config file. The feature is off by default.
The launcher refuses Play while an enabled directory is missing; a headless
run logs a missing directory and uses the previous layers.

## What BB_Launcher does

Inspected BB_Launcher at commit `0fdce9f094d760d65cb1871b8ac27d4fcace0e81`:
[ModManager.cpp](https://github.com/rainmakerv3/BB_Launcher/blob/0fdce9f094d760d65cb1871b8ac27d4fcace0e81/modules/ModManager.cpp)
creates `<install>-mods/dvdroot_ps4`. Activation populates that tree with
symlinks to active mods (UAC/Linux builds) or copies (the Windows no-UAC build).
[bblauncher.cpp](https://github.com/rainmakerv3/BB_Launcher/blob/0fdce9f094d760d65cb1871b8ac27d4fcace0e81/modules/bblauncher.cpp)
still starts shadPS4 with `--game` pointing at the original eboot. The launcher
prepares a separate tree for the emulator; it does not merge those assets into
the original install at launch. bbhost now reads that prepared tree directly
through its own file layer, without requiring shadPS4 or its mounting code.

The selected tree is trusted for reads, including symlink targets outside it,
as needed by BB_Launcher. Do not move or change it or its targets while the game
runs. Broken links fall back to lower layers. Guest writes, creation, deletion,
renaming and truncation of asset files are refused, including original/update
assets; saves and temporary files retain their normal writable locations.

## Verify a mod and diagnose differences

The log starts with `FS merged assets=<directory>` and prints the first 32
combined overlay hits, including `FS merged assets: <guest path> -> <mod file>`.
To trace a specific file on later accesses, set `BBHOST_FS_TRACE` for that
path using PowerShell before starting the game:

```powershell
$env:BBHOST_FS_TRACE = "dvdroot_ps4/chr/"
.\bbhost.exe --setup
```

Remove the override afterward with `Remove-Item Env:BBHOST_FS_TRACE`.
Keep a copy of saves before testing mods that change progression or params.
A readable mod file is not proof it is compatible with bbhost's translated
code. Mods requiring shadPS4-specific code patches or emulator behavior need
separate work. Mods replacing `menu/optionsetting.gfx` or message bundles may
replace the PC menu additions; event/map mods may conflict with PC enhancements.
For diagnosis, compare the same scene with this switch off, and separately try
turning off affected PC enhancements. No features are automatically disabled.

This first implementation replaces files requested by the game. It deliberately
does not replace directory listings with the partial merged tree; listings stay
with the existing lower layer. Mods that rely on discovery of entirely new
filenames by directory enumeration need additional support. It does not merge
archive contents, stack individual mods, download mods, or manage activation.

## Empty assets and restart behavior

Close bbhost completely and start it again after changing the merged-assets
setting. A computer restart is unnecessary. Files in either tree are not
modified by enabling this option.

On Windows, symlink/reparse-point metadata is read from the opened target,
so a nonempty mod file is not mistaken for an empty link. The same target
metadata is used for asset validation, open logging and stat/fstat.

Zero-byte files in the selected merged tree (including symlinks to empty files)
are skipped with an `ignoring empty replacement` log message. Reads and stat
then use the existing lower asset layers. A valid, nonempty replacement still
wins. This does not repair an empty original/update file or a nonempty corrupt
archive, and does not change other overlay layers' behavior.

If a startup abort reports `menu/common.tpf.dcx -> 0 bytes`, inspect that file and its symlink target
in the selected merged tree and compare a run with the option off. The full
log's `FS merged assets:` lines identify which mod paths were used. The
file-loader's generic advice about an incomplete dump also appears when an
empty mod file shadows a complete dump; it does not prove the original files
were changed. If the new build still fails, provide the full `.log` listed
at the top of the console so the actual source path can be checked.
