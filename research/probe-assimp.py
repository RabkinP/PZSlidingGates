"""Build a tiny JVM probe without installing a JDK; run the game's own JNI importer.

Outputs first-vertex position, normal and UV for comparison with GLB accessors.
Class version 49 uses straight-line bytecode; no engine initialization is needed.
"""
import struct
from pathlib import Path

ROOT=Path(__file__).resolve().parent/'render-audit'/'probe'
ROOT.mkdir(parents=True,exist_ok=True)
def u2(n): return struct.pack('>H',n)
def u4(n): return struct.pack('>I',n)

class ClassFile:
    def __init__(self,name,parent):
        self.pool=[]; self.methods=[]
        self.this=self.cls(name); self.parent=self.cls(parent)
    def add(self,data):
        self.pool.append(data); return len(self.pool)
    def utf(self,s):
        b=s.encode(); return self.add(b'\x01'+u2(len(b))+b)
    def cls(self,s): return self.add(b'\x07'+u2(self.utf(s)))
    def string(self,s): return self.add(b'\x08'+u2(self.utf(s)))
    def ref(self,owner,name,desc,tag=10):
        c=self.cls(owner); n=self.utf(name); d=self.utf(desc)
        nt=self.add(b'\x0c'+u2(n)+u2(d))
        return self.add(bytes([tag])+u2(c)+u2(nt))
    def method(self,name,desc,code,access=1):
        n=self.utf(name); d=self.utf(desc); a=self.utf('Code')
        body=u2(12)+u2(4)+u4(len(code))+code+u2(0)+u2(0)
        self.methods.append(u2(access)+u2(n)+u2(d)+u2(1)+u2(a)+u4(len(body))+body)
    def save(self,name):
        raw=b'\xca\xfe\xba\xbe'+u2(0)+u2(49)+u2(len(self.pool)+1)
        raw+=b''.join(self.pool)+u2(0x21)+u2(self.this)+u2(self.parent)
        raw+=u2(0)+u2(0)+u2(len(self.methods))+b''.join(self.methods)+u2(0)
        (ROOT/(name+'.class')).write_bytes(raw)

loader=ClassFile('PZNativeLoader','jassimp/JassimpLibraryLoader')
loader.method('<init>','()V',b'\x2a\xb7'+u2(loader.ref('jassimp/JassimpLibraryLoader','<init>','()V'))+b'\xb1')
loader.method('loadLibrary','()V',b'\x13'+u2(loader.string(r'E:\SteamLibrary\steamapps\common\ProjectZomboid\jassimp64.dll'))+b'\xb8'+u2(loader.ref('java/lang/System','load','(Ljava/lang/String;)V'))+b'\xb1')
loader.save('PZNativeLoader')

probe=ClassFile('PZImportProbe','java/lang/Object')
code=b'\xbb'+u2(probe.cls('PZNativeLoader'))+b'\x59\xb7'+u2(probe.ref('PZNativeLoader','<init>','()V'))
code+=b'\xb8'+u2(probe.ref('jassimp/Jassimp','setLibraryLoader','(Ljassimp/JassimpLibraryLoader;)V'))
code+=b'\xb2'+u2(probe.ref('jassimp/AiPostProcessSteps','MAKE_LEFT_HANDED','Ljassimp/AiPostProcessSteps;',9))
code+=b'\xb8'+u2(probe.ref('java/util/EnumSet','of','(Ljava/lang/Enum;)Ljava/util/EnumSet;'))+b'\x4e'
for flag in ['FIND_INSTANCES','LIMIT_BONE_WEIGHTS','TRIANGULATE','OPTIMIZE_MESHES','REMOVE_REDUNDANT_MATERIALS','JOIN_IDENTICAL_VERTICES']:
    code+=b'\x2d\xb2'+u2(probe.ref('jassimp/AiPostProcessSteps',flag,'Ljassimp/AiPostProcessSteps;',9))
    code+=b'\xb6'+u2(probe.ref('java/util/EnumSet','add','(Ljava/lang/Object;)Z'))+b'\x57'
code+=b'\x2a\x03\x32\x2d\xb8'+u2(probe.ref('jassimp/Jassimp','importFile','(Ljava/lang/String;Ljava/util/Set;)Ljassimp/AiScene;'))+b'\x4c'
code+=b'\x2b\xb6'+u2(probe.ref('jassimp/AiScene','getMeshes','()Ljava/util/List;'))+b'\x03\xb9'+u2(probe.ref('java/util/List','get','(I)Ljava/lang/Object;',11))+b'\x02\x00\xc0'+u2(probe.cls('jassimp/AiMesh'))+b'\x4d'
for name in ['getNumVertices','getNumFaces']:
    code+=b'\xb2'+u2(probe.ref('java/lang/System','out','Ljava/io/PrintStream;',9))+b'\x2c\xb6'+u2(probe.ref('jassimp/AiMesh',name,'()I'))
    code+=b'\xb6'+u2(probe.ref('java/io/PrintStream','println','(I)V'))
for name in ['getPositionX','getPositionY','getPositionZ','getNormalX','getNormalY','getNormalZ','getTexCoordU','getTexCoordV']:
    code+=b'\xb2'+u2(probe.ref('java/lang/System','out','Ljava/io/PrintStream;',9))+b'\x2c\x03'
    desc='(I)F'
    if name.startswith('getTex'): code+=b'\x03'; desc='(II)F'
    code+=b'\xb6'+u2(probe.ref('jassimp/AiMesh',name,desc))+b'\xb6'+u2(probe.ref('java/io/PrintStream','println','(F)V'))
code+=b'\xb1'
probe.method('main','([Ljava/lang/String;)V',code,9)
probe.save('PZImportProbe')
print(ROOT)
