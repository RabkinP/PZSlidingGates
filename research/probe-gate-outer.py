"""Parse the outer-side spriteModels (SG_models_outer.txt) with the installed B42 classes.

The file exceeds the 65535-byte class constant limit, so it is parsed as several
`module Base` chunks through the same ScriptManager.ParseScript pass.
"""
import ast
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
template=(ROOT/'research/probe-drive-recipe.py').read_text().replace('PZDriveRecipeProbe','PZGateOuterProbe')
tree=ast.parse(template)
index=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='script' for t in n.targets))
ns={'__file__':str(__file__)}
exec(compile(ast.Module(body=tree.body[:index],type_ignores=[]),'<probe-bootstrap>','exec'),ns)
script=(ROOT/'mod/SlidingGates/42/media/scripts/SG_models_outer.txt').read_text(encoding='utf-8')
entries=re.findall(r'(    spriteModel\s+\w+\s*\{[^}]+\})',script)
names=re.findall(r'\bspriteModel\s+(\w+)\s*\{',script)
assert len(entries)==len(names)==608
chunks,current=[],[]
for entry in entries:
    current.append(entry)
    if sum(map(len,current))>40000:
        chunks.append(current); current=[]
if current: chunks.append(current)
chunks=['module Base\n{\n'+'\n'.join(chunk)+'\n}\n' for chunk in chunks]
ns['script']=chunks[0]
end=next(i for i in range(index+1,len(tree.body)) if isinstance(tree.body[i],ast.For))
exec(compile(ast.Module(body=tree.body[index+1:end],type_ignores=[]),'<probe-init>','exec'),ns)
c,p,call,field,text,u2=(ns[k] for k in ('c','p','call','field','text','u2'))
for chunk in chunks[1:]:
    c+=field('zombie/scripting/ScriptManager','instance','Lzombie/scripting/ScriptManager;')
    c+=field('zombie/scripting/ScriptLoadMode','Init','Lzombie/scripting/ScriptLoadMode;')+text(chunk)
    c+=call('zombie/scripting/ScriptManager','ParseScript','(Lzombie/scripting/ScriptLoadMode;Ljava/lang/String;)V')
for collection in ('models','animationMeshes','spriteModels'):
    c+=field('zombie/scripting/ScriptManager','instance','Lzombie/scripting/ScriptManager;')+text(collection)
    c+=call('PZGateOuterProbe','getField','(Ljava/lang/Object;Ljava/lang/String;)Ljava/lang/Object;',0xb8)
    c+=b'\xc0'+u2(p.cls('zombie/scripting/ScriptBucketCollection'))
    c+=field('zombie/scripting/ScriptLoadMode','Init','Lzombie/scripting/ScriptLoadMode;')
    c+=call('zombie/scripting/ScriptBucketCollection','LoadScripts','(Lzombie/scripting/ScriptLoadMode;)V')
for name in names:
    c+=field('zombie/scripting/ScriptManager','instance','Lzombie/scripting/ScriptManager;')+text('Base.'+name)
    c+=call('zombie/scripting/ScriptManager','getSpriteModel','(Ljava/lang/String;)Lzombie/iso/SpriteModel;')
    c+=call('java/util/Objects','requireNonNull','(Ljava/lang/Object;)Ljava/lang/Object;',0xb8)+b'\x57'
c+=b'\xb1';p.method('main','([Ljava/lang/String;)V',c,9);p.save('PZGateOuterProbe')
GAME,OUT=ns['GAME'],ns['OUT']
run=subprocess.run([str(GAME/'jre64/bin/java.exe'),'-Djava.awt.headless=true',f'-Duser.home={OUT}',
                    '-cp',f'{OUT};{GAME}/projectzomboid.jar','PZGateOuterProbe'],cwd=ROOT,capture_output=True,text=True)
(ROOT/'research/render-audit/gate-outer-native.txt').write_text(run.stdout+run.stderr)
assert run.returncode==0,run.stdout+run.stderr
print(f'PASS installed B42 parser: {len(names)} outer spriteModels in {len(chunks)} chunks')
