#!/usr/bin/env python3
"""Rasterizes Lucide SVG icons into 1-bit Adafruit_GFX::drawBitmap() arrays.

Mirrors the approach crosspoint-reader uses (stock Lucide SVGs -> packed
1bpp bitmaps), adapted to plain ImageMagick since we don't have their
freeink-sdk gen_icons.py tool available.
"""
import pathlib
import subprocess

SIZE = 20  # bitmap width/height in px, for menu/row icons
SIZE_SMALL = 12  # for chrome-scale icons (header status), too tight for HEADER_H otherwise

# Identifiers (from ICONS below) also rendered at SIZE_SMALL, as "<ident>_sm".
SMALL_VARIANTS = {"moon", "zap"}

# (C identifier, Lucide icon name, SVG child elements)
ICONS = [
    ("lightbulb", "lightbulb", [
        ('path', {'d': 'M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5'}),
        ('path', {'d': 'M9 18h6'}),
        ('path', {'d': 'M10 22h4'}),
    ]),
    ("toggle_right", "toggle-right", [
        ('circle', {'cx': '15', 'cy': '12', 'r': '3'}),
        ('rect', {'width': '20', 'height': '14', 'x': '2', 'y': '5', 'rx': '7'}),
    ]),
    ("moon", "moon", [
        ('path', {'d': 'M20.985 12.486a9 9 0 1 1-9.473-9.472c.405-.022.617.46.402.803a6 6 0 0 0 8.268 8.268c.344-.215.825-.004.803.401'}),
    ]),
    ("zap", "zap", [
        ('path', {'d': 'M15.914 4a1.5 1.5 0 00-2.474-1.561l-9 9A1.5 1.5 0 005.5 14h4.002a.5.5 0 01.471.666L8.086 20a1.5 1.5 0 002.475 1.56l9-9A1.5 1.5 0 0018.5 10h-3.997a.5.5 0 01-.472-.667z'}),
    ]),
    ("lock", "lock", [
        ('rect', {'width': '18', 'height': '11', 'x': '3', 'y': '11', 'rx': '2', 'ry': '2'}),
        ('path', {'d': 'M7 11V7a5 5 0 0 1 10 0v4'}),
    ]),
    ("fan", "fan", [
        ('path', {'d': 'M10.827 16.379a6.082 6.082 0 0 1-8.618-7.002l5.412 1.45a6.082 6.082 0 0 1 7.002-8.618l-1.45 5.412a6.082 6.082 0 0 1 8.618 7.002l-5.412-1.45a6.082 6.082 0 0 1-7.002 8.618l1.45-5.412Z'}),
        ('path', {'d': 'M12 12v.01'}),
    ]),
    ("thermometer", "thermometer", [
        ('path', {'d': 'M14 4v10.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z'}),
    ]),
    ("tv", "tv", [
        ('path', {'d': 'm17 2-5 5-5-5'}),
        ('rect', {'width': '20', 'height': '15', 'x': '2', 'y': '7', 'rx': '2'}),
    ]),
    ("wifi", "wifi", [
        ('path', {'d': 'M12 20h.01'}),
        ('path', {'d': 'M2 8.82a15 15 0 0 1 20 0'}),
        ('path', {'d': 'M5 12.859a10 10 0 0 1 14 0'}),
        ('path', {'d': 'M8.5 16.429a5 5 0 0 1 7 0'}),
    ]),
]


def svg_for(elements):
    parts = []
    for tag, attrs in elements:
        attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
        parts.append(f'<{tag} {attr_str}/>')
    body = ''.join(parts)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
        'viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2.5" '
        f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )


def rasterize(svg_text, size):
    p1 = subprocess.run(
        ['magick', 'svg:-', '-background', 'white', '-flatten',
         '-resize', f'{size}x{size}', '-threshold', '50%', '-depth', '8', 'gray:-'],
        input=svg_text.encode(), capture_output=True, check=True,
    )
    data = p1.stdout
    assert len(data) == size * size, f'expected {size*size} bytes, got {len(data)}'
    return data


def pack_bits(gray, size):
    row_bytes = (size + 7) // 8
    out = bytearray(row_bytes * size)
    for y in range(size):
        for x in range(size):
            on = gray[y * size + x] < 128
            if on:
                out[y * row_bytes + x // 8] |= 0x80 >> (x % 8)
    return bytes(out), row_bytes


def main():
    header = []
    header.append('#pragma once')
    header.append('#include <cstdint>')
    header.append('')
    header.append('// 1-bit icon bitmaps, generated from stock Lucide SVGs (same source')
    header.append('// crosspoint-reader uses) via scripts/gen_icons.py — rasterized at')
    header.append(f'// {SIZE}x{SIZE}px and packed for Adafruit_GFX::drawBitmap(). Regenerate with')
    header.append('// that script if the icon set changes; do not hand-edit the byte arrays.')
    header.append('namespace IconBitmaps {')
    header.append('')
    header.append(f'constexpr int ICON_SIZE = {SIZE};')
    header.append(f'constexpr int ICON_SIZE_SMALL = {SIZE_SMALL};')
    header.append('')

    def emit(ident, lucide_name, gray, size, row_bytes):
        packed, _ = pack_bits(gray, size)
        header.append(f'// lucide: {lucide_name}')
        header.append(f'constexpr uint8_t {ident}[{len(packed)}] = {{')
        for i in range(0, len(packed), row_bytes):
            row = packed[i:i + row_bytes]
            hexes = ', '.join(f'0x{b:02x}' for b in row)
            header.append(f'    {hexes},')
        header.append('};')
        header.append('')

    names = []
    for ident, lucide_name, elements in ICONS:
        svg = svg_for(elements)
        names.append((ident, lucide_name))

        gray = rasterize(svg, SIZE)
        emit(ident, lucide_name, gray, SIZE, (SIZE + 7) // 8)

        if ident in SMALL_VARIANTS:
            gray_sm = rasterize(svg, SIZE_SMALL)
            emit(f'{ident}_sm', lucide_name, gray_sm, SIZE_SMALL, (SIZE_SMALL + 7) // 8)

    header.append('}  // namespace IconBitmaps')
    header.append('')

    out_path = pathlib.Path(__file__).resolve().parent.parent / 'src/components/icons/IconBitmaps.h'
    out_path.write_text('\n'.join(header))

    print(f'Wrote {out_path} with {len(names)} icons:', ', '.join(n for n, _ in names))


if __name__ == '__main__':
    main()
