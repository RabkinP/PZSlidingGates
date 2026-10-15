"""Deploy six-cell GLBs, model scripts, recipes and recipe names.

Every six-cell block is derived from its registered four-cell counterpart, so
anchors, rotations and shaders stay calibrated: names change _4 -> _6, resting
open poses 6 -> 9 seconds. Preview footprints are appended at 184..327
(see art/tiles/README.md); existing indices are untouched.
"""
from pathlib import Path
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / 'mod/SlidingGates/42/media'
SIX = ROOT / 'art/exports/six'
SCRIPTS = MEDIA / 'scripts'
# (material entity prefix, quality suffix) -> first preview index of its 24-tile footprint block
PREVIEW = {('ChainLink', 'Low'): 184, ('ChainLink', 'Medium'): 208, ('ChainLink', ''): 232,
           ('Wood', 'Low'): 256, ('Wood', 'Medium'): 280, ('Wood', ''): 304}

glbs = {p.stem: p for p in SIX.rglob('*.glb')}
assert len(glbs) == 48
for stem, path in glbs.items():
    shutil.copyfile(path, MEDIA / 'models_X/IsoObject' / path.name)

sources = '\n'.join((SCRIPTS / name).read_text(encoding='utf-8') for name in
                    ('SG_models.txt', 'SG_models_quality.txt', 'SG_models_reverse.txt',
                     'SG_models_damage.txt', 'SG_models_wood.txt'))
lines = ['module Base', '{']
counts = {}
for kind, name, body in re.findall(r'\b(animationsMesh|model|spriteModel)\s+(\w+)\s*\{([^}]+)\}', sources):
    if not re.match(r'SG_(ChainLink|Wood)_4_', name) or (kind == 'spriteModel' and '_G_' not in name):
        continue  # Only gate carriers (_G_) are used by the mod; bare poses are legacy.
    reference = re.search(r'(?:meshFile|mesh|modelScript)\s*=\s*(?:IsoObject/|Base\.)(\w+)', body)[1]
    six = reference.replace('_4_', '_6_', 1)
    if six not in glbs:
        continue  # Legacy _Left/_W_Right leaves have no six-cell counterpart.
    body = body.replace('_4_', '_6_')
    if kind == 'spriteModel':
        body = re.sub(r'animationTime = 6(\.0)?,', 'animationTime = 9,', body)
    lines.extend([f'    {kind} {name.replace("_4_", "_6_", 1)}', '    {' + body + '    }', ''])
    counts[kind] = counts.get(kind, 0) + 1
lines.extend(['}', ''])
assert counts == {'animationsMesh': 48, 'model': 48, 'spriteModel': 192}, counts
(SCRIPTS / 'SG_models_six.txt').write_text('\n'.join(lines), encoding='utf-8')

entities = '\n'.join((SCRIPTS / name).read_text(encoding='utf-8') for name in
                     ('entity_sliding_gates.txt', 'entity_sliding_gates_quality.txt',
                      'entity_sliding_gates_wood.txt'))


def entity_block(name):
    match = re.search(r'    entity ' + name + r'\s*\{', entities)
    start, end, depth = match.start(), match.end(), 1
    while depth:
        depth += (entities[end] == '{') - (entities[end] == '}')
        end += 1
    return entities[start:end]


def footprint(start):
    row = lambda indices: ' '.join(f'sg_gates_preview_01_{i}' for i in indices)
    faces = []
    for face, offset in (('N', 0), ('W', 6), ('S', 12), ('E', 18)):
        indices = range(start + offset, start + offset + 6)
        rows = [row(indices)] if face in 'NS' else [row([i]) for i in indices]
        faces += [f'            face {face}', '            {', '                layer', '                {']
        faces += [f'                    row = {r},' for r in rows]
        faces += ['                }', '            }']
    return '\n'.join(faces) + '\n'


# Six-cell inputs: materials scale with frame length; tools and fittings as noted.
INPUTS = {'ChainLink': {'Base.BlowTorch': 8, 'Base.MetalPipe;': 14, 'Base.Wire': 12, 'Base.ScrapMetal': 4,
                        'Base.SmallSheetMetal': 3, 'Base.Screws;': 4, 'Base.WeldingRods': 8,
                        'Base.RubberHose;': 2},
          'Wood': {'Base.Plank': 28, 'Base.Nails': 56, 'Base.Screws': 8, 'Base.MetalBar': 4,
                   'Base.RubberHose': 2}}
out = ['module Base', '{', '    xuiSkin default', '    {']
for material in ('ChainLink', 'Wood'):
    icon = 'SG_BuildGate4' if material == 'ChainLink' else 'SG_BuildWood4'
    for quality in ('', 'Low', 'Medium'):
        out += [f'        entity ES_SlidingGate{material}6{quality}', '        {',
                '            LuaWindowClass = ISEntityWindow,',
                f'            DisplayName = SlidingGate{material}6{quality},', f'            Icon = {icon},', '        }']
out += ['    }', '']
for (material, quality), start in PREVIEW.items():
    old, new = f'SlidingGate{material}4{quality}', f'SlidingGate{material}6{quality}'
    text = entity_block(old).replace(old, new)
    text = re.sub(r'^            face N\n.*?(?=^        \}$)', lambda m: footprint(start), text, flags=re.S | re.M)
    text = re.sub(r'time = \d+,', 'time = 700,', text)
    text = re.sub(r'xpAward = (\w+):\d+,', r'xpAward = \1:60,', text)
    for item, count in INPUTS[material].items():
        text = re.sub(r'item \d+ (\[' + re.escape(item) + ')', f'item {count} \\1', text)
    assert 'sg_gates_preview_01_' + str(start + 23) in text and new in text
    out += [text, '']
out += ['}', '']
(SCRIPTS / 'entity_sliding_gates_six.txt').write_text('\n'.join(out), encoding='utf-8')

# Plural forms where "6 <cells>" differs from "4 <cells>".
PLURAL = {'RU': ('6 клетки', '6 клеток'), 'UA': ('6 клітини', '6 клітин'),
          'CS': ('6 políčka', '6 políček'), 'PL': ('6 pola', '6 pól')}
for directory in (MEDIA / 'lua/shared/Translate').iterdir():
    if not directory.is_dir():
        continue
    path = directory / 'Recipes.json'
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    for material in ('ChainLink', 'Wood'):
        for quality in ('', 'Low', 'Medium'):
            value = data[f'SlidingGate{material}4{quality}']
            assert value.count('4') == 1, (directory.name, value)
            value = value.replace('4', '6')
            if directory.name in PLURAL:
                value = value.replace(*PLURAL[directory.name])
            data[f'SlidingGate{material}6{quality}'] = value
    path.write_text(json.dumps(data, ensure_ascii=False, indent=4) + '\n', encoding='utf-8')
print('Registered 48 six-cell GLBs, 192 poses, 6 recipes; preview footprints 184..327')
