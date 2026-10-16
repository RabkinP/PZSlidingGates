"""Register outer-side spriteModels for every placed leaf and static part.

Derived from the registered inner spriteModels (all widths, materials, qualities, damage
stages, N/W, forward/reverse) with tools/outer_variant.py. No new meshes: the mirrored model of
each pair is rotated 180 degrees. Names: leaf ..._G[_DamageN]_Pose -> ..._G_Out[_DamageN]_Pose,
static ..._Static -> ..._Out_Static (SGGate.leafModel / staticModel in Lua).
Rerun after registering new inner variants; the output is regenerated in full.
"""
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from outer_variant import outer  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT/'mod/SlidingGates/42/media/scripts'
OUTPUT = SCRIPTS/'SG_models_outer.txt'
LEAF = re.compile(r'_G(?=(_Damage\d)?_(Open|Closed)$)')


def outer_name(name):
    if '_Left' in name:  # historical prototype leaves, never placed
        return None
    if name.endswith('_Static'):
        return name[:-len('_Static')] + '_Out_Static'
    if LEAF.search(name):
        return LEAF.sub('_G_Out', name, count=1)


def sprite_models():
    for path in sorted(SCRIPTS.glob('SG_models*.txt')):
        if path == OUTPUT:
            continue
        text = path.read_text(encoding='utf-8')
        for name, body in re.findall(r'\bspriteModel\s+(\w+)\s*\{([^}]+)\}', text):
            yield name, dict((k, v.strip()) for k, v in re.findall(r'(\w+)\s*=\s*([^,\n]+),', body))


def main():
    lines = ['module Base', '{']
    names = set()
    for name, fields in sprite_models():
        target = outer_name(name)
        if not target:
            continue
        assert target not in names, target
        names.add(target)
        lines += [f'    spriteModel {target}', '    {']
        lines += [f'        {key} = {value},' for key, value in outer(fields).items()]
        lines += ['    }', '']
    lines += ['}', '']
    OUTPUT.write_text('\n'.join(lines), encoding='utf-8')
    print(f'Registered {len(names)} outer spriteModels in {OUTPUT.name}')


if __name__ == '__main__':
    main()
