"""Read installed PZPK v1 atlases for local Blender poster reference materials."""
from pathlib import Path
from io import BytesIO
import struct, json
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
GAME=Path(r'E:\SteamLibrary\steamapps\common\ProjectZomboid')
OUT=ROOT/'art/poster/game_textures'
OUT.mkdir(parents=True,exist_ok=True)

def integer(f):return struct.unpack('<i',f.read(4))[0]
def string(f):return f.read(integer(f)).decode('utf-8')
manifest=[]
names=[]
for filename in ('Tiles2x.pack','Tiles2x.floor.pack'):
    with (GAME/'media/texturepacks'/filename).open('rb') as f:
        assert f.read(4)==b'PZPK' and integer(f)==1
        pages=integer(f)
        for i in range(pages):
            page=string(f);count=integer(f);alpha=integer(f)
            entries=[]
            for j in range(count):
                name=string(f);bounds=struct.unpack('<8i',f.read(32))
                names.append(name);entries.append((name,bounds))
            length=integer(f)
            selected=[(n,b) for n,b in entries if n.startswith(('fencing_01_','carpentry_02_','blends_street_01_','street_01_','floors_exterior_street_01_','d_streetcracks_1_','street_decoration_01_','vegetation_ornamental_01_','blends_natural_01_'))]
            if not selected:f.seek(length,1);continue
            atlas=Image.open(BytesIO(f.read(length))).convert('RGBA')
            for name,b in selected:
                x,y,w,h,ox,oy,ow,oh=b
                tile=atlas.crop((x,y,x+w,y+h))
                tile.save(OUT/(name+'.png'))
                manifest.append(dict(name=name,pack=filename,page=page,bounds=list(b)))
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
(OUT/'texture_names.txt').write_text('\n'.join(names))
for prefix in sorted({r['name'].rsplit('_',1)[0] for r in manifest}):
    tiles=[r for r in manifest if r['name'].startswith(prefix+'_')]
    tiles.sort(key=lambda r:int(r['name'].rsplit('_',1)[1]))
    thumb_w,thumb_h=160,240
    sheet=Image.new('RGB',(thumb_w*8,thumb_h*((len(tiles)+7)//8)),(90,92,88))
    draw=ImageDraw.Draw(sheet)
    for i,row in enumerate(tiles):
        tile=Image.open(OUT/(row['name']+'.png'));tile.thumbnail((144,205))
        x=(i%8)*thumb_w;y=(i//8)*thumb_h
        sheet.paste(tile,(x+(thumb_w-tile.width)//2,y+22),tile)
        draw.text((x+4,y+4),row['name'].rsplit('_',1)[1],fill='white')
    sheet.save(OUT/(prefix+'_contact.jpg'))
print('EXTRACTED',len(manifest),'tiles, total atlas entries',len(names))
print('FENCE SETS',sorted({n.rsplit('_',1)[0] for n in names if 'fenc' in n}))
print('ROAD SETS',sorted({n.rsplit('_',1)[0] for n in names if any(k in n for k in ('street','asphalt'))}))
