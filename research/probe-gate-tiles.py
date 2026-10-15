"""Run the installed game's real .pack metadata/PNG and spriteModels parsers headlessly.

Uses the existing small classfile writer, so no JDK/compiler installation is needed.
Does not initialize OpenGL, load a save, or modify the running game.
"""
import ast
import struct
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GAME = Path(r'E:/SteamLibrary/steamapps/common/ProjectZomboid')
OUT = REPO/'research/render-audit/probe'
OUT.mkdir(parents=True, exist_ok=True)
source = ast.parse((REPO/'research/probe-assimp.py').read_text())
definitions = [node for node in source.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))]
namespace = dict(struct=struct, ROOT=OUT)
exec(compile(ast.Module(body=definitions, type_ignores=[]), '<classfile-writer>', 'exec'), namespace)
ClassFile, u2 = namespace['ClassFile'], namespace['u2']
p = ClassFile('PZGateTilesProbe', 'java/lang/Object')


def call(owner, name, signature, opcode=0xb6):
    return bytes([opcode])+u2(p.ref(owner, name, signature))


def field(owner, name, signature, opcode=0xb2):
    return bytes([opcode])+u2(p.ref(owner, name, signature, 9))


def text(s):
    return b'\x13'+u2(p.string(s))


def new(owner, signature='()V', args=b''):
    return b'\xbb'+u2(p.cls(owner))+b'\x59'+args+call(owner, '<init>', signature, 0xb7)


# Reflection helper for package-private metadata fields.
c=b'\x2a'+call('java/lang/Object','getClass','()Ljava/lang/Class;')+b'\x2b'
c+=call('java/lang/Class','getDeclaredField','(Ljava/lang/String;)Ljava/lang/reflect/Field;')+b'\x4e\x2d\x04'
c+=call('java/lang/reflect/Field','setAccessible','(Z)V')+b'\x2d\x2a\x2c'
c+=call('java/lang/reflect/Field','set','(Ljava/lang/Object;Ljava/lang/Object;)V')+b'\xb1'
p.method('setField','(Ljava/lang/Object;Ljava/lang/String;Ljava/lang/Object;)V',c,9)
c=b'\x2a'+call('java/lang/Object','getClass','()Ljava/lang/Class;')+b'\x2b'
c+=call('java/lang/Class','getDeclaredField','(Ljava/lang/String;)Ljava/lang/reflect/Field;')+b'\x4e\x2d\x04'
c+=call('java/lang/reflect/Field','setAccessible','(Z)V')+b'\x2d\x2a'
c+=call('java/lang/reflect/Field','get','(Ljava/lang/Object;)Ljava/lang/Object;')+b'\xb0'
p.method('getField','(Ljava/lang/Object;Ljava/lang/String;)Ljava/lang/Object;',c,9)
c=b'\x2a'+call('java/lang/Object','getClass','()Ljava/lang/Class;')+b'\x2b\x03\xbd'+u2(p.cls('java/lang/Class'))
c+=call('java/lang/Class','getDeclaredMethod','(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;')+b'\x4e\x2d\x04'
c+=call('java/lang/reflect/Method','setAccessible','(Z)V')+b'\x2d\x2a\x03\xbd'+u2(p.cls('java/lang/Object'))
c+=call('java/lang/reflect/Method','invoke','(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;')+b'\x57\xb1'
p.method('invokeNoArg','(Ljava/lang/Object;Ljava/lang/String;)V',c,9)

# Invoke SpriteModelsFile.parseFile(String) directly so parse errors cannot be swallowed by read().
c=b'\x2a'+call('java/lang/Object','getClass','()Ljava/lang/Class;')+b'\x2b\x04\xbd'+u2(p.cls('java/lang/Class'))
c+=b'\x59\x03\x13'+u2(p.cls('java/lang/String'))+b'\x53'
c+=call('java/lang/Class','getDeclaredMethod','(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;')+b'\x4e\x2d\x04'
c+=call('java/lang/reflect/Method','setAccessible','(Z)V')+b'\x2d\x2a\x04\xbd'+u2(p.cls('java/lang/Object'))+b'\x59\x03\x2c\x53'
c+=call('java/lang/reflect/Method','invoke','(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;')+b'\x57\xb1'
p.method('invokeString','(Ljava/lang/Object;Ljava/lang/String;Ljava/lang/String;)V',c,9)

c=field('zombie/ZomboidFileSystem','instance','Lzombie/ZomboidFileSystem;')
c+=field('zombie/ZomboidFileSystem','base','Lzombie/ZomboidFileSystem$PZFolder;',0xb4)
c+=new('java/io/File','(Ljava/lang/String;)V',text(str(GAME)))
c+=call('zombie/ZomboidFileSystem$PZFolder','set','(Ljava/io/File;)V')
c+=new('zombie/fileSystem/TexturePackDevice','(Ljava/lang/String;I)V',text('SG_GatesPreview')+b'\x03')+b'\x4c'
c+=b'\x2b'+text('filename')+text(str(REPO/'mod/SlidingGates/42/media/texturepacks/SG_GatesPreview.pack'))
c+=call('PZGateTilesProbe','setField','(Ljava/lang/Object;Ljava/lang/String;Ljava/lang/Object;)V',0xb8)
c+=new('zombie/fileSystem/FileSystem$TexturePackTextures')+b'\x4d\x2b\x2c'
c+=call('zombie/fileSystem/TexturePackDevice','getSubTextureInfo','(Lzombie/fileSystem/FileSystem$TexturePackTextures;)V')
for i in range(328):
    c+=b'\x2c'+text(f'sg_gates_preview_01_{i}')+call('java/util/HashMap','get','(Ljava/lang/Object;)Ljava/lang/Object;')
    c+=call('java/util/Objects','requireNonNull','(Ljava/lang/Object;)Ljava/lang/Object;',0xb8)+b'\x57'
c+=field('java/lang/System','out','Ljava/io/PrintStream;')+b'\x2c'+call('java/util/HashMap','size','()I')
c+=call('java/io/PrintStream','println','(I)V')
c+=b'\x2b'+text('SG_GatesPreview_0')+b'\x01'+call('zombie/fileSystem/TexturePackDevice','createStream','(Ljava/lang/String;Ljava/io/InputStream;)Ljava/io/InputStream;')
c+=call('javax/imageio/ImageIO','read','(Ljava/io/InputStream;)Ljava/awt/image/BufferedImage;',0xb8)+b'\x4e'
for getter in ['getWidth','getHeight']:
    c+=field('java/lang/System','out','Ljava/io/PrintStream;')+b'\x2d'+call('java/awt/image/BufferedImage',getter,'()I')
    c+=call('java/io/PrintStream','println','(I)V')
c+=b'\x04'+field('zombie/network/GameServer','server','Z',0xb3)
c+=field('zombie/iso/IsoWorld','instance','Lzombie/iso/IsoWorld;')
c+=field('zombie/iso/sprite/IsoSpriteManager','instance','Lzombie/iso/sprite/IsoSpriteManager;')
c+=text(str(REPO/'mod/SlidingGates/42/media/SG_GatesPreview.tiles'))+b'\x11'+struct.pack('>h',6842)
c+=call('zombie/iso/IsoWorld','LoadTileDefinitions','(Lzombie/iso/sprite/IsoSpriteManager;Ljava/lang/String;I)V')
for i in range(328):
    c+=field('zombie/iso/sprite/IsoSpriteManager','instance','Lzombie/iso/sprite/IsoSpriteManager;')
    c+=field('zombie/iso/sprite/IsoSpriteManager','namedMap','Ljava/util/HashMap;',0xb4)
    c+=text(f'sg_gates_preview_01_{i}')+call('java/util/HashMap','get','(Ljava/lang/Object;)Ljava/lang/Object;')
    c+=call('java/util/Objects','requireNonNull','(Ljava/lang/Object;)Ljava/lang/Object;',0xb8)+b'\x57'
c+=new('zombie/iso/SpriteModelsFile')+b'\x4c\x2b'+text('parseFile')
# Read the file in Java: its text exceeds the 65535-byte class constant limit.
c+=new('java/lang/String','([B)V',new('java/io/File','(Ljava/lang/String;)V',text(str(REPO/'mod/SlidingGates/common/media/spriteModels.txt')))
    +call('java/io/File','toPath','()Ljava/nio/file/Path;')+call('java/nio/file/Files','readAllBytes','(Ljava/nio/file/Path;)[B',0xb8))
c+=call('PZGateTilesProbe','invokeString','(Ljava/lang/Object;Ljava/lang/String;Ljava/lang/String;)V',0xb8)
c+=b'\x2b'+text('tilesets')+call('PZGateTilesProbe','getField','(Ljava/lang/Object;Ljava/lang/String;)Ljava/lang/Object;',0xb8)
c+=b'\xc0'+u2(p.cls('java/util/ArrayList'))+b'\x03'+call('java/util/ArrayList','get','(I)Ljava/lang/Object;')
c+=text('initSprites')+call('PZGateTilesProbe','invokeNoArg','(Ljava/lang/Object;Ljava/lang/String;)V',0xb8)
for i in range(328):
    c+=field('zombie/iso/sprite/IsoSpriteManager','instance','Lzombie/iso/sprite/IsoSpriteManager;')
    c+=field('zombie/iso/sprite/IsoSpriteManager','namedMap','Ljava/util/HashMap;',0xb4)
    c+=text(f'sg_gates_preview_01_{i}')+call('java/util/HashMap','get','(Ljava/lang/Object;)Ljava/lang/Object;')
    c+=b'\xc0'+u2(p.cls('zombie/iso/sprite/IsoSprite'))
    c+=field('zombie/iso/sprite/IsoSprite','spriteModel','Lzombie/iso/SpriteModel;',0xb4)
    c+=call('java/util/Objects','requireNonNull','(Ljava/lang/Object;)Ljava/lang/Object;',0xb8)+b'\x57'
c+=field('java/lang/System','out','Ljava/io/PrintStream;')+text('PASS installed pack metadata, PNG decoder, tile definitions and all 328 spriteModel bindings')
c+=call('java/io/PrintStream','println','(Ljava/lang/String;)V')+b'\xb1'
p.method('main','([Ljava/lang/String;)V',c,9)
p.save('PZGateTilesProbe')
run=subprocess.run([str(GAME/'jre64/bin/java.exe'),'-Djava.awt.headless=true',f'-Duser.home={OUT}',
                    '-cp',f'{OUT};{GAME}/projectzomboid.jar','PZGateTilesProbe'],
                   cwd=REPO, capture_output=True, text=True)
print(run.stdout, end='')
print(run.stderr, end='')
if run.returncode:
    raise SystemExit(run.returncode)
assert '\n328\n1024\n10496\n' in '\n'+run.stdout.replace('\r','')
report=REPO/'research/render-audit/gate-tiles-native.txt'
report.write_text(run.stdout+run.stderr)
