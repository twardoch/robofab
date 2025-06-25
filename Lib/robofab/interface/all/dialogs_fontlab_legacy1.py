"""

Dialogs for FontLab < 5.1.

This one should be loaded for various platforms, using dialogKit
http://www.robofab.org/tools/dialogs.html

Modified: 2017-11-20 by Adam Twardoch

"""

from FL import *

# 2017-11-20 by Adam Twardoch: dialogKit is no longer used here
# from dialogKit import ModalDialog, Button, TextBox, EditText

__all__ = [
    # "AskString",
    # "AskYesNoCancel",
    # "FindGlyph",
    "GetFile",
    "GetFolder",
    # "Message",
    # "OneList",
    # "PutFile",
    # "SearchList",
    # "SelectFont",
    # "SelectGlyph",
    # "TwoChecks",
    # "TwoFields",
    "ProgressBar",
]


def GetFile(
    message=None,
    title=None,
    directory=None,
    fileName=None,
    allowsMultipleSelection=False,
    fileTypes=[],
):
    # fileTypes is converted into strFilter in a way compatible with FLS5 Mac, FLS5 Win and FLVI Mac/Win
    # FLVI uses ';'-separated list of filters, FLS5 uses the same list but inside '||'
    if len(fileTypes):
        listFilter = [f"*.{ext};*.{ext.upper()};" for ext in fileTypes]
    else:
        listFilter = ["*.*;"]
    strFilter = "{}|{}|".format("".join(listFilter), "".join(listFilter))
    defaultExt = ""
    # using fontlab's internal file dialogs
    return fl.GetFileName(1, defaultExt, message, strFilter)


def GetFolder(message=None, title=None, directory=None, allowsMultipleSelection=False):
    # using fontlab's internal file dialogs
    if message is None:
        message = ""
    if title is None:
        title = ""
    return fl.GetPathName(title, message)


def PutFile(message=None, fileName=None):
    # using fontlab's internal file dialogs
    # message is not used
    if message is None:
        message = ""
    if fileName is None:
        fileName = ""
    defaultExt = ""
    return fl.GetFileName(0, defaultExt, fileName, "")


class ProgressBar:
    def __init__(self, title="RoboFab...", ticks=0, label=""):
        self._tickValue = 1
        fl.BeginProgress(title, ticks)

    def getCurrentTick(self):
        return self._tickValue

    def tick(self, tickValue=None):
        if not tickValue:
            tickValue = self._tickValue
        fl.TickProgress(tickValue)
        self._tickValue = tickValue + 1

    def label(self, label):
        pass

    def close(self):
        fl.EndProgress()
