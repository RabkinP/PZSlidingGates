"""Deploy wood assets, recipes and spriteModels using the established anchors."""
from pathlib import Path
import re
import json
import shutil

ROOT=Path(__file__).resolve().parents[1];MEDIA=ROOT/'mod/SlidingGates/42/media'
lines=['module Base','{']
def block(kind,name,fields):
    lines.extend([f'    {kind} {name}','    {'])
    lines.extend(f'        {k} = {v},' for k,v in fields.items())
    lines.extend(['    }',''])

for width,prefix in ((2,'SG_Wood'),(4,'SG_Wood_4')):
    for quality in ('','Low','Medium'):
        for reverse in (False,True):
            for damage in range(4):
                stem=prefix+('_'+quality if quality else '')
                model=stem+'_N_'+('Reverse' if reverse else 'Right')+(f'_Damage{damage}' if damage else '')
                shutil.copyfile(ROOT/'art/exports/wood'/f'{model}.glb',MEDIA/'models_X/IsoObject'/f'{model}.glb')
                block('animationsMesh',model,dict(meshFile='IsoObject/'+model,keepMeshAnimations='true'))
                block('model',model,dict(mesh='IsoObject/'+model,texture='IsoObject/SG_Wood_Atlas',
                    animationsMesh=model,shader='door',static='false',undoCoreScale='true'))
                tx=-.5 if reverse else .5
                for orientation,translate,rotate in [('N',f'{tx} 0 -0.38','0 0 0'),('W',f'-0.38 0 {-tx}','0 90 0')]:
                    base=stem+'_'+orientation+('_Reverse' if reverse else ('_Right' if orientation=='N' else ''))+'_G'
                    if damage:base+=f'_Damage{damage}'
                    for pose,time in [('Closed',0),('Open',width*1.5)]:
                        block('spriteModel',base+'_'+pose,dict(modelScript='Base.'+model,translate=translate,
                            rotate=rotate,scale='1',animation='Open',animationTime=f'{time:g}'))
sources='\n'.join((MEDIA/'scripts'/name).read_text() for name in ('SG_models.txt','SG_models_reverse.txt'))
for name in ('CatcherPost','GuidePost','Rail','Drive'):
    for reverse in (False,True):
        old='SG_'+name+('_Reverse' if reverse else '');new=old.replace('SG_','SG_Wood_',1)
        shutil.copyfile(ROOT/'art/exports/wood'/f'{new}.glb',MEDIA/'models_X/IsoObject'/f'{new}.glb')
        body=re.search(r'\bmodel\s+'+old+r'\s*\{([^}]+)\}',sources)[1]
        fields=dict(re.findall(r'(\w+)\s*=\s*([^,]+),',body))
        fields={k:v.strip().replace(old,new).replace('SG_ChainLink_Atlas','SG_Wood_Atlas') for k,v in fields.items()}
        block('model',new,fields)
        for suffix in ('_Static','_W_Static'):
            body=re.search(r'\bspriteModel\s+'+old+suffix+r'\s*\{([^}]+)\}',sources)[1]
            fields={k:v.strip().replace(old,new) for k,v in re.findall(r'(\w+)\s*=\s*([^,]+),',body)}
            block('spriteModel',new+suffix,fields)
lines.extend(['}','']);(MEDIA/'scripts/SG_models_wood.txt').write_text('\n'.join(lines),encoding='utf-8')
shutil.copyfile(ROOT/'art/SG_Wood_Atlas.png',MEDIA/'textures/IsoObject/SG_Wood_Atlas.png')

template=(MEDIA/'scripts/entity_sliding_gates.txt').read_text()
entities=['module Base','{','    xuiSkin default','    {']
for width in (2,4):
    for quality in ('','Low','Medium'):
        name=f'SlidingGateWood{width}{quality}'
        entities.extend([f'        entity ES_{name}','        {','            LuaWindowClass = ISEntityWindow,',
            f'            DisplayName = {name},',f'            Icon = SG_BuildWood{width},','        }'])
entities.extend(['    }',''])
for width in (2,4):
    old=f'SlidingGateChainLink{width}'
    start=re.search(r'    entity '+old+r'\s*\{',template).start()
    end=template.index('{',start)+1;depth=1
    while depth:
        depth+=(template[end]=='{')-(template[end]=='}');end+=1
    entity=template[start:end]
    originals=[0,1,6,7,24,25,30,31] if width==2 else [2,3,4,5,12,13,14,15,26,27,28,29,32,33,34,35]
    for quality,offset,level in (('Low',96,4),('Medium',120,5),('',144,7)):
        name=f'SlidingGateWood{width}{quality}'
        text=entity.replace(old,name).replace('SGGateHighRecipeTest','SGGateWood'+(quality or 'High')+'RecipeTest')
        text=text.replace('BuildWireFence','BuildWallHammer').replace('category = Welding','category = Carpentry')
        text=text.replace('MetalWelding:8',f'Woodwork:{level}').replace('MetalWelding:50','Woodwork:50')
        text=text.replace('Tooltip_craft_slidingGateDesc','Tooltip_craft_slidingWoodGateDesc')
        text=re.sub(r'skillBaseHealth = \d+',f'skillBaseHealth = {450 if width==2 else 650}',text)
        mapping={v:offset+(0 if width==2 else 8)+i for i,v in enumerate(originals)}
        text=re.sub(r'sg_gates_preview_01_(\d+)',lambda m:'sg_gates_preview_01_'+str(mapping[int(m[1])]),text)
        inputs='\n'.join([
            '                item 1 tags[base:hammer] mode:keep flags[Prop1;MayDegradeVeryLight],',
            '                item 1 tags[base:saw] mode:keep flags[MayDegradeVeryLight],',
            f'                item {12 if width==2 else 20} [Base.Plank],',
            f'                item {24 if width==2 else 40} [Base.Nails],',
            '                item 8 [Base.Screws],',
            f'                item {1 if width==2 else 2} [Base.Doorknob],',
            f'                item {2 if width==2 else 3} [Base.MetalBar],',
            f'                item {1 if width==2 else 2} [Base.RubberHose],'])
        text=re.sub(r'(            inputs\s*\{)[^}]+(            \})',lambda m:m[1]+'\n'+inputs+'\n'+m[2],text)
        entities.extend([text,''])
entities.extend(['}','']);(MEDIA/'scripts/entity_sliding_gates_wood.txt').write_text('\n'.join(entities),encoding='utf-8')

# All existing locales keep key parity and the existing localized quality suffixes.
labels={
    'EN':('Wooden sliding gate','Carpentry'), 'RU':('Деревянные откатные ворота','Плотничество'),
    'UA':("Дерев’яні відкатні ворота",'Теслярство'), 'DE':('Hölzernes Schiebetor','Tischlerei'),
    'FR':('Portail coulissant en bois','Menuiserie'), 'ES':('Portón corredizo de madera','Carpintería'),
    'IT':('Cancello scorrevole in legno','Carpenteria'), 'PT':('Portão deslizante de madeira','Carpintaria'),
    'PL':('Drewniana brama przesuwna','Stolarstwo'), 'CS':('Dřevěná posuvná brána','Tesařství'),
    'NL':('Houten schuifpoort','Timmeren'), 'DA':('Skydeport af træ','Tømrerarbejde'),
    'NO':('Skyveport av tre','Snekring'), 'FI':('Puinen liukuportti','Puusepäntyö'),
    'HU':('Fa tolókapu','Ácsmesterség'), 'RO':('Poartă culisantă din lemn','Tâmplărie'),
    'TR':('Ahşap sürgülü kapı','Marangozluk'), 'ID':('Gerbang geser kayu','Pertukangan'),
    'AR':('بوابة خشبية منزلقة','النجارة'), 'CA':('Porta corredissa de fusta','Fusteria'),
    'CN':('木制滑动门','木工'), 'CH':('木製滑動門','木工'),
    'JP':('木製スライドゲート','大工仕事'), 'KO':('목제 슬라이딩 게이트','목공'),
    'TH':('ประตูเลื่อนไม้','งานไม้'),
}
for locale in ('ES_CL','ES_MX'):labels[locale]=labels['ES']
labels['PTBR']=labels['PT'];labels['STREW']=labels['EN']
for directory in (MEDIA/'lua/shared/Translate').iterdir():
    if not directory.is_dir():continue
    path=directory/'Recipes.json';data=json.loads(path.read_text(encoding='utf-8-sig'))
    label,skill=labels[directory.name]
    for width in (2,4):
        for quality in ('','Low','Medium'):
            # Preserve the already translated quality labels from chain-link recipes.
            tier=re.search(r'\(([^()]*)\)$',data[f'SlidingGateChainLink{width}{quality}'])[1]
            data[f'SlidingGateWood{width}{quality}']=f'{label} ({width}) ({tier})'
    path.write_text(json.dumps(data,ensure_ascii=False,indent=4)+'\n',encoding='utf-8')
    path=directory/'Tooltip.json';data=json.loads(path.read_text(encoding='utf-8-sig'))
    data['Tooltip_craft_slidingWoodGateDesc']=f'{label}. {skill}: 4 / 5–6 / 7+.'
    path.write_text(json.dumps(data,ensure_ascii=False,indent=4)+'\n',encoding='utf-8')
print('Registered 56 wood models, 208 poses and six carpentry recipes')
