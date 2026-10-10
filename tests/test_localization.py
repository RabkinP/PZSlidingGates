"""Translation loader filenames, locale parity and player-facing script keys."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / 'mod/SlidingGates/42/media'
TRANSLATE = MEDIA / 'lua/shared/Translate'
# Installed B42 Translator.BY_NAME basenames, not getText prefixes.
CATEGORIES = {'ContextMenu', 'IG_UI', 'ItemName', 'Recipes', 'Tooltip', 'UI'}

def read_locale(directory):
    assert {p.stem for p in directory.glob('*.json')} == CATEGORIES, directory
    result = {}
    for path in directory.glob('*.json'):
        entries = json.loads(path.read_text(encoding='utf-8-sig'))
        assert all(isinstance(v, str) and v.strip() for v in entries.values()), path
        result[path.stem] = entries
    return result

english = read_locale(TRANSLATE / 'EN')
locales = [p for p in TRANSLATE.iterdir() if p.is_dir()]
for locale in locales:
    entries = read_locale(locale)
    for category, values in english.items():
        assert entries[category].keys() == values.keys(), (locale.name, category)
        for key, value in values.items():
            assert sorted(re.findall(r'<[^>]+>', entries[category][key])) == sorted(re.findall(r'<[^>]+>', value)), (locale.name, key)

keys = {key for values in english.values() for key in values}
entity = '\n'.join(p.read_text() for p in (MEDIA/'scripts').glob('entity_sliding_gates*.txt'))
# XuiSkinScript removes spaces and calls Translator.getRecipeName.
names = re.findall(r'DisplayName\s*=\s*([^,\r\n]+)', entity)
assert len(names) == 12
for name in names:
    assert name.replace(' ', '') in english['Recipes'], name
for recipe in re.findall(r'\b(?:craftRecipe|buildRecipe)\s+(\w+)', '\n'.join(p.read_text() for p in (MEDIA / 'scripts').glob('*.txt'))):
    assert recipe in english['Recipes'], recipe
for item in ('ElectricMotor', 'GateDrive', 'GateRemote'):
    assert 'SlidingGates.' + item in english['ItemName']
assert 'IGUI_ContainerTitle_sg_drive_battery' in english['IG_UI']
for path in (MEDIA / 'lua').rglob('*.lua'):
    for key in re.findall(r'["\']((?:ContextMenu|Tooltip|UI|IGUI)_SG_[\w]+)["\']', path.read_text()):
        if key.endswith('_'):  # Dynamic drive rejection reason suffix.
            continue
        assert key in keys, (path.name, key)
for reason in ('missing', 'instance', 'busy', 'changed', 'distance', 'skills', 'tools', 'materials', 'contents', 'power'):
    assert 'Tooltip_SG_Drive_' + reason in english['Tooltip']
print(f'PASS: {len(locales)} locales, {len(keys)} keys; loader categories, construction, recipes, items and UI coverage')
