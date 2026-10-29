"""Small, dependency-free helpers for the public website's local assets."""
from pathlib import Path
import re
import struct
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.avif', '.svg'}


def image_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if path.suffix == '.svg':
        svg = ET.fromstring(data)
        if 'viewBox' in svg.attrib:
            box = re.split(r'[ ,]+', svg.attrib['viewBox'].strip())
            return round(float(box[2])), round(float(box[3]))
        return int(svg.attrib['width']), int(svg.attrib['height'])
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return struct.unpack('>II', data[16:24])
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        kind = data[12:16]
        if kind == b'VP8X':
            return 1 + int.from_bytes(data[24:27], 'little'), 1 + int.from_bytes(data[27:30], 'little')
        if kind == b'VP8L':
            bits = int.from_bytes(data[21:25], 'little')
            return (bits & 0x3fff) + 1, ((bits >> 14) & 0x3fff) + 1
        if kind == b'VP8 ':
            start = data.index(b'\x9d\x01\x2a') + 3
            width, height = struct.unpack('<HH', data[start:start + 4])
            return width & 0x3fff, height & 0x3fff
    if data.startswith(b'\xff\xd8'):
        offset = 2
        while offset < len(data):
            if data[offset] != 0xff:
                offset += 1
                continue
            while data[offset] == 0xff:
                offset += 1
            marker = data[offset]
            offset += 1
            if marker in {0x01, *range(0xd0, 0xda)}:
                continue
            length = int.from_bytes(data[offset:offset + 2], 'big')
            if marker in {0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf}:
                height, width = struct.unpack('>HH', data[offset + 3:offset + 7])
                return width, height
            offset += length
    if path.suffix == '.avif':
        offset = data.index(b'ispe') + 8
        return struct.unpack('>II', data[offset:offset + 8])
    raise ValueError(f'Unsupported image: {path.relative_to(ROOT)}')
