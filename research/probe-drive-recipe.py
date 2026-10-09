"""Parse drive items/recipe using installed B42 classes, without a game world."""
import ast
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAME = Path(r'E:/SteamLibrary/steamapps/common/ProjectZomboid')
OUT = ROOT/'research/render-audit/probe'
OUT.mkdir(parents=True, exist_ok=True)
source = ast.parse((ROOT/'research/probe-assimp.py').read_text())
ns = dict(struct=struct, ROOT=OUT)
exec(compile(ast.Module(body=[n for n in source.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))], type_ignores=[]), '<classfile-writer>', 'exec'), ns)
p = ns['ClassFile']('PZDriveRecipeProbe', 'java/lang/Object')
u2 = ns['u2']


def call(owner, name, signature, opcode=0xb6):
    return bytes([opcode])+u2(p.ref(owner, name, signature))


def field(owner, name, signature):
    return b'\xb2'+u2(p.ref(owner, name, signature, 9))


def text(value):
    return b'\x13'+u2(p.string(value))


# Read the private script collections so their real second loading pass runs.
helper = b'\x2a'+call('java/lang/Object', 'getClass', '()Ljava/lang/Class;')+b'\x2b'
helper += call('java/lang/Class', 'getDeclaredField', '(Ljava/lang/String;)Ljava/lang/reflect/Field;')+b'\x4d\x2c\x04'
helper += call('java/lang/reflect/Field', 'setAccessible', '(Z)V')+b'\x2c\x2a'
helper += call('java/lang/reflect/Field', 'get', '(Ljava/lang/Object;)Ljava/lang/Object;')+b'\xb0'
p.method('getField', '(Ljava/lang/Object;Ljava/lang/String;)Ljava/lang/Object;', helper, 9)

script = (ROOT/'mod/SlidingGates/42/media/scripts/SG_drive.txt').read_text()
c = field('zombie/core/random/RandStandard', 'INSTANCE', 'Lzombie/core/random/RandStandard;')
c += call('zombie/core/random/RandStandard', 'init', '()V')
c += b'\x04\xb3'+u2(p.ref('zombie/network/GameServer', 'server', 'Z', 9))
c += text('zombie.scripting.ScriptManager')+call('java/lang/Class', 'forName', '(Ljava/lang/String;)Ljava/lang/Class;', 0xb8)
c += text('currentLoadFileMod')+call('java/lang/Class', 'getDeclaredField', '(Ljava/lang/String;)Ljava/lang/reflect/Field;')+b'\x4d\x2c\x04'
c += call('java/lang/reflect/Field', 'setAccessible', '(Z)V')+b'\x2c\x01'+text('pz-vanilla')
c += call('java/lang/reflect/Field', 'set', '(Ljava/lang/Object;Ljava/lang/Object;)V')
c += call('zombie/characters/skills/PerkFactory', 'init', '()V', 0xb8)
c += field('zombie/scripting/ScriptManager', 'instance', 'Lzombie/scripting/ScriptManager;')+text('SG_drive.txt')
c += b'\xb5'+u2(p.ref('zombie/scripting/ScriptManager', 'currentFileName', 'Ljava/lang/String;', 9))
c += field('zombie/scripting/ScriptManager', 'instance', 'Lzombie/scripting/ScriptManager;')
c += field('zombie/scripting/ScriptLoadMode', 'Init', 'Lzombie/scripting/ScriptLoadMode;')+text(script)
c += call('zombie/scripting/ScriptManager', 'ParseScript', '(Lzombie/scripting/ScriptLoadMode;Ljava/lang/String;)V')
for collection in ('items', 'craftRecipes'):
    c += field('zombie/scripting/ScriptManager', 'instance', 'Lzombie/scripting/ScriptManager;')+text(collection)
    c += call('PZDriveRecipeProbe', 'getField', '(Ljava/lang/Object;Ljava/lang/String;)Ljava/lang/Object;', 0xb8)
    c += b'\xc0'+u2(p.cls('zombie/scripting/ScriptBucketCollection'))
    c += field('zombie/scripting/ScriptLoadMode', 'Init', 'Lzombie/scripting/ScriptLoadMode;')
    c += call('zombie/scripting/ScriptBucketCollection', 'LoadScripts', '(Lzombie/scripting/ScriptLoadMode;)V')
for name in ('SlidingGates.ElectricMotor', 'SlidingGates.GateDrive', 'SlidingGates.GateRemote'):
    c += field('zombie/scripting/ScriptManager', 'instance', 'Lzombie/scripting/ScriptManager;')+text(name)
    c += call('zombie/scripting/ScriptManager', 'getItem', '(Ljava/lang/String;)Lzombie/scripting/objects/Item;')
    c += call('java/util/Objects', 'requireNonNull', '(Ljava/lang/Object;)Ljava/lang/Object;', 0xb8)+b'\x57'
for recipe in ('SlidingGates.AssembleSlidingGateDrive', 'SlidingGates.AssembleSlidingGateRemote'):
    c += field('zombie/scripting/ScriptManager', 'instance', 'Lzombie/scripting/ScriptManager;')+text(recipe)
    c += call('zombie/scripting/ScriptManager', 'getCraftRecipe', '(Ljava/lang/String;)Lzombie/scripting/entity/components/crafting/CraftRecipe;')+b'\x4c'
    for name, signature in [('isAnySurfaceCraft', '()Z'), ('canBeDoneInDark', '()Z'), ('getRequiredSkillCount', '()I'), ('getXPAwardCount', '()I'), ('getTime', '()I')]:
        c += field('java/lang/System', 'out', 'Ljava/io/PrintStream;')+b'\x2b'
        c += call('zombie/scripting/entity/components/crafting/CraftRecipe', name, signature)
        c += call('java/io/PrintStream', 'println', '('+signature[-1]+')V')
    for name in ('getInputs', 'getOutputs'):
        c += field('java/lang/System', 'out', 'Ljava/io/PrintStream;')+b'\x2b'
        c += call('zombie/scripting/entity/components/crafting/CraftRecipe', name, '()Ljava/util/ArrayList;')
        c += call('java/util/ArrayList', 'size', '()I')+call('java/io/PrintStream', 'println', '(I)V')
    c += field('java/lang/System', 'out', 'Ljava/io/PrintStream;')+b'\x2b'
    c += call('zombie/scripting/entity/components/crafting/CraftRecipe', 'needToBeLearn', '()Z')
    c += call('java/io/PrintStream', 'println', '(Z)V')
c += b'\xb1'
p.method('main', '([Ljava/lang/String;)V', c, 9)
p.save('PZDriveRecipeProbe')
run = subprocess.run([str(GAME/'jre64/bin/java.exe'), '-Djava.awt.headless=true', f'-Duser.home={OUT}', '-cp', f'{OUT};{GAME}/projectzomboid.jar', 'PZDriveRecipeProbe'], cwd=ROOT, capture_output=True, text=True)
print(run.stdout, end='')
print(run.stderr, end='')
if run.returncode:
    raise SystemExit(run.returncode)
assert '\ntrue\nfalse\n3\n3\n500\n12\n1\n' in '\n'+run.stdout.replace('\r', '')
assert '\ntrue\nfalse\n1\n1\n100\n5\n1\nfalse\n' in '\n'+run.stdout.replace('\r', '')
print('PASS native drive/remote items and recipes: surface/light, skills, time, inputs/output')
(ROOT/'research/render-audit/drive-recipe-native.txt').write_text(run.stdout+run.stderr)
