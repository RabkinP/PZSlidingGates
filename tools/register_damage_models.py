"""Deploy damaged GLBs; derive every sprite anchor/pose from existing definitions."""
from pathlib import Path
import re
import shutil

ROOT=Path(__file__).resolve().parents[1]
MEDIA=ROOT/'mod/SlidingGates/42/media'
sources='\n'.join(p.read_text() for p in (MEDIA/'scripts').glob('SG_models*.txt') if p.name!='SG_models_damage.txt')
blocks={name:(kind,body) for kind,name,body in re.findall(r'\b(model|animationsMesh|spriteModel)\s+(\w+)\s*\{([^}]+)\}',sources)}
lines=['module Base','{']
count=0
for width in (2,4):
    prefix='SG_ChainLink' if width==2 else 'SG_ChainLink_4'
    for quality in ('','_Low','_Medium'):
        for reverse in (False,True):
            model=prefix+quality+'_N_'+('Reverse' if reverse else 'Right')
            for stage in (1,2,3):
                damaged=model+f'_Damage{stage}'
                shutil.copyfile(ROOT/'art/exports/damage'/f'{damaged}.glb',MEDIA/'models_X/IsoObject'/f'{damaged}.glb')
                for name in (model,):
                    # animationsMesh and model have the same name; retain both blocks.
                    for kind,body in re.findall(r'\b(animationsMesh|model)\s+'+name+r'\s*\{([^}]+)\}',sources):
                        lines.extend([f'    {kind} {damaged}','    {'+body.replace(name,damaged)+'    }'])
                for orientation in ('N','W'):
                    base=prefix+quality+'_'+orientation+('_Reverse' if reverse else ('_Right' if orientation=='N' else ''))+'_G'
                    for pose in ('Closed','Open'):
                        kind,body=blocks[base+'_'+pose]
                        lines.extend([f'    {kind} {base}_Damage{stage}_{pose}',
                                      '    {'+body.replace('Base.'+model,'Base.'+damaged)+'    }'])
                count+=1
lines.extend(['}',''])
(MEDIA/'scripts/SG_models_damage.txt').write_text('\n'.join(lines),encoding='utf-8')
print('Deployed',count,'damage GLBs and',count*4,'resting poses')
