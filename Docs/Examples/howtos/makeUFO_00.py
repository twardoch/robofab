# robofab manual
# Makeufo howto
# Makeufo from a font binary examples

from robofab.interface.all.dialogs import GetFile, PutFile
from robofab.tools.toolsAll import fontToUFO

srcPath = GetFile("Select the source")
dstPath = PutFile("Save as...")

fontToUFO(srcPath, dstPath)
