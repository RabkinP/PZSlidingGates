"""Deploy quality assets and native build-menu recipe variants; preserve high IDs."""
from pathlib import Path
import json
import re
import shutil

ROOT=Path(__file__).resolve().parents[1]
MEDIA=ROOT/'mod/SlidingGates/42/media'
lines=['module Base','{']
def block(kind,name,fields):
    lines.extend([f'    {kind} {name}','    {'])
    lines.extend(f'        {k} = {v},' for k,v in fields.items())
    lines.extend(['    }',''])
for width,prefix in ((2,'SG_ChainLink'),(4,'SG_ChainLink_4')):
    for quality in ('Low','Medium'):
        for reverse in (False,True):
            model=f'{prefix}_{quality}_N_'+('Reverse' if reverse else 'Right')
            shutil.copyfile(ROOT/'art/exports/quality'/f'{model}.glb', MEDIA/'models_X/IsoObject'/f'{model}.glb')
            block('animationsMesh',model,dict(meshFile='IsoObject/'+model,keepMeshAnimations='true'))
            block('model',model,dict(mesh='IsoObject/'+model,texture='IsoObject/SG_ChainLink_Atlas',
                  animationsMesh=model,shader='door',static='false',undoCoreScale='true'))
            tx=-.5 if reverse else .5
            for orientation,translate,rotate in [('N',f'{tx} 0 -0.38','0 0 0'),('W',f'-0.38 0 {-tx}','0 90 0')]:
                base=f'{prefix}_{quality}_{orientation}'+('_Reverse' if reverse else ('_Right' if orientation=='N' else ''))+'_G'
                for pose,time in [('Closed',0),('Open',width*1.5)]:
                    block('spriteModel',base+'_'+pose,dict(modelScript='Base.'+model,translate=translate,
                          rotate=rotate,scale='1',animation='Open',animationTime=f'{time:g}'))
lines.extend(['}',''])
(MEDIA/'scripts/SG_models_quality.txt').write_text('\n'.join(lines),encoding='utf-8')

# Use separate recipes and native OnAddToMenu, exactly as vanilla wooden walls.
source_path=MEDIA/'scripts/entity_sliding_gates.txt'
source=source_path.read_text(encoding='utf-8')
source=source.replace('SkillRequired = MetalWelding:5,','SkillRequired = MetalWelding:8,')
if 'OnAddToMenu = SGGateHighRecipeTest,' not in source:
    source=source.replace('            timedAction = BuildWireFence,',
                          '            OnAddToMenu = SGGateHighRecipeTest,\n            timedAction = BuildWireFence,')
source_path.write_text(source,encoding='utf-8')
def entity_block(name):
    match=re.search(r'    entity '+name+r'\s*\{',source)
    assert match,name
    start=match.start();end=match.end();depth=1
    while depth:
        if source[end]=='{':depth+=1
        if source[end]=='}':depth-=1
        end+=1
    return source[start:end]
entity_lines=['module Base','{','    xuiSkin default','    {']
for width in (2,4):
    for quality in ('Low','Medium'):
        name=f'SlidingGateChainLink{width}{quality}'
        entity_lines.extend([f'        entity ES_{name}','        {','            LuaWindowClass = ISEntityWindow,',
                             f'            DisplayName = {name},',f'            Icon = SG_BuildGate{width},','        }'])
entity_lines.extend(['    }',''])
for quality,offset in (('Low',48),('Medium',72)):
    for width in (2,4):
        name=f'SlidingGateChainLink{width}'
        template=entity_block(name).replace(name,name+quality)
        template=template.replace('MetalWelding:8','MetalWelding:'+('4' if quality=='Low' else '6'))
        template=template.replace('SGGateHighRecipeTest','SGGate'+quality+'RecipeTest')
        original=[0,1,6,7,24,25,30,31] if width==2 else [2,3,4,5,12,13,14,15,26,27,28,29,32,33,34,35]
        mapping={old:offset+(0 if width==2 else 8)+i for i,old in enumerate(original)}
        template=re.sub(r'sg_gates_preview_01_(\d+)',lambda m:'sg_gates_preview_01_'+str(mapping[int(m[1])]),template)
        entity_lines.extend([template,''])
entity_lines.extend(['}',''])
(MEDIA/'scripts/entity_sliding_gates_quality.txt').write_text('\n'.join(entity_lines),encoding='utf-8')

labels={
 'EN':('Low quality','Medium quality','High quality'),
 'RU':('Низкое качество','Среднее качество','Высокое качество'),
 'UA':('Низька якість','Середня якість','Висока якість'),
 'DE':('Niedrige Qualität','Mittlere Qualität','Hohe Qualität'),
 'FR':('Qualité faible','Qualité moyenne','Qualité élevée'),
 'ES':('Calidad baja','Calidad media','Calidad alta'),
 'IT':('Qualità bassa','Qualità media','Qualità alta'),
 'PT':('Qualidade baixa','Qualidade média','Qualidade alta'),
 'PL':('Niska jakość','Średnia jakość','Wysoka jakość'),
 'CS':('Nízká kvalita','Střední kvalita','Vysoká kvalita'),
 'NL':('Lage kwaliteit','Gemiddelde kwaliteit','Hoge kwaliteit'),
 'DA':('Lav kvalitet','Middel kvalitet','Høj kvalitet'),
 'NO':('Lav kvalitet','Middels kvalitet','Høy kvalitet'),
 'FI':('Heikko laatu','Keskitasoinen laatu','Korkea laatu'),
 'HU':('Alacsony minőség','Közepes minőség','Magas minőség'),
 'RO':('Calitate scăzută','Calitate medie','Calitate ridicată'),
 'TR':('Düşük kalite','Orta kalite','Yüksek kalite'),
 'ID':('Kualitas rendah','Kualitas sedang','Kualitas tinggi'),
 'AR':('جودة منخفضة','جودة متوسطة','جودة عالية'),
 'CA':('Qualitat baixa','Qualitat mitjana','Qualitat alta'),
 'CN':('低品质','中等品质','高品质'),
 'CH':('低品質','中等品質','高品質'),
 'JP':('低品質','中品質','高品質'),
 'KO':('낮은 품질','중간 품질','높은 품질'),
 'TH':('คุณภาพต่ำ','คุณภาพปานกลาง','คุณภาพสูง'),
}
for locale in ('ES_CL','ES_MX'):labels[locale]=labels['ES']
labels['PTBR']=labels['PT'];labels['STREW']=labels['EN']
for directory in (MEDIA/'lua/shared/Translate').iterdir():
    if not directory.is_dir():continue
    path=directory/'Recipes.json';data=json.loads(path.read_text(encoding='utf-8-sig'))
    low,medium,high=labels[directory.name]
    for width in (2,4):
        name=f'SlidingGateChainLink{width}'
        # Idempotent: strip only our own previously written high suffix.
        base=data[name]
        suffix=f' ({high})'
        if base.endswith(suffix):base=base[:-len(suffix)]
        data[name]=base+suffix
        data[name+'Low']=f'{base} ({low})'
        data[name+'Medium']=f'{base} ({medium})'
    path.write_text(json.dumps(data,ensure_ascii=False,indent=4)+'\n',encoding='utf-8')
print('Registered/deployed 8 quality GLBs, 32 poses, 4 recipes and 29 locales')
