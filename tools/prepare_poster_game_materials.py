"""Undo isometric projection for Blender materials, using installed game tiles."""
from pathlib import Path
import json, random
from PIL import Image, ImageOps, ImageEnhance, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'art/poster/game_textures'
OUT=RAW/'prepared';OUT.mkdir(exist_ok=True)
rows={r['name']:r for r in json.loads((RAW/'manifest.json').read_text())}

def full(name):
    x,y,w,h,ox,oy,ow,oh=rows[name]['bounds']
    canvas=Image.new('RGBA',(ow,oh))
    canvas.paste(Image.open(RAW/(name+'.png')),(ox,oy))
    return canvas

def floor(name,opaque=False):
    # The game's ground diamond occupies the final 64 rows of a 128x256 cell.
    tile=full(name).crop((0,192,128,256))
    flat=tile.transform((128,128),Image.Transform.AFFINE,
        (62/128,-62/128,64,30/128,30/128,2),Image.Resampling.BICUBIC)
    if opaque:
        bg=Image.new('RGBA',flat.size,(92,92,92,255));bg.alpha_composite(flat);flat=bg
    return flat

wood=Image.open(RAW/'fencing_01_8.png').convert('RGBA')
wood=wood.transform((128,384),Image.Transform.AFFINE,
    (57/128,0,4,.60*57/128,169/384,6),Image.Resampling.BICUBIC)
wood.save(OUT/'wood_face.png')
for i in range(7):
    # Grain between the sprite's horizontal backing rails; different native boards.
    x=22+i*12
    strip=wood.crop((x,125,x+12,250)).resize((64,512),Image.Resampling.BICUBIC)
    strip=ImageEnhance.Color(strip).enhance(.8)
    strip.save(OUT/f'wood_board_{i}.png')

asphalt=floor('floors_exterior_street_01_17',True).crop((8,8,120,120)).resize((128,128),Image.Resampling.BICUBIC)
mosaic=Image.new('RGBA',(512,512));rnd=random.Random(93)
for y in range(4):
    for x in range(4):
        # Mirror adjoining edges: no baked diamond boundary or square color seams.
        tile=asphalt.copy()
        if x%2:tile=ImageOps.mirror(tile)
        if y%2:tile=ImageOps.flip(tile)
        mosaic.paste(tile,(x*128,y*128))
mosaic.save(OUT/'asphalt.png')
floor('blends_natural_01_64',True).save(OUT/'grass.png')
for i in range(24): floor(f'd_streetcracks_1_{i}').save(OUT/f'crack_{i}.png')
(OUT/'provenance.json').write_text(json.dumps(dict(
    wood='fencing_01_8',asphalt='floors_exterior_street_01_17',
    grass='blends_natural_01_64',cracks='d_streetcracks_1_0..23',
    purpose='Local poster Blender materials; not added to gameplay mod files.',
    transform='Affine inverse isometric projection and native board grain crops.'),indent=2))
print('PREPARED',OUT)
