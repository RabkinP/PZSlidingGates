"""Prepare generated icon originals for the installed B42 UI (Pillow).

The vanilla UI2.pack uses 32px item canvases and a 48px construction canvas.
Keep originals intact; ignore near-transparent fringe only when measuring bounds.
"""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'art/icons/generated'
OUTPUT = ROOT / 'mod/SlidingGates/42/media/textures'
PREVIEW = ROOT / 'art/icons/prepared'
ICONS = [
    ('electric-motor', 'Item_SG_ElectricMotor', 32),
    ('gate-drive', 'Item_SG_GateDrive', 32),
    ('gate-remote', 'Item_SG_GateRemote', 32),
    ('build-gate-2', 'SG_BuildGate2', 48),
    ('build-gate-4', 'SG_BuildGate4', 48),
]


def prepare(source, size):
    bounds = source.getchannel('A').point(lambda a: 255 if a >= 16 else 0).getbbox()
    if bounds is None:
        raise ValueError('Empty icon')
    crop = source.crop(bounds)
    # Premultiplied alpha resampling avoids dark/coloured fringes at small sizes.
    crop = crop.convert('RGBa')
    crop.thumbnail((size - 4, size - 4), Image.Resampling.LANCZOS)
    canvas = Image.new('RGBA', (size, size))
    canvas.paste(crop.convert('RGBA'), ((size-crop.width)//2, (size-crop.height)//2))
    return canvas


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    PREVIEW.mkdir(parents=True, exist_ok=True)
    sheet = Image.new('RGB', (760, 5*150), '#343434')
    draw = ImageDraw.Draw(sheet)
    for row, (name, texture, native_size) in enumerate(ICONS):
        source = Image.open(SOURCE / f'{name}.png').convert('RGBA')
        native = prepare(source, native_size)
        native.save(OUTPUT / f'{texture}.png', optimize=True)
        y = row*150
        draw.text((10, y+8), f'{name} / game {native_size}px', fill='white')
        for col, size in enumerate((32, 48, 64)):
            icon = prepare(source, size)
            icon.save(PREVIEW / f'{name}-{size}.png', optimize=True)
            x = 15 + col*245
            draw.text((x, y+30), f'{size}px actual / 2x', fill='white')
            for offset, background, scale in ((0, '#222222', 1), (80, '#dddddd', 2)):
                shown = icon.resize((size*scale, size*scale), Image.Resampling.NEAREST)
                tile = Image.new('RGBA', shown.size, background)
                tile.alpha_composite(shown)
                sheet.paste(tile.convert('RGB'), (x+offset, y+50))
        print(f'{texture}.png: {native_size}x{native_size}, {native.mode}')
    sheet.save(PREVIEW / 'contact-sheet.png')


if __name__ == '__main__':
    main()
