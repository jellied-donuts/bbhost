#!/usr/bin/env python3
"""Import reviewed 1.09 XML sites as opt-in, byte-checked bbhost manifests.

No arbitrary XML import: timing, resolution and live graphics remain bbhost's.
Original bytes are read from the player's exact decrypted ELF, never guessed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

EBOOT_SHA256 = '941f887a562aae054fac35af8cc8f27cf075f3d4cc2e029fb5ae2a663aaa5ae7'
PREFERRED_BASE = 0x400000

# XML VA and replacement bytes. A changed list must be reviewed, not trusted.
# The performance bundle also edits sleep intervals already owned by frame_rate.cpp,
# renderer defaults, code caves, physics and synchronization. Only its seven
# scalar reciprocal-square-root substitutions are offered here, experimentally.
RSQRT = {
    0x00BB82C1: 'c5fa52c9', 0x00BB838A: 'c5fa52d2',
    0x00BB86D1: 'c5fa52c9', 0x00BB8796: 'c5fa52e4',
    0x02617069: 'c5fa52e4', 0x02617147: 'c5fa52e4',
    0x026172E9: 'c5fa52e4',
}
CATALOG = {
    'performance-fast-rsqrt': (
        'Performance Patch (perf increase)',
        'Kyo: experimental fast scalar reciprocal square roots only; changes numerical '
        'precision. No timing, resolution, physics, waits or renderer-default edits. '
        'Performance and visual correctness need testing on your machine.',
        {a: bytes.fromhex(v + '90' * 12) for a, v in RSQRT.items()},
    ),
    'intel-black-tonemap': (
        'Intel Black Tonemap Fix',
        'Kyo: experimental Intel black tonemap workaround, most noticeable in DLC areas. '
        'Enable only if you see black tonemapping; no performance benefit is promised.',
        {0x025843E5: bytes.fromhex('90' * 6)},
    ),
    'intel-sfx-fallback': (
        'Intel 12th Gen+ SFX workaround',
        'emoose: last-resort SFX workaround; disables an effect draw routine and removes '
        'ribbon effects of that type. bbhost already fixes the Windows red-zone crash '
        'in its native ribbon writers. Leave off unless diagnosing a remaining crash.',
        {0x02CF83E0: b'\xc3'},
    ),
}


def load_elf(data):
    if hashlib.sha256(data).hexdigest() != EBOOT_SHA256:
        raise ValueError('eboot SHA-256 is not the supported decrypted Bloodborne 1.09 build')
    return elf_segments(data)


def elf_segments(data):
    if len(data) < 64 or data[:6] != b'\x7fELF\x02\x01':
        raise ValueError('expected a decrypted ELF64 little-endian executable')
    if struct.unpack_from('<H', data, 18)[0] != 62:
        raise ValueError('expected an x86-64 ELF')
    phoff = struct.unpack_from('<Q', data, 32)[0]
    entsize, count = struct.unpack_from('<HH', data, 54)
    if entsize != 56 or phoff + count * entsize > len(data):
        raise ValueError('invalid ELF program headers')
    segments = []
    for i in range(count):
        ty, flags, off, va, _, size, memsize, _ = struct.unpack_from('<IIQQQQQQ', data, phoff + i * entsize)
        if ty != 1:
            continue
        if size > memsize or off + size > len(data):
            raise ValueError('invalid ELF load segment')
        segments.append((va + PREFERRED_BASE, off, size, flags))
    return segments


def original_bytes(data, segments, address, size):
    matches = [(va, off) for va, off, fs, flags in segments
               if flags & 1 and va <= address and address + size <= va + fs]
    if len(matches) != 1:
        raise ValueError(f'0x{address:x} is not uniquely inside file-backed executable memory')
    va, off = matches[0]
    start = off + address - va
    return data[start:start + size]


def reviewed_sites(root, key):
    name, _, allowed = CATALOG[key]
    matches = [m for m in root.iter('Metadata') if m.get('Name') == name
               and m.get('AppVer') == '01.09' and m.get('AppElf') == 'eboot.bin']
    if len(matches) != 1:
        raise ValueError(f'expected exactly one 1.09 eboot entry for {name}')
    found = {}
    patch = matches[0].find('PatchList')
    if patch is None:
        raise ValueError(f'missing PatchList for {name}')
    for line in patch:
        address = int(line.get('Address', ''), 16)
        if address not in allowed:
            continue  # Unreviewed parts of the Performance bundle never become sites.
        if address in found:
            raise ValueError(f'duplicate reviewed site 0x{address:x}')
        if line.get('Type') != 'bytes':
            raise ValueError(f'unsupported type at 0x{address:x}')
        value = bytes.fromhex(line.get('Value', ''))
        if value != allowed[address]:
            raise ValueError(f'XML differs from reviewed replacement at 0x{address:x}')
        found[address] = value
    if found != allowed:
        raise ValueError(f'missing reviewed sites for {name}')
    return found


def manifest(root, key, data, segments):
    sites = reviewed_sites(root, key)
    lines = ['# Imported reviewed XML sites; game files are never modified.',
             '[patch]', f'name = {json.dumps(key)}', f'eboot = "{EBOOT_SHA256}"',
             f'description = {json.dumps(CATALOG[key][1])}', 'default_on = false']
    for address, replacement in sorted(sites.items()):
        original = original_bytes(data, segments, address, len(replacement))
        if original == replacement:
            raise ValueError(f'0x{address:x} is already patched')
        lines += ['', f'[site.at-{address:08x}]', f'address = "0x{address:08x}"',
                  f'expect = "{original.hex(" ")}"', f'bytes = "{replacement.hex(" ")}"',
                  'kind = "code"']
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', action='store_true', help='show the reviewed choices without a game executable')
    parser.add_argument('--xml', type=Path)
    parser.add_argument('--eboot', type=Path)
    parser.add_argument('--output', type=Path, help='NEW directory for generated manifests (does not overwrite files)')
    parser.add_argument('--patch', action='append', choices=CATALOG, help='repeat to select more than one; no implicit imports')
    args = parser.parse_args()
    if args.list:
        for key, (_, description, _) in CATALOG.items():
            print(f'{key} (off by default): {description}')
        return
    if not all((args.xml, args.eboot, args.output, args.patch)):
        parser.error('--xml, --eboot, --output and at least one --patch are required')
    try:
        data = args.eboot.read_bytes()
        segments = load_elf(data)
        root = ET.parse(args.xml).getroot()
        # Validate every selected patch before creating any output.
        outputs = {key: manifest(root, key, data, segments) for key in args.patch}
        args.output.mkdir(parents=True, exist_ok=False)
        for key, text in outputs.items():
            (args.output / f'{key}.toml').write_text(text, encoding='utf-8')
    except (OSError, ValueError, ET.ParseError) as exc:
        parser.exit(1, f'import refused: {exc}\n')
    print(f'Created {len(outputs)} opt-in manifests in {args.output}. Copy them to <mods>/patches, '
          'then enable individual entries in the launcher Patches tab and restart.')


if __name__ == '__main__':
    main()
