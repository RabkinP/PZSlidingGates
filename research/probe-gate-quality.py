"""Parse all six entity recipes with installed B42 classes, no world or UI."""
import ast
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
# Reuse the maintained classfile/reflection bootstrap; don't require a JDK.
template=(ROOT/'research/probe-drive-recipe.py').read_text().replace('PZDriveRecipeProbe','PZGateQualityProbe')
template=template.replace('+text(script)', "+text(script)+call('zombie/scripting/ScriptParser','stripComments','(Ljava/lang/String;)Ljava/lang/String;',0xb8)")
tree=ast.parse(template)
script_index=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.Assign)
                  and any(isinstance(t,ast.Name) and t.id=='script' for t in n.targets))
ns={'__file__':str(__file__)}
exec(compile(ast.Module(body=tree.body[:script_index],type_ignores=[]),'<probe-bootstrap>','exec'),ns)
media=ROOT/'mod/SlidingGates/42/media'
ns['script']=(media/'scripts/entity_sliding_gates.txt').read_text(encoding='utf-8')
first_loop=next(i for i in range(script_index+1,len(tree.body)) if isinstance(tree.body[i],ast.For))
exec(compile(ast.Module(body=tree.body[script_index+1:first_loop],type_ignores=[]),'<probe-init>','exec'),ns)
c,p,call,field,text,u2=(ns[k] for k in ('c','p','call','field','text','u2'))
c+=field('zombie/scripting/ScriptManager','instance','Lzombie/scripting/ScriptManager;')+text('entity_sliding_gates_quality.txt')
c+=b'\xb5'+u2(p.ref('zombie/scripting/ScriptManager','currentFileName','Ljava/lang/String;',9))
c+=field('zombie/scripting/ScriptManager','instance','Lzombie/scripting/ScriptManager;')
c+=field('zombie/scripting/ScriptLoadMode','Init','Lzombie/scripting/ScriptLoadMode;')
c+=text((media/'scripts/entity_sliding_gates_quality.txt').read_text(encoding='utf-8'))
c+=call('zombie/scripting/ScriptParser','stripComments','(Ljava/lang/String;)Ljava/lang/String;',0xb8)
c+=call('zombie/scripting/ScriptManager','ParseScript','(Lzombie/scripting/ScriptLoadMode;Ljava/lang/String;)V')
for collection in ('xuiSkinScripts','entities'):
    c+=field('zombie/scripting/ScriptManager','instance','Lzombie/scripting/ScriptManager;')+text(collection)
    c+=call('PZGateQualityProbe','getField','(Ljava/lang/Object;Ljava/lang/String;)Ljava/lang/Object;',0xb8)
    c+=b'\xc0'+u2(p.cls('zombie/scripting/ScriptBucketCollection'))
    c+=field('zombie/scripting/ScriptLoadMode','Init','Lzombie/scripting/ScriptLoadMode;')
    c+=call('zombie/scripting/ScriptBucketCollection','LoadScripts','(Lzombie/scripting/ScriptLoadMode;)V')
recipe_class='zombie/scripting/entity/components/crafting/CraftRecipe'
expected=[]
c+=field('zombie/scripting/ScriptManager','instance','Lzombie/scripting/ScriptManager;')+text('Base.default')
c+=call('zombie/scripting/ScriptManager','getXuiSkinScript','(Ljava/lang/String;)Lzombie/scripting/objects/XuiSkinScript;')
c+=text('entityUiScriptMap')+call('PZGateQualityProbe','getField','(Ljava/lang/Object;Ljava/lang/String;)Ljava/lang/Object;',0xb8)
c+=b'\xc0'+u2(p.cls('java/util/HashMap'))+b'\x4e'
for width in (2,4):
    for suffix,quality,level in (('Low','Low',4),('Medium','Medium',6),('','High',8)):
        name=f'Base.SlidingGateChainLink{width}{suffix}'
        c+=b'\x2d'+text(f'ES_SlidingGateChainLink{width}{suffix}')
        c+=call('java/util/HashMap','get','(Ljava/lang/Object;)Ljava/lang/Object;')
        c+=call('java/util/Objects','requireNonNull','(Ljava/lang/Object;)Ljava/lang/Object;',0xb8)+b'\x57'
        callback='SGGate'+quality+'RecipeTest';expected.append(f'{name}\n{level}\n{callback}\n')
        c+=field('java/lang/System','out','Ljava/io/PrintStream;')+text(name)
        c+=call('java/io/PrintStream','println','(Ljava/lang/String;)V')
        c+=field('zombie/scripting/ScriptManager','instance','Lzombie/scripting/ScriptManager;')+text(name)
        c+=call('zombie/scripting/ScriptManager','getCraftRecipe',f'(Ljava/lang/String;)L{recipe_class};')+b'\x4c'
        c+=field('java/lang/System','out','Ljava/io/PrintStream;')+b'\x2b\x03'
        c+=call(recipe_class,'getRequiredSkill',f'(I)L{recipe_class}$RequiredSkill;')
        c+=call(recipe_class+'$RequiredSkill','getLevel','()I')
        c+=call('java/io/PrintStream','println','(I)V')
        c+=field('java/lang/System','out','Ljava/io/PrintStream;')+b'\x2b'
        c+=call(recipe_class,'getOnAddToMenu','()Ljava/lang/String;')
        c+=call('java/io/PrintStream','println','(Ljava/lang/String;)V')
c+=b'\xb1';p.method('main','([Ljava/lang/String;)V',c,9);p.save('PZGateQualityProbe')
GAME,OUT=ns['GAME'],ns['OUT']
run=subprocess.run([str(GAME/'jre64/bin/java.exe'),'-Djava.awt.headless=true',f'-Duser.home={OUT}',
                    '-cp',f'{OUT};{GAME}/projectzomboid.jar','PZGateQualityProbe'],cwd=ROOT,capture_output=True,text=True)
print(run.stdout,end='');print(run.stderr,end='')
if run.returncode:raise SystemExit(run.returncode)
for entry in expected:assert entry in run.stdout.replace('\r',''),entry
(ROOT/'research/render-audit/gate-quality-native.txt').write_text(run.stdout+run.stderr,encoding='utf-8')
print('PASS all six native entity recipes and UI styles: welding requirements 4/6/8 and menu callbacks')
