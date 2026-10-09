"""Register X-reflected assets using reflected calibrated N anchors and W rotation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
lines = ['module Base', '{']


def block(kind, name, fields):
    lines.extend([f'    {kind} {name}', '    {'])
    lines.extend(f'        {key} = {value},' for key, value in fields.items())
    lines.extend(['    }', ''])


for prefix in ('SG_ChainLink', 'SG_ChainLink_4'):
    model = prefix+'_N_Reverse'
    block('animationsMesh', model, dict(meshFile='IsoObject/'+model, keepMeshAnimations='true'))
    block('model', model, dict(mesh='IsoObject/'+model, texture='IsoObject/SG_ChainLink_Atlas',
                              animationsMesh=model, shader='door', static='false', undoCoreScale='true'))
    for orientation, translate, rotate in [('N','-0.5 0 -0.38','0 0 0'),('W','-0.38 0 0.5','0 90 0')]:
        for pose, time in [('Closed',0),('Open',6 if prefix.endswith('_4') else 3)]:
            block('spriteModel', prefix+'_'+orientation+'_Reverse_G_'+pose,
                  dict(modelScript='Base.'+model, translate=translate, rotate=rotate, scale='1',
                       animation='Open', animationTime=str(time)))

for part, ntx, tz in [('CatcherPost',0.46,-0.38),('GuidePost',0.54,-0.38),('Rail',0.5,-0.38),('Drive',0.5,-0.6)]:
    model = 'SG_'+part+'_Reverse'
    block('model', model, dict(mesh='IsoObject/'+model, texture='IsoObject/SG_ChainLink_Atlas',
                              shader='door', static='true', undoCoreScale='true'))
    block('spriteModel', model+'_Static', dict(modelScript='Base.'+model, translate=f'{ntx} 0 {tz}', rotate='0 0 0', scale='1'))
    block('spriteModel', model+'_W_Static', dict(modelScript='Base.'+model, translate=f'{tz} 0 {-ntx}', rotate='0 90 0', scale='1'))
lines.extend(['}', ''])
(ROOT/'mod/SlidingGates/42/media/scripts/SG_models_reverse.txt').write_text('\n'.join(lines), encoding='utf8')
print('Registered reverse leaves, four reflected static parts and N/W calibrated poses')
