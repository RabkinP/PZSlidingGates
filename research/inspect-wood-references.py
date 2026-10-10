"""Extract installed vanilla wooden wall and door references without editing game assets."""
from pathlib import Path
from io import BytesIO
import struct
import json
from PIL import Image, ImageDraw

GAME = Path(r'E:\SteamLibrary\steamapps\common\ProjectZomboid')
OUT = Path(__file__).resolve().parent / 'wood-references'
OUT.mkdir(exist_ok=True)
names = {f'walls_exterior_wooden_01_{i}' for i in (24,25,40,41,44,45)}
names |= {f'fixtures_doors_fences_01_{i}' for i in (4,5,96,97,104,105)}
names |= {f'carpentry_01_{i}' for i in (48,49,52,53,56,57)}
names |= {'Item_DoorKnob', 'Item_Doorknob'}
manifest = []

def integer(f):
    return struct.unpack('<i', f.read(4))[0]

def string(f):
    return f.read(integer(f)).decode('utf-8')

for filename in ('Tiles2x.pack', 'UI.pack', 'UI2.pack', 'ApCom.pack'):
    with (GAME / 'media/texturepacks' / filename).open('rb') as f:
        magic = f.read(4)
        modern = magic == b'PZPK'
        if modern:
            assert integer(f) == 1
            pages = integer(f)
        else:
            pages = struct.unpack('<i', magic)[0]
        for _ in range(pages):
            page = string(f)
            count, alpha = integer(f), integer(f)
            entries = [(string(f), struct.unpack('<8i', f.read(32))) for _ in range(count)]
            selected = [(n,b) for n,b in entries if n in names]
            if modern:
                length = integer(f)
                if selected:
                    data = f.read(length)
                else:
                    f.seek(length,1)
            else:
                start = f.tell()
                assert f.read(8) == b'\x89PNG\r\n\x1a\n'
                while True:
                    length = struct.unpack('>I', f.read(4))[0]
                    chunk = f.read(4)
                    f.seek(length + 4,1)
                    if chunk == b'IEND':
                        break
                end = f.tell()
                if selected:
                    f.seek(start)
                    data = f.read(end-start)
                sentinel = integer(f)
                assert sentinel == -559038737, hex(sentinel & 0xffffffff)
            if not selected:
                continue
            atlas = Image.open(BytesIO(data)).convert('RGBA')
            for n,b in selected:
                x,y,w,h,ox,oy,ow,oh = b
                atlas.crop((x,y,x+w,y+h)).save(OUT / (n+'.png'))
                manifest.append({'name':n,'pack':filename,'page':page,'bounds':b})

(OUT / 'manifest.json').write_text(json.dumps(manifest,indent=2))
groups = [('Low (2-3)',44,45), ('Medium (4-5)',40,41), ('High (6+)',24,25)]
sheet = Image.new('RGB',(900,360),(65,69,66))
draw = ImageDraw.Draw(sheet)
for col,(label,*indices) in enumerate(groups):
    draw.text((col*300+15,15),label,fill='white')
    for j,index in enumerate(indices):
        n = f'walls_exterior_wooden_01_{index}'
        tile = Image.open(OUT/(n+'.png'))
        sheet.paste(tile,(col*300+j*140+10,55),tile)
        draw.text((col*300+j*140+10,325),n.rsplit('_',1)[-1],fill='white')
sheet.save(OUT/'wall-quality.png')
icon = OUT/'Item_DoorKnob.png'
if icon.exists():
    tile = Image.open(icon)
    tile = tile.resize((tile.width*6,tile.height*6),Image.Resampling.NEAREST)
    tile.save(OUT/'doorknob-enlarged.png')
print('Extracted',len(manifest),'references:', ', '.join(r['name'] for r in manifest))
