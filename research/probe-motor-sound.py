"""Check the custom sound script with the installed B42 GameSoundScript parser."""
import ast
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
GAME = Path('E:/SteamLibrary/steamapps/common/ProjectZomboid')
OUT = ROOT/'research/render-audit/probe'
OUT.mkdir(parents=True, exist_ok=True)
source = ast.parse((ROOT/'research/probe-assimp.py').read_text())
ns = dict(struct=struct, ROOT=OUT)
exec(compile(ast.Module(body=[n for n in source.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))],
                       type_ignores=[]), '<classfile-writer>', 'exec'), ns)
p = ns['ClassFile']('PZMotorSoundProbe', 'java/lang/Object')
u2 = ns['u2']


def call(owner, name, signature, opcode=0xb6):
    return bytes([opcode])+u2(p.ref(owner, name, signature))


def text(value):
    return b'\x13'+u2(p.string(value))


script = (ROOT/'mod/SlidingGates/42/media/scripts/SG_sounds.txt').read_text()
body = script[script.index('sound SG_GateMotorRunning'):script.rindex('}')]
c = b'\xbb'+u2(p.cls('zombie/scripting/objects/GameSoundScript'))+b'\x59'
c += call('zombie/scripting/objects/GameSoundScript', '<init>', '()V', 0xb7)+b'\x4c\x2b'
c += text('SG_GateMotorRunning')+text(body)
c += call('zombie/scripting/objects/GameSoundScript', 'Load', '(Ljava/lang/String;Ljava/lang/String;)V')
c += b'\x2b\xb4'+u2(p.ref('zombie/scripting/objects/GameSoundScript', 'gameSound', 'Lzombie/audio/GameSound;', 9))+b'\x4d'
for field in ('loop', 'is3d'):
    c += b'\xb2'+u2(p.ref('java/lang/System', 'out', 'Ljava/io/PrintStream;', 9))+b'\x2c\xb4'
    c += u2(p.ref('zombie/audio/GameSound', field, 'Z', 9))+call('java/io/PrintStream', 'println', '(Z)V')
c += b'\x2c\xb4'+u2(p.ref('zombie/audio/GameSound', 'clips', 'Ljava/util/ArrayList;', 9))+b'\x03'
c += call('java/util/ArrayList', 'get', '(I)Ljava/lang/Object;')+b'\xc0'+u2(p.cls('zombie/audio/GameSoundClip'))+b'\x4e'
for field, sig in (('file','Ljava/lang/String;'), ('distanceMin','F'), ('distanceMax','F'), ('volume','F')):
    c += b'\xb2'+u2(p.ref('java/lang/System', 'out', 'Ljava/io/PrintStream;', 9))+b'\x2d\xb4'
    c += u2(p.ref('zombie/audio/GameSoundClip', field, sig, 9))+call('java/io/PrintStream', 'println', '('+sig+')V')
c += b'\xb1'
p.method('main', '([Ljava/lang/String;)V', c, 9)
p.save('PZMotorSoundProbe')
run = subprocess.run([str(GAME/'jre64/bin/java.exe'), '-Djava.awt.headless=true', f'-Duser.home={OUT}',
                      '-cp', f'{OUT};{GAME}/projectzomboid.jar', 'PZMotorSoundProbe'],
                     cwd=ROOT, capture_output=True, text=True)
print(run.stdout, end='')
print(run.stderr, end='')
assert run.returncode == 0
assert run.stdout.strip().splitlines() == ['true','true','media/sound/SG_GateMotorRunning.wav','2.0','20.0','1.0']
print('PASS installed sound parser: loop, 3D, selected WAV, distances and volume')
(ROOT/'research/render-audit/motor-sound-native.txt').write_text(run.stdout+run.stderr, encoding='utf8')
