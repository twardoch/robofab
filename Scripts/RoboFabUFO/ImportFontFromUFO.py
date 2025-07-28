#FLM: Import .ufo File into FontLab

from robofab.interface.all.dialogs import GetFileOrFolder
from robofab.world import NewFont

path = GetFileOrFolder("Please select a .ufo")
if path is not None:
	font = NewFont()
	font.readUFO(path, doProgress=True)
	font.update()
	print 'DONE!'
