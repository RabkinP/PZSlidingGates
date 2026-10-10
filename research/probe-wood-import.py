"""Read all wood GLBs with the installed game's JNI/Assimp route."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess
import hashlib

ROOT=Path(__file__).resolve().parents[1]
GAME=Path(r'E:\SteamLibrary\steamapps\common\ProjectZomboid')
fingerprint=hashlib.sha256((GAME/'projectzomboid.jar').read_bytes()).hexdigest().upper()
assert fingerprint=='E1A69EB743EDE60B213A0FE7F8B83D4FCAB773036D256CC4543A336F3B058A33'
paths=sorted((ROOT/'art/exports/wood').glob('*.glb'));assert len(paths)==56
def check(path):
    run=subprocess.run([str(GAME/'jre64/bin/java.exe'),'--enable-native-access=ALL-UNNAMED',
        f'-Djava.library.path={GAME}','-cp',f'{ROOT}/research/render-audit/probe;{GAME}/projectzomboid.jar',
        'PZImportProbe',str(path)],cwd=ROOT,capture_output=True,text=True)
    assert run.returncode==0,(path.name,run.stdout,run.stderr)
    values=run.stdout.strip().splitlines()
    assert len(values)==10 and int(values[0])>0 and int(values[1])>0,(path.name,run.stdout)
    assert abs(sum(float(v)**2 for v in values[5:8])-1)<1e-4,(path.name,run.stdout)
    return path.name+'\n'+run.stdout+run.stderr
with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(check,paths))
(ROOT/'art/wood_native_import.txt').write_text('Installed JAR SHA256 '+fingerprint+'\n\n'+'\n'.join(results))
print('PASS installed JNI importer: all 56 wood GLBs; first-vertex diagnostics saved')
