"""Import all 48 six-cell source GLBs through the installed PZ JNI importer."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
GAME = Path(r'E:\SteamLibrary\steamapps\common\ProjectZomboid')
fingerprint = hashlib.sha256((GAME / 'projectzomboid.jar').read_bytes()).hexdigest().upper()
assert fingerprint == 'E1A69EB743EDE60B213A0FE7F8B83D4FCAB773036D256CC4543A336F3B058A33'
manifest = json.loads((ROOT / 'art/six_export_manifest.json').read_text())
assert len(manifest) == 48


def check(row):
    path = ROOT / 'art' / row['path']
    run = subprocess.run([str(GAME / 'jre64/bin/java.exe'), '--enable-native-access=ALL-UNNAMED',
        f'-Djava.library.path={GAME}', '-cp', f'{ROOT}/research/render-audit/probe;{GAME}/projectzomboid.jar',
        'PZImportProbe', str(path)], cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 0, (path.name, run.stdout, run.stderr)
    values = run.stdout.strip().splitlines()
    assert len(values) == 10 and int(values[0]) > 0 and int(values[1]) > 0, (path.name, run.stdout)
    assert abs(sum(float(v)**2 for v in values[5:8]) - 1) < 1e-4, (path.name, run.stdout)
    return row['path'] + '\n' + run.stdout + run.stderr


with ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(check, manifest))
(ROOT / 'art/six_native_import.txt').write_text(
    'Installed JAR SHA256 ' + fingerprint + '\n\n' + '\n'.join(results), encoding='utf-8')
print('PASS installed JNI importer: all 48 six-cell GLBs; first-vertex diagnostics saved')
