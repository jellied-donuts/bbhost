#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import struct
import tempfile
import tomllib
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('importer', ROOT / 'tools/import_community_patches.py')
imp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(imp)


def xml_for(key):
    root = ET.Element('Patch')
    name, _, sites = imp.CATALOG[key]
    md = ET.SubElement(root, 'Metadata', Name=name, AppVer='01.09', AppElf='eboot.bin', isEnabled='true')
    pl = ET.SubElement(md, 'PatchList')
    for address, value in sites.items():
        ET.SubElement(pl, 'Line', Type='bytes', Address=hex(address), Value=value.hex())
    return root


class ImportTest(unittest.TestCase):
    def test_generated_manifest_default_off_and_exact_originals(self):
        for key in imp.CATALOG:
            segments, data = [], bytearray()
            for address, value in imp.CATALOG[key][2].items():
                segments.append((address, len(data), len(value), 5))
                data.extend(b'\x55' * len(value))
            doc = tomllib.loads(imp.manifest(xml_for(key), key, bytes(data), segments))
            self.assertIs(doc['patch']['default_on'], False)
            self.assertEqual(doc['patch']['eboot'], imp.EBOOT_SHA256)
            for site in doc['site'].values():
                self.assertEqual(bytes.fromhex(site['expect']), b'\x55' * len(bytes.fromhex(site['bytes'])))

    def test_performance_bundle_excludes_unreviewed_sites(self):
        root = xml_for('performance-fast-rsqrt')
        ET.SubElement(root.find('.//PatchList'), 'Line', Type='bytes', Address='0x025629f0', Value='bf401f0000')
        self.assertNotIn(0x25629f0, imp.reviewed_sites(root, 'performance-fast-rsqrt'))

    def test_modified_missing_duplicate_wrong_version_sites_refused(self):
        for mutation in ('modified', 'missing', 'duplicate', 'version', 'elf', 'type'):
            root = xml_for('intel-black-tonemap')
            md, pl, line = root.find('Metadata'), root.find('.//PatchList'), root.find('.//Line')
            if mutation == 'modified': line.set('Value', 'c3')
            if mutation == 'missing': pl.remove(line)
            if mutation == 'duplicate': ET.SubElement(pl, 'Line', **line.attrib)
            if mutation == 'version': md.set('AppVer', '01.00')
            if mutation == 'elf': md.set('AppElf', 'other.bin')
            if mutation == 'type': line.set('Type', 'bytes32')
            with self.assertRaises(ValueError, msg=mutation):
                imp.reviewed_sites(root, 'intel-black-tonemap')

    def test_hash_mismatch_refused(self):
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            imp.load_elf(b'not the game')

    def test_elf_translation_uses_preferred_base_once(self):
        data = bytearray(128)
        data[:6] = b'\x7fELF\x02\x01'
        struct.pack_into('<H', data, 18, 62)
        struct.pack_into('<Q', data, 32, 64)
        struct.pack_into('<HH', data, 54, 56, 1)
        struct.pack_into('<IIQQQQQQ', data, 64, 1, 5, 120, 0x1234, 0, 8, 8, 1)
        data[120:] = b'abcdefgh'
        segs = imp.elf_segments(data)
        self.assertEqual(imp.original_bytes(data, segs, 0x401236, 3), b'cde')
        for address, size in ((0x1234, 1), (0x40123b, 2)):
            with self.assertRaises(ValueError): imp.original_bytes(data, segs, address, size)
        with self.assertRaises(ValueError): imp.original_bytes(data, segs + segs, 0x401234, 1)
        with self.assertRaises(ValueError): imp.original_bytes(data, [(0x401234, 120, 8, 6)], 0x401234, 1)

    def test_truncated_or_invalid_elf_refused(self):
        for data in (b'', b'\x7fELF\x02\x01' + b'\0' * 58):
            with self.assertRaises(ValueError): imp.elf_segments(data)

    def test_already_patched_refused(self):
        key = 'intel-sfx-fallback'
        with self.assertRaisesRegex(ValueError, 'already patched'):
            imp.manifest(xml_for(key), key, b'\xc3', [(0x2cf83e0, 0, 1, 5)])

    def test_import_sites_disjoint_from_shipped_manifests_and_fps_sites(self):
        ranges = []
        for path in (ROOT / 'patches').glob('*.toml'):
            for site in tomllib.loads(path.read_text())['site'].values():
                a = int(site['address'], 16)
                ranges.append((a, a + len(bytes.fromhex(site['bytes']))))
        import re
        for path in (ROOT / 'src/engine').glob('*fps_sites.inc'):
            for a, old in re.findall(r'\{(0x[0-9a-fA-F]+),\s*"([0-9a-fA-F ]+)"', path.read_text()):
                address = int(a, 16)
                ranges.append((address, address + len(bytes.fromhex(old))))
        self.assertTrue(ranges)
        for _, _, sites in imp.CATALOG.values():
            for a, value in sites.items():
                self.assertFalse(any(a < end and start < a + len(value) for start, end in ranges), hex(a))


if __name__ == '__main__':
    unittest.main()
