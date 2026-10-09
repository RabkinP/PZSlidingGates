"""Exercise remote eligibility through the installed vanilla rename menu/dialog."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
tree = ast.parse((ROOT/'tests/test_gate_drive.py').read_text())
prefix = tree.body[:next(i for i,n in enumerate(tree.body) if isinstance(n,ast.For))]
ns = {'__file__':str(ROOT/'tests/test_gate_drive.py')}
exec(compile(ast.Module(body=prefix,type_ignores=[]),'<drive-fixture>','exec'),ns)
lua = ns['runtime']()
native = Path(r'E:/SteamLibrary/steamapps/common/ProjectZomboid/media/lua/client/ISUI/ISInventoryPaneContextMenu.lua').read_text()
rename_start = 'function ISInventoryPaneContextMenu:onRenameBagClick'
rename_callback = rename_start + native.split(rename_start,1)[1].split('ISInventoryPaneContextMenu.dryMyself',1)[0]
lua.execute("ISInventoryPaneContextMenu={}; local MAXIMUM_RENAME_LENGTH=28\n" + rename_callback)
for start,end in (
    ('ISInventoryPaneContextMenu.onRenameBag = function','ISInventoryPaneContextMenu.onRenameFood = function'),
    ('ISInventoryPaneContextMenu.doMoreContextMenu = function','ISInventoryPaneContextMenu.doDebugContextMenu = function')):
    lua.execute(start+native.split(start,1)[1].split(end,1)[0])
lua.execute(r'''
require 'SG_GateRemote'
package.preload['ISUI/ISInventoryPaneContextMenu']=function() return true end
require 'SG_GateRemoteRename'
function getText(key) return key end
p=character(square(30,20,0));function p:getPlayerNum() return 0 end
function getSpecificPlayer() return p end
id=SGGate.build(square(30,20,0),'chainlink');drive=SGGate.installDrive(id,{})
remote=add(p.inv,SGGateRemote.itemType)
assert(SGGateRemote.pair(p,id,SGGate.findRole(id,'leaf').md.sgInstance,remote.id,drive.md.sgDriveIdentity))
function remote:setName(name) self.name=name end
function remote:getName() return self.name or self.kind end
function remote:setCustomName(value) self.custom=value end
JoypadState={players={}}
refreshes=0
local panel={refreshBackpacks=function() refreshes=refreshes+1 end}
function getPlayerData() return {playerInventory=panel,lootInventory=panel} end
HaloTextHelper={addBadText=function() rejected=true end}
ISTextBox={new=function(_,x,y,w,h,text,name,target,callback,player,character,item)
 modal={callback=callback,item=item,entry={getInternalText=function() return entered end,
 getText=function() return entered end},initialise=function() end,addToUIManager=function() end}
 return modal end}
local function context()
 local c={options={}}
 function c:getNew() return context() end
 function c:addOption(label,target,callback,...)
  local o={label=label,target=target,callback=callback,args={...}}
  table.insert(self.options,o);return o
 end
 function c:addSubMenu(option,sub) option.sub=sub end
 return c
end
for _,items in ipairs({{remote},{{items={remote,remote}}}}) do
 local c=context()
 ISInventoryPaneContextMenu.doMoreContextMenu(c,{}, {},p,items,1)
 assert(#c.options==1 and c.options[1].label=='ContextMenu_More')
 local option=c.options[1].sub.options[1]
 assert(option.label=='ContextMenu_RenameBag' and option.target==remote)
 assert(option.callback==ISInventoryPaneContextMenu.onRenameBag)
 option.callback(option.target,unpack(option.args))
 assert(modal.item==remote and modal.callback==ISInventoryPaneContextMenu.onRenameBagClick)
end
entered='Home gate'
ISInventoryPaneContextMenu:onRenameBagClick({internal='OK',parent=modal},p,remote)
assert(remote.name=='Home gate' and remote.custom and remote.syncs==1 and refreshes==2)
assert(SGGateRemote.linked(remote,drive))
entered=string.rep('x',29);rejected=false
ISInventoryPaneContextMenu:onRenameBagClick({internal='OK',parent=modal},p,remote)
assert(rejected and remote.name=='Home gate' and remote.syncs==1)
entered='';ISInventoryPaneContextMenu:onRenameBagClick({internal='OK',parent=modal},p,remote)
entered='Changed';ISInventoryPaneContextMenu:onRenameBagClick({internal='CANCEL',parent=modal},p,remote)
assert(remote.name=='Home gate' and remote.syncs==1 and SGGateRemote.linked(remote,drive))
local other=add(p.inv,'Base.Remote')
local c=context();ISInventoryPaneContextMenu.doMoreContextMenu(c,{}, {},p,{other},1);assert(#c.options==0)
c=context();ISInventoryPaneContextMenu.doMoreContextMenu(c,{}, {},p,{remote,other},2);assert(#c.options==0)
-- Existing vanilla eligibility wins; do not replace another mod's chosen item.
c=context();ISInventoryPaneContextMenu.doMoreContextMenu(c,{canBeRenamed=other},{},p,{remote},1)
assert(c.options[1].sub.options[1].target==other)
''')
print('PASS native remote rename: More menu, grouped selection, vanilla dialog, name synchronization, length/cancel, pairing preservation and other-item compatibility')
