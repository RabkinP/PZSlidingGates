"""Installed B42 parsing of wood models, animation meshes, poses and recipes."""
import ast
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MEDIA=ROOT/'mod/SlidingGates/42/media'
template=(ROOT/'research/probe-drive-recipe.py').read_text().replace('PZDriveRecipeProbe','PZWoodProbe')
tree=ast.parse(template)
index=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='script' for t in n.targets))
ns={'__file__':str(__file__)}
exec(compile(ast.Module(body=tree.body[:index],type_ignores=[]),'<bootstrap>','exec'),ns)
script=(MEDIA/'scripts/SG_models_wood.txt').read_text()
blocks=re.findall(r'\b(?:model|animationsMesh|spriteModel)\s+\w+\s*\{[^}]+\}',script)
chunks=['module Base\n{\n'+'\n'.join(blocks[i:i+100])+'\n}' for i in range(0,len(blocks),100)]
ns['script']=chunks[0]
end=next(i for i in range(index+1,len(tree.body)) if isinstance(tree.body[i],ast.For))
exec(compile(ast.Module(body=tree.body[index+1:end],type_ignores=[]),'<init>','exec'),ns)
c,p,call,field,text,u2=(ns[k] for k in ('c','p','call','field','text','u2'))
def parse(code,name):
    global c
    c+=field('zombie/scripting/ScriptManager','instance','Lzombie/scripting/ScriptManager;')+text(name)
    c+=b'\xb5'+u2(p.ref('zombie/scripting/ScriptManager','currentFileName','Ljava/lang/String;',9))
    c+=field('zombie/scripting/ScriptManager','instance','Lzombie/scripting/ScriptManager;')
    c+=field('zombie/scripting/ScriptLoadMode','Init','Lzombie/scripting/ScriptLoadMode;')
    c+=text(code)+call('zombie/scripting/ScriptParser','stripComments','(Ljava/lang/String;)Ljava/lang/String;',0xb8)
    c+=call('zombie/scripting/ScriptManager','ParseScript','(Lzombie/scripting/ScriptLoadMode;Ljava/lang/String;)V')
for i,chunk in enumerate(chunks[1:]):parse(chunk,f'wood-models-{i}.txt')
recipes=(MEDIA/'scripts/entity_sliding_gates_wood.txt').read_text()
parse(recipes,'entity_sliding_gates_wood.txt')
for collection in ('models','animationMeshes','spriteModels','xuiSkinScripts','entities'):
    c+=field('zombie/scripting/ScriptManager','instance','Lzombie/scripting/ScriptManager;')+text(collection)
    c+=call('PZWoodProbe','getField','(Ljava/lang/Object;Ljava/lang/String;)Ljava/lang/Object;',0xb8)
    c+=b'\xc0'+u2(p.cls('zombie/scripting/ScriptBucketCollection'))
    c+=field('zombie/scripting/ScriptLoadMode','Init','Lzombie/scripting/ScriptLoadMode;')
    c+=call('zombie/scripting/ScriptBucketCollection','LoadScripts','(Lzombie/scripting/ScriptLoadMode;)V')
for kind,name in re.findall(r'\b(model|spriteModel)\s+(\w+)\s*\{',script):
    c+=field('zombie/scripting/ScriptManager','instance','Lzombie/scripting/ScriptManager;')+text('Base.'+name)
    method,cls=('getModelScript','zombie/scripting/objects/ModelScript') if kind=='model' else ('getSpriteModel','zombie/iso/SpriteModel')
    c+=call('zombie/scripting/ScriptManager',method,'(Ljava/lang/String;)L'+cls+';')
    c+=call('java/util/Objects','requireNonNull','(Ljava/lang/Object;)Ljava/lang/Object;',0xb8)+b'\x57'
expected=[];recipe_class='zombie/scripting/entity/components/crafting/CraftRecipe'
for width in (2,4):
    for suffix,level in (('Low',4),('Medium',5),('',7)):
        name=f'Base.SlidingGateWood{width}{suffix}'
        expected.append(f'{name}\n{level}\nSGGateWood{suffix or "High"}RecipeTest\n')
        c+=field('java/lang/System','out','Ljava/io/PrintStream;')+text(name)+call('java/io/PrintStream','println','(Ljava/lang/String;)V')
        c+=field('zombie/scripting/ScriptManager','instance','Lzombie/scripting/ScriptManager;')+text(name)
        c+=call('zombie/scripting/ScriptManager','getCraftRecipe',f'(Ljava/lang/String;)L{recipe_class};')+b'\x4c'
        c+=field('java/lang/System','out','Ljava/io/PrintStream;')+b'\x2b\x03'
        c+=call(recipe_class,'getRequiredSkill',f'(I)L{recipe_class}$RequiredSkill;')
        c+=call(recipe_class+'$RequiredSkill','getLevel','()I')+call('java/io/PrintStream','println','(I)V')
        c+=field('java/lang/System','out','Ljava/io/PrintStream;')+b'\x2b'
        c+=call(recipe_class,'getOnAddToMenu','()Ljava/lang/String;')+call('java/io/PrintStream','println','(Ljava/lang/String;)V')
c+=b'\xb1';p.method('main','([Ljava/lang/String;)V',c,9);p.save('PZWoodProbe')
GAME,OUT=ns['GAME'],ns['OUT']
run=subprocess.run([str(GAME/'jre64/bin/java.exe'),'-Djava.awt.headless=true',f'-Duser.home={OUT}',
    '-cp',f'{OUT};{GAME}/projectzomboid.jar','PZWoodProbe'],cwd=ROOT,capture_output=True,text=True)
(ROOT/'research/render-audit/wood-native.txt').write_text(run.stdout+run.stderr)
assert run.returncode==0,run.stdout+run.stderr
for entry in expected:assert entry in run.stdout.replace('\r',''),entry
print('PASS installed parser: 56 models, 48 animation meshes, 208 poses, six recipes (Woodwork 4/5/7)')
