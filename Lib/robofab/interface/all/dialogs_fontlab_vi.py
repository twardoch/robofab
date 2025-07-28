"""

Dialogs for FontLab VI
Added: 2017-11-20 by Adam Twardoch

"""

# The "butchered version of vanilla.dialogs" implementation of GetFileOrFolder
# works on FontLab VI for Mac but cannot work on Windows, so we're using GetFile instead
# import sys
# if sys.platform in ('mac', 'darwin'):
#    from robofab.interface.all.dialogs_fontlab_legacy2 import GetFileOrFolder
# else:
# 'fl' FontLab implementation works in FontLab VI
from robofab.interface.all.dialogs_fontlab_legacy1 import GetFile
from robofab.interface.all.dialogs_fontlab_legacy1 import \
    GetFile as GetFileOrFolder
from robofab.interface.all.dialogs_fontlab_legacy1 import GetFolder, PutFile
# 'fl' FontLab implementation works in FontLab VI
from robofab.interface.all.dialogs_legacy import (AskString, AskYesNoCancel,
                                                  FindGlyph, Message, OneList,
                                                  ProgressBar, SearchList,
                                                  SelectFont, SelectGlyph,
                                                  TwoChecks, TwoFields)

__all__ = [
    "AskString",
    "AskYesNoCancel",
    "FindGlyph",
    "GetFile",
    "GetFolder",
    "GetFileOrFolder",
    "Message",
    "OneList",
    "PutFile",
    "SearchList",
    "SelectFont",
    "SelectGlyph",
    "TwoChecks",
    "TwoFields",
    "ProgressBar",
]
