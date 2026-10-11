# Modding

bbhost never modifies the game files. Every change is layered on top at run
time, from a few places:

| What | Where | Needs code? |
|---|---|---|
| Replacement files (menus, text, textures, layouts) | the mods folder | no |
| Param values (weapons, enemies, item lots, shops) | `<mods>/params/*.toml` | no |
| Byte patches to the game's code | `patches/*.toml` | no |
| Anything else | a plugin ([plugins.md](plugins.md)) | yes |

## The mods folder

`paths.mods` in `bbhost.toml` (default `<data>/mods`) is checked before the
game dump for every file the game opens. A file at
`<mods>/dvdroot_ps4/<path>` replaces the game's `dvdroot_ps4/<path>`. The log
lists the files served from it (`FS overlay: ...`).

Files are matched by their path as the game requests it, so a replacement
keeps the original's name and container format (`.dcx` stays compressed).

## Params

The game's numbers live in 62 param tables: weapons, armour, enemies, attacks,
magic, item lots, shops, special effects, the lock-on camera and more. bbhost
reads the field definitions the game ships (`dvdroot_ps4/paramdef`), so fields
are named the way FromSoftware named them.

Put one TOML file per table in `<mods>/params/<TableName>.toml`:

```toml
# <mods>/params/EquipParamWeapon.toml - the Saw Cleaver is row 1000000
row.1000000.correctStrength = 250
row.1000000.weight = 0.5

# <mods>/params/LockCamParam.toml - every row
row.all.camDistTarget = 5.5
row.all.chrLockRangeMaxRadius = 30

# An array element is row.<id>.<name>[<i>]. Where no name fits, use a raw
# type and byte offset: f32 i32 u32 i16 u16 i8 u8.
row.1000000.f32_0x10 = 1.5
```

Table names are the ones the log prints (`params: slot N <TableName>: <TYPE>,
R rows`). To see a row before changing it:

```sh
BBHOST_PARAM_DUMP="EquipParamWeapon:1000000,LockCamParam:0" ./bbhost
```

This prints every field with its value, type and the game's own description.
Overrides apply whenever a table loads, including when the game reloads one.
A table whose rows do not match its definition is refused with a log line
instead of being written wrongly.

`tools/bbparam.py` reads and searches the param tables of a dump from the
command line (set `BBHOST_APP0` to the game folder).

## Lighting and post-processing

Per-area lighting, fog, tone mapping and post effects are data in
`param/drawparam/*.gparam.dcx`. `tools/gparam.py --list <file>` shows a
file's parameters; `tools/gparam.py --set "Name=value" <dump> <mods>` writes
edited copies of every file into the mods folder.

## Text

Message banks (`msg/<lang>/*.msgbnd.dcx`, FMG files) are read through the mods
folder as well. `src/engine/menu_assets.cpp` shows how bbhost adds its own
entries to the game's banks at start, in every language.

## Patch manifests

A byte patch is a TOML file. bbhost reads every `*.toml` in these folders, a
later file replacing an earlier one with the same name:

1. `<exe dir>/patches` (the release package)
2. `<exe dir>/../patches` (a build tree: `build/bbhost` reads the repository's `patches/`)
3. `<mods>/patches` (a mod's own)

```toml
[patch]
name = "skip-intro"
eboot = "941f887a562aae054fac35af8cc8f27cf075f3d4cc2e029fb5ae2a663aaa5ae7"
description = "the three company logos at startup are skipped"
option = "startup.skip_intro"      # optional: a setting that switches it
enabled = true                      # optional, default true
default_on = true                   # optional; false offers an opt-in launcher switch

[site.logo-fromsoft]
address = "0x04d99138"              # Binary Ninja address (image at 0x400000)
expect = "4c 00 6f 00"              # the bytes that must be there
bytes = "00 00 00 00"               # the bytes written, same length
kind = "code"                       # optional: "code" (default) or "data"
```

- `eboot` is the SHA-256 of the decrypted eboot the addresses belong to. A
  file for another build is skipped.
- Every site's `expect` is checked before anything is written; one mismatch
  refuses the whole file. A site that already holds `bytes` counts as done.
- `default_on = false` leaves a patch off until `[patches] <name> = true`
  or its launcher checkbox enables it individually. The All on button skips
  default-off entries. `enabled = false` instead locks it off.
  Existing manifests keep their default-on behavior.
- `kind = "code"` restores the page to read-only and executable afterwards;
  `"data"` leaves it writable.
- `BBHOST_PATCHES=0` skips all manifests. The log has one line per file:
  written, skipped or refused.

The setup window's Patches tab lists every manifest with a switch. A patch
that follows an `option` is switched by that setting; any other is turned off
with `<name> = false` under `[patches]` in `bbhost.toml`.

Shipped patches:

| File | Effect |
|---|---|
| `skip-intro.toml` | skips the company logos and the "Exit Game may not have been selected" warning (illusion's 1.09 patch) |
| `fov-uncap.toml` | removes the 38-48 degree limit on the camera's field of view |
| `quick-reentry.toml` | loads after a death or lamp travel end when the area is ready instead of after 12 seconds (on by default) |
| `ingame-post-processors.toml` | three resource post-processors during play instead of two: streaming settles sooner, with more hitches meanwhile (off by default) |
| `deflate-level.toml` | the game's run-time compression at level 1 instead of 9, removing a periodic ~25 ms hitch |
| `old-hunters.toml` | makes the game treat itself as The Old Hunters edition, so the DLC is available (Kyo's 1.09 patch) |
| `debug-camera.toml` | restores the debug free camera (Lance McDonald's 1.09 patch): hold Action and press L3 to cycle its modes. Off by default; it replaces a debug-menu test step, which then must not be used |

Patches whose bytes depend on settings, and anything that needs a hook rather
than fixed bytes, are written in code or as plugins.

## Event scripts and talk scripts

The maps' event scripts (`event/*.emevd.dcx`) and the NPC talk scripts
(`script/talk/*.talkesdbnd.dcx`) can be rewritten at start from the player's
own dump and served through the overlay, so nothing is redistributed. Two of
bbhost's PC enhancements work this way and serve as examples:

- `src/engine/maiden_events.cpp` rewrites the invasion events so the late
  areas take two invaders (the five-player sessions).
- `src/engine/rebirth.cpp` adds "Rebirth in the Nightmare" to the Altar of
  Despair's talk script and drives the level-up screen from it.

## Tools

The `tools/` folder has small, independent scripts for the game's formats:
`bbparam.py` (params), `gparam.py` (draw params), `msb.py` (map layouts),
`luabnd.py` (AI script bundles), `shaderbnd.py` (shader bundles) and
`gfx_dump.py` (Scaleform menus). Each documents its options at the top of
the file. Scripts that read the game need `BBHOST_APP0` set to the folder
that contains `dvdroot_ps4`.

## Importing reviewed community patches

`tools/import_community_patches.py` converts selected entries from the community
Bloodborne XML to the manifest format. It does **not** import arbitrary patches
or obey the XML's `isEnabled` values. Every imported option starts off and
applies only after enabling it in the launcher's Patches tab and restarting.

```sh
python3 tools/import_community_patches.py --list
python3 tools/import_community_patches.py --xml /path/to/Bloodborne.xml \
  --eboot /path/to/decrypted/eboot.bin --output /path/to/new-import-directory \
  --patch performance-fast-rsqrt --patch intel-black-tonemap
```

Copy the generated TOML files into `<mods>/patches` (create that folder if
needed). The output directory must be new; existing patches are never overwritten.
The importer requires the exact supported 1.09 SHA-256, checks each selected
replacement against its reviewed address/byte list, and reads the original bytes
from executable ELF segments to populate `expect`. ELF addresses receive the
preferred 0x400000 base exactly once; XML addresses are already at that base.
The game executable and the XML are read only. No game data is shipped here.

| Option | Scope and tradeoff |
|---|---|
| `performance-fast-rsqrt` | Seven scalar reciprocal-square-root substitutions from Kyo's Performance Patch. Experimental: fewer refinement operations change numerical precision; visual/gameplay correctness and speedup require measurement. The rest of the bundle is excluded. |
| `intel-black-tonemap` | Kyo's black-tonemap workaround, reported for Intel CPUs in DLC areas. Test only when the symptom exists. |
| `intel-sfx-fallback` | emoose's early return in an effect draw routine. Removes ribbon effects of that type. Last resort only: bbhost already fixes the Windows red-zone issue in native ribbon writers (`src/decomp/sfx/ribbons.cpp`). |

The bundled Performance Patch also changes renderer settings, synchronization,
clock routines, physics, sleep intervals and code caves. In particular its
`0x025629f0` worker sleep overlaps frame-rate-controlled timing, and graphics
and LOD toggles already have live bbhost controls. Those edits, FPS/uncap lists,
resolution/light-grid lists and HTTP disabling are intentionally excluded.
Use PC Graphics/Effects and the native frame cap/resolution controls for those
settings. No generic XML-loader override is added.

Test one imported option at a time at the same resolution, frame cap and scene.
For tonemapping compare a DLC area; for the SFX fallback compare ribbon effects
and confirm whether the crash still occurs. For fast math compare frame times,
cloth, animation and gameplay at 30/60/high caps. These are optional experiments,
not a claim of compatibility or performance on every CPU. Disable the checkbox
and restart to restore the default. `BBHOST_PATCHES=0` is the emergency switch
for all manifests. Look for `patch: <name>` in the log to check whether a patch
was applied or refused; a checked box alone does not prove application.
