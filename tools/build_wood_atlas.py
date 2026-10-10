"""Opaque gameplay atlas from installed native timber grain and the Doorknob texture."""
from pathlib import Path
from PIL import Image, ImageEnhance, ImageDraw
import json

ROOT = Path(__file__).resolve().parents[1]
GAME = Path(r'E:\SteamLibrary\steamapps\common\ProjectZomboid')
OUT = ROOT/'art/SG_Wood_Atlas.png'
atlas = Image.new('RGB',(512,512))
source = Image.open(ROOT/'research/wood-references/walls_exterior_wooden_01_25.png').convert('RGB')
for sw,brightness in enumerate((1.0,1.13,.78,.92)):
    grain = source.crop((18+sw*3,65,30+sw*3,185)).resize((128,256),Image.Resampling.BICUBIC)
    grain = ImageEnhance.Brightness(grain).enhance(brightness)
    atlas.paste(grain,(sw*128,256))
for sw,color in ((4,(77,82,77)),(6,(25,29,26)),(7,(140,145,137))):
    tile = Image.new('RGB',(128,256),color)
    draw = ImageDraw.Draw(tile)
    for x in range(128):
        factor = .88+.12*(1-abs(x-64)/64)
        draw.line((x,0,x,255),fill=tuple(int(c*factor) for c in color))
    atlas.paste(tile,((sw%4)*128,0))
knob = Image.open(GAME/'media/textures/WorldItems/DoorKnob.png').convert('RGB')
atlas.paste(knob.resize((128,256),Image.Resampling.BILINEAR),(128,0))
atlas.save(OUT)
(ROOT/'art/wood_atlas_provenance.json').write_text(json.dumps({
    'timber':'Installed Tiles2x.pack: walls_exterior_wooden_01_25, interior grain crops; quality is geometry.',
    'doorknob':'Installed media/textures/WorldItems/DoorKnob.png; native FBX UV retained within atlas tile 5.',
    'opaque':True,'swatches':{'0':'wood','1':'light wood','2':'dark wood','3':'weathered wood','4':'steel','5':'native doorknob','6':'rubber','7':'fasteners'}
},indent=2)+'\n')
print(OUT)
