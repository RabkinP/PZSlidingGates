"""Build the construction-only carrier pack using the installed B42 binary formats.

No TileZed dependency. Pillow is only used to encode the transparent PNG atlas.
Tile indices and file number are save-format identifiers: never renumber/reuse them.
See skills/pz-models/references/engine-render-audit.md for format evidence.
"""
from io import BytesIO
from pathlib import Path
import json
import struct
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / 'mod/SlidingGates'
MEDIA = MOD / '42/media'
TILESET = 'sg_gates_preview_01'
FILE_NUMBER = 6842
COUNT = 24  # append W statics; preserve all existing indices


def integer(n):
    return struct.pack('<i', n)


def pack_string(s):
    raw = s.encode('ascii')
    return integer(len(raw)) + raw


def bindings():
    hidden = dict(modelScript='Base.SG_Rail', translate='0 0 0',
                  rotate='0 0 0', scale='0.001')
    result = [dict(hidden) for _ in range(COUNT)]
    for index, prefix in ((1, 'SG_ChainLink'), (5, 'SG_ChainLink_4')):
        result[index] = dict(modelScript=f'Base.{prefix}_N_Right',
                             translate='0.5 0 -0.38', rotate='0 0 0', scale='1',
                             animation='Open', animationTime='0')
    for index, name, offset in ((8, 'CatcherPost', '-0.46 0 -0.38'),
                                 (9, 'GuidePost', '-0.54 0 -0.38'),
                                 (10, 'Rail', '-0.5 0 -0.38'),
                                 (11, 'Drive', '-0.5 0 -0.6')):
        result[index] = dict(modelScript=f'Base.SG_{name}', translate=offset,
                             rotate='0 0 0', scale='1')
    for index, prefix in ((6, 'SG_ChainLink'), (12, 'SG_ChainLink_4')):
        result[index] = dict(modelScript=f'Base.{prefix}_N_Right',
                             translate='-0.38 0 -0.5', rotate='0 90 0', scale='1',
                             animation='Open', animationTime='0')
    for index, name, offset in ((16, 'CatcherPost', '-0.38 0 0.46'),
                                 (17, 'GuidePost', '-0.38 0 0.54'),
                                 (18, 'Rail', '-0.38 0 0.5'),
                                 (19, 'Drive', '-0.6 0 0.5')):
        result[index] = dict(modelScript=f'Base.SG_{name}', translate=offset,
                             rotate='0 90 0', scale='1')
    return result


def build():
    atlas = Image.new('RGBA', (1024, 768), (0, 0, 0, 0))
    # Explicit untrimmed subtextures keep completely transparent carriers valid.
    png = BytesIO()
    atlas.save(png, format='PNG')
    payload = png.getvalue()
    pack = b'PZPK' + integer(1) + integer(1)
    pack += pack_string('SG_GatesPreview_0') + integer(COUNT) + integer(1)
    for index in range(COUNT):
        pack += pack_string(f'{TILESET}_{index}')
        pack += b''.join(integer(n) for n in
                         ((index % 8) * 128, (index // 8) * 256,
                          128, 256, 0, 0, 128, 256))
    pack += integer(len(payload)) + payload
    textures = MEDIA / 'texturepacks'
    textures.mkdir(parents=True, exist_ok=True)
    (textures / 'SG_GatesPreview.pack').write_bytes(pack)

    # tdef v1: little-endian integers, LF-terminated ASCII strings (NOT CRLF).
    tiles = b'tdef' + integer(1) + integer(1)
    tiles += (TILESET + '\n' + TILESET + '.png\n').encode('ascii')
    tiles += b''.join(integer(n) for n in (8, 3, 1, COUNT))
    # Construction carriers have no collision, door, floor or physics properties.
    tiles += integer(0) * COUNT
    (MEDIA / 'SG_GatesPreview.tiles').write_bytes(tiles)

    common = MOD / 'common/media'
    common.mkdir(parents=True, exist_ok=True)
    lines = ['spriteModel', '{', '    VERSION = 1,', '    tileset', '    {',
             f'        name = {TILESET},']
    for index, fields in enumerate(bindings()):
        lines += ['        tile', '        {', f'            xy = {index % 8} {index // 8},']
        lines += [f'            {key} = {value},' for key, value in fields.items()]
        lines += ['        }']
    lines += ['    }', '}', '']
    (common / 'spriteModels.txt').write_text('\n'.join(lines), encoding='utf-8')

    source = ROOT / 'art/tiles'
    source.mkdir(parents=True, exist_ok=True)
    atlas.save(source / f'{TILESET}.png')
    manifest = dict(tileset=TILESET, file_number=FILE_NUMBER, tileset_number=1,
                    tile_size=[128, 256], construction_only=True,
                    indices={str(i): fields for i, fields in enumerate(bindings())})
    (source / 'gate_tiles.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Built {COUNT} carriers: .pack/.tiles and common/media/spriteModels.txt')


if __name__ == '__main__':
    build()
