"""Parse damaged model scripts and spriteModels with the installed B42 classes."""
import ast
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
template=(ROOT/'research/probe-drive-recipe.py').read_text().replace('PZDriveRecipeProbe','PZGateDamageProbe')
tree=ast.parse(template)
index=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='script' for t in n.targets))
ns={'__file__':str(__file__)}
exec(compile(ast.Module(body=tree.body[:index],type_ignores=[]),'<probe-bootstrap>','exec'),ns)
script=(ROOT/'mod/SlidingGates/42/media/scripts/SG_models_damage.txt').read_text()
ns['script']=script
end=next(i for i in range(index+1,len(tree.body)) if isinstance(tree.body[i],ast.For))
exec(compile(ast.Module(body=tree.body[index+1:end],type_ignores=[]),'<probe-init>','exec'),ns)
c,p,call,field,text,u2=(ns[k] for k in ('c','p','call','field','text','u2'))
for collection in ('models','animationMeshes','spriteModels'):
    c+=field('zombie/scripting/ScriptManager','instance','Lzombie/scripting/ScriptManager;')+text(collection)
    c+=call('PZGateDamageProbe','getField','(Ljava/lang/Object;Ljava/lang/String;)Ljava/lang/Object;',0xb8)
    c+=b'\xc0'+u2(p.cls('zombie/scripting/ScriptBucketCollection'))
    c+=field('zombie/scripting/ScriptLoadMode','Init','Lzombie/scripting/ScriptLoadMode;')
    c+=call('zombie/scripting/ScriptBucketCollection','LoadScripts','(Lzombie/scripting/ScriptLoadMode;)V')
for kind,name in re.findall(r'\b(model|spriteModel)\s+(\w+)\s*\{',script):
    c+=field('zombie/scripting/ScriptManager','instance','Lzombie/scripting/ScriptManager;')+text('Base.'+name)
    method,cls=('getModelScript','zombie/scripting/objects/ModelScript') if kind=='model' else ('getSpriteModel','zombie/iso/SpriteModel')
    c+=call('zombie/scripting/ScriptManager',method,'(Ljava/lang/String;)L'+cls+';')
    c+=call('java/util/Objects','requireNonNull','(Ljava/lang/Object;)Ljava/lang/Object;',0xb8)+b'\x57'
c+=b'\xb1';p.method('main','([Ljava/lang/String;)V',c,9);p.save('PZGateDamageProbe')
GAME,OUT=ns['GAME'],ns['OUT']
run=subprocess.run([str(GAME/'jre64/bin/java.exe'),'-Djava.awt.headless=true',f'-Duser.home={OUT}',
                    '-cp',f'{OUT};{GAME}/projectzomboid.jar','PZGateDamageProbe'],cwd=ROOT,capture_output=True,text=True)
(ROOT/'research/render-audit/gate-damage-native.txt').write_text(run.stdout+run.stderr)
assert run.returncode==0,run.stdout+run.stderr
print('PASS installed B42 parser: 36 model scripts and 144 spriteModels')
