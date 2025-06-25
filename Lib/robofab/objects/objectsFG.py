"""UFO implementation for the FontGate objects as used in FontLab VI"""

import datetime
import os
import sys
from warnings import warn

import fontgate
from fontgate import *
from StringIO import StringIO

from robofab import RoboFabError, ufoLib
from robofab.misc import arrayTools
from robofab.objects.objectsBase import (CORNER, CURVE, LINE, MOVE, OFFCURVE,
                                         QCURVE, BaseAnchor, BaseBPoint,
                                         BaseComponent, BaseContour,
                                         BaseFeatures, BaseFont, BaseGlyph,
                                         BaseGroups, BaseGuide, BaseInfo,
                                         BaseKerning, BaseLib, BasePoint,
                                         BasePostScriptFontHintValues,
                                         BasePostScriptGlyphHintValues,
                                         BaseSegment, _box, absoluteBCPIn,
                                         absoluteBCPOut, addPt,
                                         postScriptHintDataLibKey,
                                         relativeBCPIn, relativeBCPOut,
                                         roundPt)
from robofab.pens.fgPen import FGPointContourPen, FGPointPen
from robofab.plistlib import Data, Dict, readPlist, writePlist
from robofab.tools.fontlabFeatureSplitter import splitFeaturesForFontLab

try:
        set
except NameError:
        from sets import Set as set

import imp

try:
    a=sys.modules['fontlab']
    a=None
    _fgWorldModuleAvailable = True
    #print "The fontlab module is available"
    import fontlab
except KeyError:
    try:
        imp.find_module('fontlab')
        _fgWorldModuleAvailable = True
        #print "The fontlab module is available"
        import fontlab
    except ImportError:
        _fgWorldModuleAvailable = False
        #print "The fontlab module is not available here"


# local encoding
if os.name in ["mac", "posix"]:
        LOCAL_ENCODING = "macroman"
else:
        LOCAL_ENCODING = "latin-1"

_IN_UFO_EXPORT = False

# a list of attributes that are to be copied when copying a glyph.
# this is used by glyph.copy and font.insertGlyph
GLYPH_COPY_ATTRS = [
        "name",
        "width",
        "unicodes",
        "note",
        "lib",
        ]



class PostScriptFontHintValues(BasePostScriptFontHintValues):
        """	Wrapper for font-level PostScript hinting information for FontGate.
                Blues values, stem values.
        """
        def __init__(self, font=None):          # , impliedMasterIndex=0
                self._object = font.naked()
                #self._masterIndex = impliedMasterIndex

        def copy(self):
                from robofab.objects.objectsRF import \
                    PostScriptFontHintValues as _PostScriptFontHintValues
                return _PostScriptFontHintValues(data=self.asDict())


class PostScriptGlyphHintValues(BasePostScriptGlyphHintValues):
        """	Wrapper for glyph-level PostScript hinting information for FontGate.
                vStems, hStems.
        """
        def __init__(self, glyph=None):
                self._object = glyph.naked()

        def copy(self):
                from robofab.objects.objectsRF import \
                    PostScriptGlyphHintValues as _PostScriptGlyphHintValues
                return _PostScriptGlyphHintValues(data=self.asDict())

        def _getVHints(self):
                hintslist = self._object.hints.getAsList(False)
                hintslist.sort()
                return hintslist

        def _setVHints(self, values):
                self._object.hints.removeHV(False)
                if values is None:
                        # just clearing it then
                        return
                values.sort()
                self._object.hints.setFromList(False, values)

        def _getHHints(self):
                hintslist = self._object.hints.getAsList(True)
                hintslist.sort()
                return hintslist

        def _setHHints(self, values):
                self._object.hints.removeHV(True)
                if values is None:
                        # just clearing it then
                        return
                values.sort()
                self._object.hints.setFromList(True, values)

        vHints = property(_getVHints, _setVHints, doc="postscript hints: vertical hint zones")
        hHints = property(_getHHints, _setHHints, doc="postscript hints: horizontal hint zones")



def _flToRFSegmentType(segmentType):
        if segmentType == 'Move':
            return MOVE
        if segmentType == 'On':
            return LINE
        if segmentType == 'Curve':
            return CURVE
        if segmentType == 'Off':
            return OFFCURVE
        return None

def _rfToFLSegmentType(segmentType):
    if segmentType == MOVE:
        return 'Move'
    if segmentType == LINE:
        return 'On'
    if segmentType == CURVE:
        return 'Curve'
    if segmentType == OFFCURVE:
        return 'Off'
    return None

def _scalePointFromCenter((pointX, pointY), (scaleX, scaleY), (centerX, centerY)):
        ogCenter = (centerX, centerY)
        scaledCenter = (centerX * scaleX, centerY * scaleY)
        shiftVal = (scaledCenter[0] - ogCenter[0], scaledCenter[1] - ogCenter[1])
        scaledPointX = (pointX * scaleX) - shiftVal[0]
        scaledPointY = (pointY * scaleY) - shiftVal[1]
        return (scaledPointX, scaledPointY)



def CurrentFont():
    """Return a RoboFab font object for the currently selected font."""
    if _fgWorldModuleAvailable:
        f = fontlab.CurrentFont()
        if f is not None:
            return RFont(f)
    return None

def CurrentGlyph():
    """Return a RoboFab glyph object for the currently selected glyph."""
    if _fgWorldModuleAvailable:
        f = fontlab.CurrentFont()
        if f is not None:
            g = fontlab.CurrentGlyph()
            if g is None:
                return None
            ff = RFont(f)
            return ff[g.name]
    return None

def AllFonts():
    """Return a list of all open fonts."""
    if _fgWorldModuleAvailable:
        _fgfonts = fontlab.AllFonts()
        fontCount = len(_fgfonts)
        all = []
        for index in xrange(fontCount):
            naked = _fgfonts[index]
            all.append(RFont(naked))
        return all
    return None

def OpenFont(path=None, note=None):
        """Open a font from a path."""
        if path == None:
                from robofab.interface.all.dialogs import GetFileOrFolder
                path = GetFileOrFolder(note)
        if path:
                if _fgWorldModuleAvailable:
                        fontlab.flItems().requestLoadingFont(path)
                        font = fontlab.CurrentFont()
                else:
                        fp = fgPackages(path)
                        font = fp[0]
                return RFont(font)
        return None

def NewFont(familyName=None, styleName=None):
        """Make a new font"""
        fp = fgPackages() # Was fgPackage
        font = fp[fp.create()] # Fix
        rf = RFont(font) # Fix
        if familyName is not None:
                rf.info.familyName = familyName
        if styleName is not None:
                rf.info.styleName = styleName
        return rf




#def getGlyphFromMask(g):
#        """Get a Fab glyph object for the data in the mask layer."""
#        from robofab.objects.objectsFL import RGlyph as FL_RGlyph
#        from robofab.objects.objectsRF import RGlyph as RF_RGlyph
#        n = g.naked()
#        mask = n.mask
#        fg = FL_RGlyph(mask)
#        rf = RF_RGlyph()
#        pen = rf.getPointPen()
#        fg.drawPoints(pen)
#        rf.width = g.width	# can we get to the mask glyph width without flipping the UI?
#        return rf
#
#def setMaskToGlyph(maskGlyph, targetGlyph, clear=True):
#        """Set the maskGlyph as a mask layer in targetGlyph.
#        maskGlyph is a FontGate or RoboFab RGlyph, orphaned or not.
#        targetGlyph is a FontGate RGLyph.
#        clear is a bool. False: keep the existing mask data, True: clear the existing mask data.
#        """
#        from robofab.objects.objectsFL import RGlyph as FL_RGlyph
#        from FL import Glyph as FL_NakedGlyph
#        flGlyph = FL_NakedGlyph()		# new, orphaned FL glyph
#        wrapped = FL_RGlyph(flGlyph)	# rf wrapper for FL glyph
#        if not clear:
#                # copy the existing mask data first
#                existingMask = getGlyphFromMask(targetGlyph)
#                if existingMask is not None:
#                        pen = FGPointContourPen(existingMask)
#                        existingMask.drawPoints(pen)
#        pen = FGPointContourPen(wrapped)
#        maskGlyph.drawPoints(pen)		# draw the data
#        targetGlyph.naked().mask = wrapped .naked()
#        targetGlyph.update()


def _normalizeLineEndings(s):
        return s.replace("\r\n", "\n").replace("\r", "\n")


class RFont(BaseFont):
        """RoboFab UFO wrapper for FontGate Font object"""

        _title = "FontGateFont"

        def __init__(self, font=None):
                BaseFont.__init__(self)
                if font is None:
                        fp = fgPackages()
                        font = fp[fp.create()]
                self._object = font
                self._supportHints = True

        def keys(self):
                return self._object.keys()

        def has_key(self, glyphName):
                return self._object.has_key(glyphName)

        __contains__ = has_key

        def __setitem__(self, glyphName, glyph):
                self._object[glyphName] = glyph.naked()

        def __cmp__(self, other):
                if not hasattr(other, '_object'):
                        return -1
                return self._compare(other)
        #	if self._object.file_name == other._object.file_name:
        #		# so, names match.
        #		# this will falsely identify two distinct "Untitled"
        #		# let's check some more
        #		return 0
        #	else:
        #		return -1


        def _get_psHints(self):
                h = PostScriptFontHintValues(self)
                h.setParent(self)
                return h

        psHints = property(_get_psHints, doc="font level postscript hint data")


        def _get_info(self):
                return RInfo(self._object)

        info = property(_get_info, doc="font info object")


        def _get_features(self):
                rf = RFeatures(self._object);
                rf.setParent(self)
                return rf

        features = property(_get_features, doc="features object")


        def _get_kerning(self):
                rk = RKerning(self._object)
                rk.setParent(self)
                return rk

        kerning = property(_get_kerning, doc="a kerning object")


        def _get_lib(self):
                return self._object.lib;

        def _set_lib(self, aDict):
                self._object.lib.update(aDict)

        lib = property(_get_lib, _set_lib, doc="font lib object")


        def _set_groups(self, aDict):
                g = RGroups({})
                g.setParent(self)
                g.update(aDict)

        def _get_groups(self):
                groups = self._object.groups.asDict()
                rg = RGroups(groups)
                rg.setParent(self)
                return rg

        groups = property(_get_groups, _set_groups, doc="a group object")



        #
        # attributes
        #

        def _get_path(self):
                return self._object.path

        path = property(_get_path, doc="path to the font")

        def _get_fileName(self):
                if self.path is None:
                        return None
                base, tail = os.path.split(self.path)
                return tail

        fileName = property(_get_fileName, doc="the font's file name")

        def _makeGlyphlist(self):
                # To allow iterations through Font.glyphs. Should become really big in fonts with lotsa letters.
                gl = []
                for c in self:
                        gl.append(c)
                return gl

        def _get_glyphs(self):
                return self._makeGlyphlist()

        glyphs = property(_get_glyphs, doc="A list of all glyphs in the font, to allow iterations through Font.glyphs")

        def update(self):
                """Don't forget to update the font when you are done."""
                # fl.UpdateFont(self.fontIndex)
                pass

        def save(self, path=None):
                """Save the font, path is required."""
                if not path:
                        if not self._object.path:
                                raise RoboFabError, "No destination path specified."
                        else:
                                path = self._object.path
                self._object.save(path)


        def close(self, save=False):
                """Close the font, saving is optional."""
                if save:
                        self.save()
                else:
                        self._object.modified = 0
                self._object = None

        #
        # rebuild FontGate internal caches
        #

        def update(self):
                self._object.update()


        def getGlyph(self, glyphName):
                # XXX may need to become private
                fgGlyph = self._object[glyphName]
                if fgGlyph is not None:
                        glyph = RGlyph(fgGlyph)
                        glyph.setParent(self)
                        return glyph
                return self.newGlyph(glyphName)

        def newGlyph(self, glyphName, clear=True, updateFont=False):
                """Make a new glyph."""
                """Make a new glyph if it doesn't already exist, return the glyph.
                font is either a FL Font or RF RFont object. If updateFont is True
                the (very slow) fl.UpdateFont function will be called.
                """
                if isinstance(glyphName, unicode):
                        glyphName = glyphName.encode(LOCAL_ENCODING)
                fgGlyph = self._object.createGlyph(glyphName, clear=clear)
                rg = RGlyph(fgGlyph)
                rg.setParent(self)
                return rg

        def insertGlyph(self, glyph, name=None):
                """Returns a new glyph that has been inserted into the font.
                name = another glyphname if you want to insert as with that."""
                from robofab.objects.objectsRF import RFont as _RFont
                from robofab.objects.objectsRF import RGlyph as _RGlyph
                oldGlyph = glyph
                if name is None:
                        name = oldGlyph.name
                # clear the destination glyph if it exists.
                if self.has_key(name):
                        self[name].clear()
                # get the parent for the glyph
                otherFont = oldGlyph.getParent()
                # in some cases we will use the native
                # FL method for appending a glyph.
                useNative = True
                testingNative = True
                while testingNative:
                        # but, maybe it is an orphan glyph.self._object = fontgateGlyph
                        # in that case we should not use the native method.
                        if otherFont is None:
                                useNative = False
                                testingNative = False
                        # or maybe the glyph is coming from a NoneLab font
                        if otherFont is not None:
                                if isinstance(otherFont, _RFont):
                                        useNative = False
                                        testingNative = False
                                # but, it could be a copied FL glyph
                                # which is a NoneLab glyph that
                                # has a FontGate font as the parent
                                elif isinstance(otherFont, RFont):
                                        useNative = False
                                        testingNative = False
                        # or, maybe the glyph is being replaced, in which
                        # case the native method should not be used
                        # since FL will destroy any references to the glyph
                        if self.has_key(name):
                                useNative = False
                                testingNative = False
                        # if the glyph contains components the native
                        # method should not be used since FL does
                        # not reference glyphs in components by
                        # name, but by index (!!!).
                        if len(oldGlyph.components) != 0:
                                useNative = False
                                testingNative = False
                        testingNative = False
                # finally, insert the glyph.
                if useNative:
                        font = self.naked()
                        otherFont = oldGlyph.getParent().naked()
                        self.naked().append(otherFont[name])
                        newGlyph = self.getGlyph(name)
                else:
                        newGlyph = self.newGlyph(name)
                        newGlyph.appendGlyph(oldGlyph)
                        for attr in GLYPH_COPY_ATTRS:
                                if attr == "name":
                                        value = name
                                else:
                                        value = getattr(oldGlyph, attr)
                                setattr(newGlyph, attr, value)
                if self._supportHints:
                        # now we need to transfer the hints from
                        # the old glyph to the new glyph. we'll do this
                        # via the dict to hint functions.
                        hintDict = {}
                        # if the glyph is a NoneLab glyph, then we need
                        # to extract the ps hints from the lib
                        if isinstance(oldGlyph, _RGlyph):
                                hintDict = oldGlyph.lib.get(postScriptHintDataLibKey, {})
                        # otherwise we need to extract the hint dict from the glyph
                        else:
                                hintDict = oldGlyph.naked().hints.getAsDict()
                        # now apply the hint data
                        if hintDict:
                                newGlyph.naked().hints.setFromDict(hintDict)
                        # delete any remaining hint data from the glyph lib
                        if newGlyph.lib.has_key(postScriptHintDataLibKey):
                                del newGlyph.lib[postScriptHintDataLibKey]
                return newGlyph

        def removeGlyph(self, glyphName):
                """remove a glyph from the font"""
                self._object.removeGlyph(glyphName)
                index = self._object.FindGlyph(glyphName)
                if index != -1:
                        del self._object[index]

        #
        # opentype
        #

        def getOTClasses(self):
                """Return all OpenType classes as a dict. Relies on properly formatted classes."""
                classes = {}
                c = self._object.ot_classes
                if c is None:
                        return classes
                c = c.replace('\r', '').replace('\n', '').split(';')
                for i in c:
                        if i.find('=') != -1:
                                value = []
                                i = i.replace(' = ', '=')
                                name = i.split('=')[0]
                                v = i.split('=')[1].replace('[', '').replace(']', '').split(' ')
                                #catch double spaces?
                                for j in v:
                                        if len(j) > 0:
                                                value.append(j)
                                classes[name] = value
                return classes

        def setOTClasses(self, dict):
                """Set all OpenType classes."""
                l = []
                for i in dict.keys():
                        l.append(''.join([i, ' = [', ' '.join(dict[i]), '];']))
                self._object.ot_classes = '\n'.join(l)

        def getOTClass(self, name):
                """Get a specific OpenType class."""
                classes = self.getOTClasses()
                return classes[name]

        def setOTClass(self, name, list):
                """Set a specific OpenType class."""
                classes = self.getOTClasses()
                classes[name] = list
                self.setOTClasses(classes)

        def getOTFeatures(self):
                """Return all OpenType features as a dict keyed by name.
                The value is a string of the text of the feature."""
                features = {}
                for i in self._object.features:
                        v = []
                        for j in i.value.replace('\r', '\n').split('\n'):
                                if j.find(i.tag) == -1:
                                        v.append(j)
                        features[i.tag] = '\n'.join(v)
                return features

        def setOTFeatures(self, dict):
                """Set all OpenType features in the font."""
                features= {}
                for i in dict.keys():
                        f = []
                        f.append('feature %s {'%i)
                        f.append(dict[i])
                        f.append('} %s;'%i)
                        features[i] = '\n'.join(f)
                self._object.features.clean()
                for i in features.keys():
                        self._object.features.append(Feature(i, features[i]))

        def getOTFeature(self, name):
                """return a specific OpenType feature."""
                features = self.getOTFeatures()
                return features[name]

        def setOTFeature(self, name, text):
                """Set a specific OpenType feature."""
                features = self.getOTFeatures()
                features[name] = text
                self.setOTFeatures(features)

        #
        # guides
        #

        def getGuides(self):
                """Return a list of wrapped guides in this RFont"""
                guides=[]
                for i in range(len(self._object.guides)):
                        g = RGuide(self._object.guides[i])
                        g.setParent(self)
                        guides.append(g)
                return guides

        def _get_guides(self):
                return self.getGuides()

        guides = property(_get_guides, doc="allow for iteration through font.guides")

        def appendHGuide(self, position, color=(0, 0, 0, 255), name=''):
                """Append a horizontal guide"""
                self._object.guides.append(position, horizontal=True, color=color, name=name)

        def appendVGuide(self, position, color=(0, 0, 0, 255), name=''):
                """Append a vertical guide"""
                self._object.guides.append(position, horizontal=False, color=color, name=name)

        def appendGuide(self, point0, point1, color=(0, 0, 0, 255), name=''):
                """Append a guide"""
                self._object.guides.append(point0, point1, color=color, name=name)

        def clearGuides(self):
                """Clear all guides."""
                self._object.guides.clean()

        def removeHGuide(self, position):
                """Remove a horizontal guide."""
                self._object.guides.removeHV(position, True)

        def removeVGuide(self, position):
                """Remove a vertical guide."""
                self._object.guides.removeHV(position, False)

        def removeGuide(self, point0, point1):
                """Remove a guide."""
                self._object.guides.remove(point0, point1)


        #
        # generators
        #

        def generate(self, outputType, path=None):
                """
                generate the font. outputType is the type of font to ouput.
                --Ouput Types:
                'pctype1'	:	PC Type 1 font (binary/PFB)
                'pcmm'		:	PC MultipleMaster font (PFB)
                'pctype1ascii'	:	PC Type 1 font (ASCII/PFA)
                'pcmmascii'	:	PC MultipleMaster font (ASCII/PFA)
                'unixascii'	:	UNIX ASCII font (ASCII/PFA)
                'mactype1'	:	Mac Type 1 font (generates suitcase  and LWFN file)
                'otfcff'		:	PS OpenType (CFF-based) font (OTF)
                'otfttf'		:	PC TrueType/TT OpenType font (TTF)
                'macttf'	:	Mac TrueType font (generates suitcase)
                'macttdfont'	:	Mac TrueType font (generates suitcase with resources in data fork)
                                        (doc adapted from http://dev.fontlab.net/flpydoc/)

                path can be a directory or a directory file name combo:
                path="DirectoryA/DirectoryB"
                path="DirectoryA/DirectoryB/MyFontName"
                if no path is given, the file will be output in the same directory
                as the vfb file. if no file name is given, the filename will be the
                vfb file name with the appropriate suffix.
                """
                outputType = outputType.lower()
                if not _flGenerateTypes.has_key(outputType):
                        raise RoboFabError, "%s output type is not supported"%outputType
                flOutputType, suffix = _flGenerateTypes[outputType]
                if path is None:
                        filePath, fileName = os.path.split(self.path)
                        fileName = fileName.replace('.vfb', '')
                else:
                        if os.path.isdir(path):
                                filePath = path
                                fileName = os.path.split(self.path)[1].replace('.vfb', '')
                        else:
                                filePath, fileName = os.path.split(path)
                if '.' in fileName:
                        raise RoboFabError, "filename cannot contain periods.", fileName
                fileName = '.'.join([fileName, suffix])
                finalPath = os.path.join(filePath, fileName)
                if isinstance(finalPath, unicode):
                        finalPath = finalPath.encode("utf-8")
                # generate is (oddly) an application level method
                # rather than a font level method. because of this,
                # the font must be the current font. so, make it so.
                fl.ifont = self.fontIndex
                fl.GenerateFont(flOutputType, finalPath)

        def writeUFO(self, path=None, doProgress=False, glyphNameToFileNameFunc=None,
                doHints=False, doInfo=True, doKerning=True, doGroups=True, doLib=True, doFeatures=False, glyphs=None, formatVersion=2):
                #from robofab.interface.all.dialogs import ProgressBar, Message
                # special glyph name to file name conversion
                if glyphNameToFileNameFunc is None:
                        glyphNameToFileNameFunc = self.getGlyphNameToFileNameFunc()
                        if glyphNameToFileNameFunc is None:
                                from robofab.tools.glyphNameSchemes import \
                                    glyphNameToShortFileName
                                glyphNameToFileNameFunc = glyphNameToShortFileName
                # get a valid path
                if not path:
                        if self.path is None:
                                # Message("Please save this font first before exporting to UFO...")
                                return
                        else:
                                path = ufoLib.makeUFOPath(self.path)
                # get the glyphs to export
                if glyphs is None:
                        glyphs = self.keys()
                # if the file exists, check the format version.
                # if the format version being written is different
                # from the format version of the existing UFO
                # and only some files are set to be written
                # raise an error.
                if os.path.exists(path):
                        if os.path.exists(os.path.join(path, "metainfo.plist")):
                                reader = ufoLib.UFOReader(path)
                                existingFormatVersion = reader.formatVersion
                                if formatVersion != existingFormatVersion:
                                        if False in [doInfo, doKerning, doGroups, doLib, doFeatures, set(glyphs) == set(self.keys())]:
                                                # Message("When overwriting an existing UFO with a different format version all files must be written.")
                                                return
                # the lib must be written if format version is 1
                if not doLib and formatVersion == 1:
                        # Message("The lib must be written when exporting format version 1.")
                        return
                # set up the progress bar
                nonGlyphCount = [doInfo, doKerning, doGroups, doLib, doFeatures].count(True)
                bar = None
                #if doProgress:
                #        bar = ProgressBar("Exporting UFO", nonGlyphCount + len(glyphs))
                # try writing
                try:
                        writer = ufoLib.UFOWriter(path, formatVersion=formatVersion)
                        ## We make a shallow copy if lib, since we add some stuff for export
                        ## that doesn't need to be retained in memory.
                        fontLib = dict(self.lib)
                        # write the font info
                        if doInfo:
                                global _IN_UFO_EXPORT
                                _IN_UFO_EXPORT = True
                                writer.writeInfo(self.info)
                                _IN_UFO_EXPORT = False
                                if bar:
                                        bar.tick()
                        # write the kerning
                        if doKerning:
                                writer.writeKerning(self.kerning.asDict())
                                if bar:
                                        bar.tick()
                        # write the groups
                        if doGroups:
                                writer.writeGroups(self.groups)
                                if bar:
                                        bar.tick()
                        # write the features
                        if doFeatures:
                                if formatVersion == 2:
                                        writer.writeFeatures(self.features.text)
                                else:
                                        self._writeOpenTypeFeaturesToLib(fontLib)
                                if bar:
                                        bar.tick()
                        # write the lib
                        if doLib:
                                ## Always export the postscript font hint values to the lib in format version 1
                                if formatVersion == 1:
                                        d = self.psHints.asDict()
                                        fontLib[postScriptHintDataLibKey] = d
                                ## Export the glyph order to the lib
                                glyphOrder = [nakedGlyph.name for nakedGlyph in self.naked()]
                                fontLib["public.glyphOrder"] = glyphOrder
                                if fontLib.has_key("org.robofab.glyphNameToFileNameFuncName"):
                                        del fontLib["org.robofab.glyphNameToFileNameFuncName"]
                                ## export the features
                                if doFeatures and formatVersion == 1:
                                        self._writeOpenTypeFeaturesToLib(fontLib)
                                        if bar:
                                                bar.tick()
                                writer.writeLib(fontLib)
                                if bar:
                                        bar.tick()
                        # write the glyphs
                        if glyphs:
                                glyphSet = writer.getGlyphSet(glyphNameToFileNameFunc)
                                count = nonGlyphCount
                                for nakedGlyph in self.naked():
                                        if nakedGlyph.name not in glyphs:
                                                continue
                                        glyph = RGlyph(nakedGlyph)
                                        if doHints:
                                                hintStuff = glyph.naked().hints.getAsDict()
                                                if hintStuff:
                                                        glyph.lib[postScriptHintDataLibKey] = hintStuff
                                        glyphSet.writeGlyph(glyph.name, glyph, glyph.drawPoints)
                                        # remove the hint dict from the lib
                                        if doHints and glyph.lib.has_key(postScriptHintDataLibKey):
                                                del glyph.lib[postScriptHintDataLibKey]
                                        if bar and not count % 10:
                                                bar.tick(count)
                                        count = count + 1
                                glyphSet.writeContents()
                # only blindly stop if the user says to
                except KeyboardInterrupt:
                        if bar:
                                bar.close()
                        bar = None
                # kill the bar
                if bar:
                        bar.close()

        def _writeOpenTypeFeaturesToLib(self, fontLib):
                # this should only be used for UFO format version 1
                flFont = self.naked()
                cls = flFont.ot_classes
                if cls is not None:
                        fontLib["org.robofab.opentype.classes"] = _normalizeLineEndings(cls).rstrip() + "\n"
                if flFont.features:
                        features = {}
                        order = []
                        for feature in flFont.features:
                                order.append(feature.tag)
                                features[feature.tag] = _normalizeLineEndings(feature.value).rstrip() + "\n"
                        fontLib["org.robofab.opentype.features"] = features
                        fontLib["org.robofab.opentype.featureorder"] = order

        def readUFO(self, path, doProgress=False,
                doHints=False, doInfo=True, doKerning=True, doGroups=True, doLib=True, doFeatures=False, glyphs=None):
                """read a .ufo into the font"""
                from robofab.pens.fgPen import FGPointPen

                # from robofab.interface.all.dialogs import ProgressBar
                # start up the reader
                reader = ufoLib.UFOReader(path)
                glyphSet = reader.getGlyphSet()
                # get a list of glyphs that should be imported
                if glyphs is None:
                        glyphs = glyphSet.keys()
                # set up the progress bar
                nonGlyphCount = [doInfo, doKerning, doGroups, doLib, doFeatures].count(True)
                bar = None
                #if doProgress:
                #        bar = ProgressBar("Importing UFO", nonGlyphCount + len(glyphs))
                # start reading
                try:
                        fontLib = reader.readLib()
                        # info
                        if doInfo:
                                reader.readInfo(self.info)
                                if bar:
                                        bar.tick()
                        # glyphs
                        count = 1
                        glyphOrder = self._getGlyphOrderFromLib(fontLib, glyphSet)
                        for glyphName in glyphOrder:
                                if glyphName not in glyphs:
                                        continue
                                glyph = self.newGlyph(glyphName, clear=True)
                                pen = FGPointPen(glyph)     # .naked()
                                glyphSet.readGlyph(glyphName=glyphName, glyphObject=glyph, pointPen=pen)
                                if doHints:
                                        hintData = glyph.lib.get(postScriptHintDataLibKey)
                                        if hintData:
                                                glyph.naked().hints.setFromDict(hintData)
                                        # now that the hints have been extracted from the glyph
                                        # there is no reason to keep the location in the lib.
                                        if glyph.lib.has_key(postScriptHintDataLibKey):
                                                del glyph.lib[postScriptHintDataLibKey]
                                if bar and not count % 10:
                                        bar.tick(count)
                                count = count + 1
                        # features
                        if doFeatures:
                                if reader.formatVersion == 1:
                                        self._readOpenTypeFeaturesFromLib(fontLib)
                                else:
                                        featureText = reader.readFeatures()
                                        self.features.text = featureText
                                if bar:
                                        bar.tick()
                        else:
                                # remove features stored in the lib
                                self._readOpenTypeFeaturesFromLib(fontLib, setFeatures=False)
                        # kerning
                        if doKerning:
                                self.kerning.clear()
                                self.kerning.update(reader.readKerning())
                                if bar:
                                        bar.tick()
                        # groups
                        if doGroups:
                                self.groups.clear()
                                self.groups.update(reader.readGroups())
                                if bar:
                                        bar.tick()
                        # hints in format version 1
                        if doHints and reader.formatVersion == 1:
                                self.psHints._loadFromLib(fontLib)
                        else:
                                # remove hint data stored in the lib
                                if fontLib.has_key(postScriptHintDataLibKey):
                                        del fontLib[postScriptHintDataLibKey]
                        # lib
                        if doLib:
                                self.lib = fontLib
                                if bar:
                                        bar.tick()
                        # update the font
                        self.update()
                # only blindly stop if the user says to
                except KeyboardInterrupt:
                        bar.close()
                        bar = None
                # kill the bar
                if bar:
                        bar.close()
                self._object.path = path

        def _getGlyphOrderFromLib(self, fontLib, glyphSet):
                key = "public.glyphOrder"
                glyphOrder = fontLib.get(key)
                if glyphOrder is None:
                        key = "org.robofab.glyphOrder"
                glyphOrder = fontLib.get(key)
                if glyphOrder is not None:
                        # no need to keep track if the glyph order in lib once the font is loaded.
                        del fontLib[key]
                        glyphNames = []
                        done = {}
                        for glyphName in glyphOrder:
                                if glyphName in glyphSet:
                                        glyphNames.append(glyphName)
                                        done[glyphName] = 1
                        allGlyphNames = glyphSet.keys()
                        allGlyphNames.sort()
                        for glyphName in allGlyphNames:
                                if glyphName not in done:
                                        glyphNames.append(glyphName)
                else:
                        glyphNames = glyphSet.keys()
                        glyphNames.sort()
                return glyphNames

        def _readOpenTypeFeaturesFromLib(self, fontLib, setFeatures=True):
                # setFeatures may be False. in this case, this method
                # should only clear the data from the lib.
                classes = fontLib.get("org.robofab.opentype.classes")
                if classes is not None:
                        del fontLib["org.robofab.opentype.classes"]
                        if setFeatures:
                                self.naked().ot_classes = classes
                features = fontLib.get("org.robofab.opentype.features")
                if features is not None:
                        order = fontLib.get("org.robofab.opentype.featureorder")
                        if order is None:
                                # for UFOs saved without the feature order, do the same as before.
                                order = features.keys()
                                order.sort()
                        else:
                                del fontLib["org.robofab.opentype.featureorder"]
                        del fontLib["org.robofab.opentype.features"]
                        #features = features.items()
                        orderedFeatures = []
                        for tag in order:
                                oneFeature = features.get(tag)
                                if oneFeature is not None:
                                        orderedFeatures.append((tag, oneFeature))
                        if setFeatures:
                                self.naked().features.clean()
                                for tag, src in orderedFeatures:
                                        self.naked().features.append(Feature(tag, src))



class RGlyph(BaseGlyph):
        """RoboFab wrapper for FL Glyph object"""

        _title = "FontGateGlyph"

        def __init__(self, fontgateGlyph):
                #BaseGlyph.__init__(self)
                if fontgateGlyph is None:
                        raise RoboFabError, "RGlyph: there's nothing to wrap!?"
                self._object = fontgateGlyph
                #self.lib = fontgateGlyph.lib
                self._contours = None

        def __getitem__(self, index):
                return self.contours[index]

        def __delitem__(self, index):
                self._object.deleteContour(index)
                self._invalidateContours()

        def __len__(self):
                return len(self.contours)

        def _get_lib(self):
                return self._object.lib;

        def _set_lib(self, aDict):
                self._object.lib.update(aDict)

        lib = property(_get_lib, _set_lib, doc="glyph lib object")

        def _invalidateContours(self):
                self._contours = None

        def _buildContours(self):
                self._contours = []
                for contourIndex in range(len(self._object)):
                        c = RContour(contourIndex)
                        c.setParent(self)
                        c._buildSegments()
                        self._contours.append(c)

        #
        # attribute handlers
        #

        def _get_index(self):
                return self._object.index

        index = property(_get_index, doc="return the index of the glyph in the font")

        def _get_name(self):
                return self._object.name

        def _set_name(self, value):
                self._object.name = value

        name = property(_get_name, _set_name, doc="name")

        def _get_psName(self):
                return self._object.name

        def _set_psName(self, value):
                self._object.name = value

        psName = property(_get_psName, _set_psName, doc="name")

        def _get_baseName(self):
                return self._object.name.split('.')[0]

        baseName = property(_get_baseName, doc="")

        def _get_unicode(self):
                return self._object.unicode

        def _set_unicode(self, value):
                self._object.unicode = value

        unicode = property(_get_unicode, _set_unicode, doc="unicode")

        def _get_unicodes(self):
                return self._object.unicodes

        def _set_unicodes(self, value):
                self._object.unicodes = value

        unicodes = property(_get_unicodes, _set_unicodes, doc="unicodes")

        def _get_width(self):
                return self._object.width

        def _set_width(self, value):
                value = int(round(value))
                self._object.width = value

        width = property(_get_width, _set_width, doc="the width")

        def _get_box(self):
                #if not len(self.contours) and not len(self.components):
                #        return (0, 0, 0, 0)
                return self._object.box

        box = property(_get_box, doc="box of glyph as a tuple (xMin, yMin, xMax, yMax)")

        def _get_mark(self):
                return self._object.mark

        def _set_mark(self, value):
                self._object.mark = value

        mark = property(_get_mark, _set_mark, doc="mark")

        def _get_note(self):
                return self._object.note
                #s = self._object.note
                #if s is None:
                #        return s
                #return unicode(s, LOCAL_ENCODING)

        def _set_note(self, value):
                if value is None:
                        value = ''
                self._object.note = value
                #if type(value) == type(u""):
                #        value = value.encode(LOCAL_ENCODING)
                #self._object.note = value

        note = property(_get_note, _set_note, doc="note")

        def _get_psHints(self):
                # get an object representing the postscript zone information
                return PostScriptGlyphHintValues(self)

        psHints = property(_get_psHints, doc="postscript hint data")

        #
        # for compatibility only
        #

        def update(self):
                pass


        #
        # tools
        #

        def getPointPen(self):
                self._invalidateContours()
                # Now just don't muck with glyph.contours before you're done drawing...
                return FGPointPen(self)

        # components

        def getComponents(self):
                """Return a list of wrapped components in this RGlyph."""
                components=[]
                for i in range(len(self._object.components)):
                        c = RComponent(self._object.components[i])
                        c.setParent(self)
                        components.append(c)
                return components

        def _get_components(self):
                return self.getComponents()

        components = property(_get_components, doc="allow for iteration through glyph.components")

        def appendComponent(self, baseGlyph, offset=(0, 0), scale=(1, 1)):
                """Append a component to the glyph. x and y are optional offset values"""
                offset = roundPt((offset[0], offset[1]))
                p = FGPointPen(self)        # naked()
                xx, yy = scale
                dx, dy = offset
                p.addComponent(baseGlyph, (xx, 0, 0, yy, dx, dy))

        def clearComponents(self):
                """Clear all components."""
                self._object.components.clean()

        def removeComponent(self, component):
                """Remove a specific component from the glyph. This only works
                if the glyph does not have duplicate components in the same location."""
                pos = (component.baseGlyph, component.offset, component.scale)
                a = self.getComponents()
                found = []
                for i in a:
                        if (i.baseGlyph, i.offset, i.scale) == pos:
                                found.append(i)
                if len(found) > 1:
                        raise RoboFabError, 'Found more than one possible component to remove'
                elif len(found) == 1:
                        del self._object.components[found[0].index]
                else:
                        raise RoboFabError, 'Component does not exist'


        # anchors

        def getAnchors(self):
                """Return a list of wrapped anchors in this RGlyph."""
                anchors=[]
                for i in range(len(self._object.anchors)):
                        a = RAnchor(self._object.anchors[i])
                        a.setParent(self)
                        anchors.append(a)
                return anchors

        def _get_anchors(self):
                return self.getAnchors()

        anchors = property(_get_anchors, doc="allow for iteration through glyph.anchors")

        def appendAnchor(self, name, position):
                """Append an anchor to the glyph"""
                value = roundPt((position[0], position[1]))
                anchor = Anchor(name, value[0], value[1])
                self._object.anchors.append(anchor)

        def clearAnchors(self):
                """Clear all anchors."""
                self._object.anchors.clean()

        def removeAnchor(self, anchor):
                """Remove a specific anchor from the glyph. This only works
                if the glyph does not have anchors with duplicate names
                in exactly the same location with the same mark."""
                pos = (anchor.name, anchor.position, anchor.mark)
                a = self.getAnchors()
                found = []
                for i in a:
                        if (i.name, i.position, i.mark) == pos:
                                found.append(i)
                if len(found) > 1:
                        raise RoboFabError, 'Found more than one possible anchor to remove'
                elif len(found) == 1:
                        del self._object.anchors[found[0].index]
                else:
                        raise RoboFabError, 'Anchor does not exist'


        # guides

        def getGuides(self):
                """Return a list of wrapped guides in this RGlyph"""
                guides=[]
                for i in range(len(self._object.guides)):
                        g = RGuide(self._object.guides[i])
                        g.setParent(self)
                        guides.append(g)
                return guides

        def _get_guides(self):
                return self.getGuides()

        guides = property(_get_guides, doc="allow for iteration through glyph.guides")

        def appendHGuide(self, position, color=(0, 0, 0, 255), name=''):
                """Append a horizontal guide"""
                self._object.guides.append(position, horizontal=True, color=color, name=name)

        def appendVGuide(self, position, color=(0, 0, 0, 255), name=''):
                """Append a vertical guide"""
                self._object.guides.append(position, horizontal=False, color=color, name=name)

        def appendGuide(self, point0, point1, color=(0, 0, 0, 255), name=''):
                """Append a guide"""
                self._object.guides.append(point0, point1, color=color, name=name)

        def clearGuides(self):
                """Clear all guides."""
                self._object.guides.clean()

        def removeHGuide(self, position):
                """Remove a horizontal guide."""
                self._object.guides.removeHV(position, True)

        def removeVGuide(self, position):
                """Remove a vertical guide."""
                self._object.guides.removeHV(position, False)

        def removeGuide(self, point0, point1):
                """Remove a guide."""
                self._object.guides.remove(point0, point1)

        # contours

        def _get_contours(self):
                if self._contours is None:
                        self._buildContours()
                return self._contours

        contours = property(_get_contours, doc="allow for iteration through glyph.contours")

        def removeContour(self, index):
                """remove a specific contour  from the glyph"""
                self._object.deleteContour(index)
                self._invalidateContours()

        def center(self, padding=None):
                """Equalise sidebearings, set to padding if wanted."""
                left = self.leftMargin
                right = self.rightMargin
                if padding:
                        e_left = e_right = padding
                else:
                        e_left = (left + right)/2
                        e_right = (left + right) - e_left
                self.leftMargin= e_left
                self.rightMargin= e_right

        def removeOverlap(self):
                """Remove overlap"""
                self._object.RemoveOverlap()
                self._invalidateContours()

        def decompose(self):
                """Decompose all components"""
                self._object.Decompose()
                self._invalidateContours()

        ##broken!
        #def removeHints(self):
        #	"""Remove the hints."""
        #	self._object.RemoveHints()

        def autoHint(self):
                """Automatically generate type 1 hints."""
                self._object.Autohint()

        def move(self, (x, y), contours=True, components=True, anchors=True):
                """Move a glyph's items that are flagged as True"""
                self._object.move((x, y))
                #components and anchors moved too by fontgate
                #for c in self.getComponents():
                #        c.move((x, y))
                #for a in self.getAnchors():
                #        a.move((x, y))


        def clear(self, contours=True, components=True, anchors=True, guides=True, hints=True):
                """Clear all items marked as true from the glyph"""
                self._object.clear(contours=contours, components=components, anchors=anchors, guides=guides, hints=hints)
                if contours:
                        self._invalidateContours()


        #
        #	special treatment for GlyphMath support in FontGate
        #

        def _getMathDestination(self):
                from robofab.objects.objectsRF import RGlyph as _RGlyph
                return _RGlyph()

        def drawPoints(self, pen):
                """draw the object with a point pen"""
                for a in self._object.anchors:
                    a.drawPoints(pen)
                for c in self._object:
                    c.drawPoints(pen)
                for c in self._object.components:
                    c.drawPoints(pen)

        def copy(self, aParent=None):
                """Make a copy of this glyph.
                Note: the copy is not a duplicate FontGate glyph, but
                a RF RGlyph with the same outlines. The new glyph is
                not part of the FontGate font in any way. Use font.appendGlyph(glyph)
                to get it in a FontGate glyph again."""
                from robofab.objects.objectsRF import RGlyph as _RGlyph
                newGlyph = _RGlyph()
                newGlyph.appendGlyph(self)
                for attr in GLYPH_COPY_ATTRS:
                        value = getattr(self, attr)
                        setattr(newGlyph, attr, value)
                # hints
                doHints = False
                parent = self.getParent()
                if parent is not None and parent._supportHints:
                        hintStuff = self.naked().hints.getAsDict()
                        if hintStuff:
                                newGlyph.lib[postScriptHintDataLibKey] = hintStuff
                if aParent is not None:
                        newGlyph.setParent(aParent)
                elif self.getParent() is not None:
                        newGlyph.setParent(self.getParent())
                return newGlyph

        def __mul__(self, factor):
                return self.copy() *factor

        __rmul__ = __mul__

        def __sub__(self, other):
                return self.copy() - other.copy()

        def __add__(self, other):
                return self.copy() + other.copy()



class RContour(BaseContour):

        """RoboFab wrapper for FontGate contour object"""

        _title = "FontGateContour"

        def __init__(self, index):
                self._index = index
                self._parentGlyph = None
                self.segments = []

        def __len__(self):
                return len(self.points)

        def _buildSegments(self):
                #######################
                # Notes about FL node contour structure
                #######################
                # for TT curves, FL lists them as seperate nodes:
                #	[move, off, off, off, line, off, off]
                # and, this list is sequential. after the last on curve,
                # it is possible (and likely) that there will be more offCurves
                # in our segment object, these should be associated with the
                # first segment in the contour.
                #
                # for PS curves, it is a very different scenerio.
                # curve nodes contain points:
                #	[on, off, off]
                # and the list is not in sequential order. the first point in
                # the list is the on curve and the subsequent points are the off
                # curve points leading up to that on curve.
                #
                # it is very important to remember these structures when trying
                # to understand the code below

                self.segments = []
                offList = []
                nodes = self._nakedcontour.nodes
                for x in range(self._nodeLength):
                        node = nodes[x]
                        # we do have a loose off curve. deal with it.
                        if node.type == "Off":
                                offList.append(x)
                        # we are not dealing with a loose off curve
                        else:
                                s = RSegment(x)
                                s.setParent(self)
                                # but do we have a collection of loose off curves above?
                                # if so, apply them to the segment, and clear the list
                                if len(offList) != 0:
                                        s._looseOffCurve = offList
                                offList = []
                                self.segments.append(s)
                # do we have some off curves now that the contour is complete?
                if len(offList) != 0:
                        # ugh. apply them to the first segment
                        self.segments[0]._looseOffCurve = offList

        def setParent(self, parentGlyph):
                self._parentGlyph = parentGlyph

        def getParent(self):
                return self._parentGlyph

        def _get__nakedcontour(self):
                return self._parentGlyph.naked()[self._index]

        _nakedcontour = property(_get__nakedcontour, doc="")

        def _get__nodeLength(self):
                return self._nakedcontour.length()

        _nodeLength = property(_get__nodeLength, doc="")

        def _get__lastNodeIndex(self):
                return self._nodeLength - 1

        _lastNodeIndex = property(_get__lastNodeIndex, doc="")

        def _previousNodeIndex(self, index):
                return (index - 1) % self._nodeLength

        def _nextNodeIndex(self, index):
                return (index + 1) % self._nodeLength

        def _getNode(self, index):
                return self._nakedcontour.getNode(index)

        def _get__nodes(self):
                return self._nakedcontour.nodes

        _nodes = property(_get__nodes, doc="")

        def _get_points(self):
                points = []
                for segment in self.segments:
                        for point in segment.points:
                                points.append(point)
                return points

        points = property(_get_points, doc="")

        def _get_bPoints(self):
                bPoints = []
                for segment in self.segments:
                        bp = RBPoint(segment.index)
                        bp.setParent(self)
                        bPoints.append(bp)
                return bPoints

        bPoints = property(_get_bPoints, doc="")

        def _get_index(self):
                return self._index

        def _set_index(self, index):
                if index != self._index:
                        self._nakedcontour.ReorderContour(self._index, index)
                        # reorder and set the _index of the existing RContour objects
                        # this will be a better solution than reconstructing all the objects
                        # segment objects will still, sadly, have to be reconstructed
                        contourList = self.getParent().contours
                        contourList.insert(index, contourList.pop(self._index))
                        for i in range(len(contourList)):
                                contourList[i]._index = i
                                contourList[i]._buildSegments()


        index = property(_get_index, _set_index, doc="the index of the contour")

        def _startNodeIndexForSegment(self, index):
                if index <= 0:
                    return 0
                if index == len(self.segments):
                    return self._nodeLength
                return self.segments[index]._nodeIndex;

        def appendSegment(self, segmentType, points, smooth=False):
                return self.insertSegment(index=len(self.segments), segmentType=segmentType, points=points, smooth=smooth)

        def insertSegment(self, index, segmentType, points, smooth=False):
                """insert a segment into the contour"""
                segmentIndex = index
                index = self._startNodeIndexForSegment(segmentIndex)
                nc = self._nakedcontour;
                # do a  qcurve insertion
                if segmentType == QCURVE:
                        for point in points[:-1]:
                                nc.insertNode(("Off", (point[0], point[1])), index)
                                index = index + 1
                        nc.insertNode(("On", (points[-1][0], points[-1][1]), smooth), index)
                # do a regular insertion
                else:
                        onX, onY = points[-1]
                        nc.insertNode((_rfToFLSegmentType(segmentType), (onX, onY), smooth), index)
                        index = index + 1
                        # fix the off curves in case the user is inserting a curve
                        # but is not specifying off curve points
                        if segmentType == CURVE and len(points) == 1:
                                pSeg = self._prevSegment(segmentIndex)
                                pOn = pSeg.onCurve
                                nc.insertNode(("Off", (pOn.x, pOn.y)), index)
                                index = index + 1
                                nc.insertNode(("Off", (onX, onX)), index)
                                index = index + 1
                        else:
                                for pointIndex in range(len(points[:-1])):
                                        x, y = points[pointIndex]
                                        nc.insertNode(("Off", (x, y)), index)
                                        index = index + 1
                self._buildSegments()
                return self.segments[segmentIndex]

        def removeSegment(self, index):
                """remove a segment from the contour"""
                segment = self.segments[index]
                # we have a qcurve. umph.
                if segment.type == QCURVE:
                        indexList = [segment._nodeIndex] + segment._looseOffCurve
                        indexList.sort()
                        indexList.reverse()
                        parent = self._nakedcontour
                        for nodeIndex in indexList:
                                parent.deleteNode(nodeIndex)
                # we have a more sane structure to follow
                else:
                        # store some info for later
                        next = self._nextSegment(index)
                        nextOffA = None
                        nextOffB = None
                        nextType = next.type
                        if nextType != LINE and nextType != MOVE:
                                pA = next.offCurve[0]
                                nextOffA = (pA.x, pA.y)
                                pB = next.offCurve[-1]
                                nextOffB = (pB.x, pB.y)
                        nodeIndex = segment._nodeIndex
                        self._nakedcontour.deleteNode(nodeIndex)
                        self._buildSegments()
                        # now we must override FL guessing about offCurves
                        next = self._nextSegment(index - 1)
                        nextType = next.type
                        if nextType != LINE and nextType != MOVE:
                                pA = next.offCurve[0]
                                pB = next.offCurve[-1]
                                pA.x, pA.y = nextOffA
                                pB.x, pB.y = nextOffB

        def reverseContour(self):
                """reverse contour direction"""
                self._nakedcontour.reverse()
                self._buildSegments()

        def autoSmoothContour(self):
                """reverse contour direction"""
                res = self._nakedcontour.autoSmooth()
                self._buildSegments()
                return res

        def autoInterpolatedContour(self):
                """reverse contour direction"""
                res = self._nakedcontour.autoInterpolated()
                self._buildSegments()
                return res

        def autoCloseContour(self):
                """reverse contour direction"""
                res = self._nakedcontour.autoClose()
                self._buildSegments()
                return res

        def setStartSegment(self, segmentIndex):
                """set the first node on the contour"""
                self._nakedcontour.setStartNode(segments[segmentIndex]._nodeIndex)
                self.getParent()._invalidateContours()
                self.getParent()._buildContours()

        def copy(self, aParent=None):
                """Copy this object -- result is an ObjectsRF flavored object.
                There is no way to make this work using FontGate objects.
                Copy is mainly used for glyphmath.
                """
                raise RoboFabError, "copy() for objectsFL.RContour is not implemented."



class RSegment(BaseSegment):

        _title = "FontGateSegment"

        def __init__(self, flNodeIndex):
                BaseSegment.__init__(self)
                self._nodeIndex = flNodeIndex
                self._looseOffCurve = []	#a list of indexes to loose off curve nodes

        def _get__node(self):
                return self.getParent()._nakedcontour.getNode(self._nodeIndex)

        _node = property(_get__node, doc="")

        def _get_qOffCurve(self):
                nodes = self.getParent()._nakedcontour.nodes
                off = []
                for x in self._looseOffCurve:
                        off.append(nodes[x])
                return off

        _qOffCurve = property(_get_qOffCurve, doc="free floating off curve nodes in the segment")

        def _get_index(self):
                return self._nodeIndex

        index = property(_get_index, doc="")

        def _isQCurve(self):
                # loose off curves only appear in q curves
                if len(self._looseOffCurve) != 0:
                        return True
                return False

        def _get_type(self):
                if self._isQCurve():
                        return QCURVE
                return _flToRFSegmentType(self._node.type)

        def _set_type(self, segmentType):
                if self._isQCurve():
                        raise RoboFabError, 'qcurve point types cannot be changed'
                oldNode = self._node
                oldType = oldNode.type
                oldPointType = _flToRFSegmentType(oldType)
                if oldPointType == MOVE:
                        raise RoboFabError, '%s point types cannot be changed'%oldPointType
                if segmentType == MOVE or segmentType == OFFCURVE:
                        raise RoboFabError, '%s point types cannot be assigned'%oldPointType
                if oldPointType == segmentType:
                        return
                oldNode.type = _rfToFLSegmentType(segmentType)

        type = property(_get_type, _set_type, doc="")

        def _get_smooth(self):
                return self._node.smooth

        def _set_smooth(self, value):
                self._node.smooth = value

        smooth = property(_get_smooth, _set_smooth, doc="")

        def _get_points(self):
                points = []
                node = self._node
                # gather the off curves
                #
                # are we dealing with a qCurve? ugh.
                # gather the loose off curves
                if self._isQCurve():
                        off = self._qOffCurve
                        x = 0
                        for n in off:
                                p = RPoint()
                                p.setParent(self)
                                p._qOffIndex = x
                                points.append(p)
                                x = x + 1
                # otherwise get the points associated with the node
                #else:
                #        index = 1
                #        for point in node.points[1:]:
                #                p = RPoint(index)
                #                p.setParent(self)
                #                points.append(p)
                #                index = index + 1
                # the last point should always be the on curve
                p = RPoint()
                p.setParent(self)
                points.append(p)
                return points

        points = property(_get_points, doc="")

        def move(self, (x, y)):
                x, y = roundPt((x, y))
                self._node.Shift(Point(x, y))
                if self._isQCurve():
                        qOff = self._qOffCurve
                        for node in qOff:
                                node.Shift(Point(x, y))

        def copy(self, aParent=None):
                """Copy this object -- result is an ObjectsRF flavored object.
                There is no way to make this work using FontGate objects.
                Copy is mainly used for glyphmath.
                """
                raise RoboFabError, "copy() for objectsFL.RSegment is not implemented."



class RPoint(BasePoint):

        _title = "FGPoint"

        def __init__(self):
                #BasePoint.__init__(self)
                #self._pointIndex = pointIndex
                self.selected = False
                self._qOffIndex = None

        def _get__parentGlyph(self):
                return self._parentContour.getParent()

        _parentGlyph = property(_get__parentGlyph, doc="")

        def _get__parentContour(self):
                return self._parentSegment.getParent()

        _parentContour = property(_get__parentContour, doc="")

        def _get__parentSegment(self):
                return self.getParent()

        _parentSegment = property(_get__parentSegment, doc="")

        def _get__node(self):
                if self._qOffIndex is not None:
                        return self.getParent()._qOffCurve[self._qOffIndex]
                return self.getParent()._node

        _node = property(_get__node, doc="")

        def _get__point(self):
                return self._node.point

        _point = property(_get__point, doc="")

        def _get_x(self):
                return self._node.x

        def _set_x(self, value):
                value = int(round(value))
                self._node.x = value

        x = property(_get_x, _set_x, doc="")

        def _get_y(self):
                return self._node.y

        def _set_y(self, value):
                value = int(round(value))
                self._node.y = value

        y = property(_get_y, _set_y, doc="")

        def _get_type(self):
                # FL store quad contour data as a list of off curves and lines
                # (see note in RContour._buildSegments). So, we need to do
                # a bit of trickery to return a decent point type.
                # if the straight FL node type is off curve, it is a loose
                # quad off curve. return that.
                tp = _flToRFSegmentType(self._node.type)
                if tp == OFFCURVE:
                        return OFFCURVE
                # otherwise we are dealing with an on curve. in this case,
                # we attempt to get the parent segment type and return it.
                segment = self.getParent()
                if segment is not None:
                        return segment.type
                # we must not have a segment, fall back to straight conversion
                return tp

        type = property(_get_type, doc="")

        def move(self, (x, y)):
                x, y = roundPt((x, y))
                self._point.Shift(Point(x, y))

        def scale(self, (x, y), center=(0, 0)):
                centerX, centerY = roundPt(center)
                point = self._point
                point.x, point.y = _scalePointFromCenter((point.x, point.y), (x, y), (centerX, centerY))

        def copy(self, aParent=None):
                """Copy this object -- result is an ObjectsRF flavored object.
                There is no way to make this work using FontGate objects.
                Copy is mainly used for glyphmath.
                """
                raise RoboFabError, "copy() for objectsFL.RPoint is not implemented."


class RBPoint(BaseBPoint):

        _title = "FLBPoint"

        def __init__(self, segmentIndex):
                #BaseBPoint.__init__(self)
                self._segmentIndex = segmentIndex

        def _get__parentSegment(self):
                return self.getParent().segments[self._segmentIndex]

        _parentSegment = property(_get__parentSegment, doc="")

        def _get_index(self):
                return self._segmentIndex

        index = property(_get_index, doc="")

        def _get_selected(self):
                return self._parentSegment.selected

        def _set_selected(self, value):
                self._parentSegment.selected = value

        selected = property(_get_selected, _set_selected, doc="")

        def copy(self, aParent=None):
                """Copy this object -- result is an ObjectsRF flavored object.
                There is no way to make this work using FontGate objects.
                Copy is mainly used for glyphmath.
                """
                raise RoboFabError, "copy() for objectsFL.RBPoint is not implemented."


class RComponent(BaseComponent):
        """RoboFab wrapper for FontGate Component object"""
        _title = "FontGateComponent"

        def __init__(self, fgComponent):
                BaseComponent.__init__(self)
                self._object =  fgComponent

        def _get_index(self):
                return self._object.index

        index = property(_get_index, doc="index of component")

        def _get_baseGlyph(self):
                return self._object.baseGlyph

        baseGlyph = property(_get_baseGlyph, doc="component's baseGlyph")

        def _get_offset(self):
                x, y = self._object.offset;
                return (int(x), int(y))

        def _set_offset(self, value):
                self._object.offset=value

        offset = property(_get_offset, _set_offset, doc="the offset of the component")

        def _get_scale(self):
                return self._object.scale

        def _set_scale(self, (x, y)):
                self._object.scale=(x, y)

        scale = property(_get_scale, _set_scale, doc="the scale of the component")

        def move(self, (x, y)):
                """Move the component"""
                self._object.move((x, y))

        def decompose(self):
                """Decompose the component"""
                self._object.decompose()

        #def copy(self, aParent=None):
        #        """Copy this object -- result is an ObjectsRF flavored object.
        #        There is no way to make this work using FontGate objects.
        #        Copy is mainly used for glyphmath.
        #        """
        #        raise RoboFabError, "copy() for objectsFG.RComponent is not implemented."



class RAnchor(BaseAnchor):
        """RoboFab wrapper for FontGate Anchor object"""

        _title = "FontGateAnchor"

        def __init__(self, fgAnchor):
                BaseAnchor.__init__(self)
                self._object =  fgAnchor

        def _get_y(self):
                return self._object.y

        def _set_y(self, value):
                self._object.y = value

        y = property(_get_y, _set_y, doc="y")

        def _get_x(self):
                return self._object.x

        def _set_x(self, value):
                self._object.x = value

        x = property(_get_x, _set_x, doc="x")

        def _get_name(self):
                return self._object.name

        def _set_name(self, value):
                self._object.name = value

        name = property(_get_name, _set_name, doc="name")

        def _get_mark(self):
                return self._object.mark

        def _set_mark(self, value):
                self._object.mark = value

        mark = property(_get_mark, _set_mark, doc="mark")

        def _get_index(self):
                return self._object.index

        index = property(_get_index, doc="index of the anchor")

        def _get_position(self):
                return self._object.position

        def _set_position(self, value):
                self._object.position = value

        position = property(_get_position, _set_position, doc="position of the anchor")



class RGuide(BaseGuide):

        """RoboFab wrapper for FontGate Guide object"""

        _title = "FontGateGuide"

        def __init__(self, fgGuide):
                BaseGuide.__init__(self)
                self._object = fgGuide

        def __repr__(self):
                # this is a doozy!
                parent = "unknown_parent"
                parentObject = self.getParent()
                if parentObject is not None:
                        # do we have a font?
                        try:
                                parent = parentObject.info.postscriptFullName
                        except AttributeError:
                                # or do we have a glyph?
                                try:
                                        parent = parentObject.name
                                # we must be an orphan
                                except AttributeError: pass
                return "<Robofab guide wrapper for %s>"%parent

        def _get_position(self):
                return self._object.position

        def _set_position(self, value):
                self._object.position = value

        position = property(_get_position, _set_position, doc="position")


        def _get_p0(self):
                return self._object.p0

        def _set_p0(self, value):
                self._object.p0 = value

        p0 = property(_get_p0, _set_p0, doc="p0")


        def _get_p1(self):
                return self._object.p1

        def _set_p1(self, value):
                self._object.p1 = value

        p1 = property(_get_p1, _set_p1, doc="p1")


        def _get_color(self):
                return self._object.color

        def _set_color(self, value):
                self._object.color = value

        color = property(_get_color, _set_color, doc="color")


        def _get_name(self):
                return self._object.name

        def _set_name(self, value):
                self._object.name = value

        name = property(_get_name, _set_name, doc="name")


        def _get_horizontal(self):
                return self._object.horizontal

        horizontal = property(_get_horizontal, doc="horizontal")

        def _get_vertical(self):
                return self._object.vertical

        vertical = property(_get_vertical, doc="vertical")

        def _get_index(self):
                return self._object.index

        index = property(_get_index, doc="index of the guide")



class RGroups(BaseGroups):

        """RoboFab wrapper for FontGate group data"""

        _title = "FontGateGroups"

        def __init__(self, aDict):
                self.update(aDict)

        def __setitem__(self, key, value):
                # override baseclass so that data is stored in FL classes
                if not isinstance(key, str):
                        raise RoboFabError, 'key must be a string'
                if not isinstance(value, list):
                        raise RoboFabError, 'group must be a list'
                super(RGroups, self).__setitem__(key, value)
                self._setFLGroups()

        def __delitem__(self, key):
                # override baseclass so that data is stored in FL classes
                super(RGroups, self).__delitem__(key, value)
                self._setFLGroups()

        def _setFLGroups(self):
                # set the group data into the font.
                if self.getParent() is not None:
                        #groups = []
                        #for i in self.keys():
                        #        value = ' '.join(self[i])
                        #        groups.append(': '.join([i, value]))
                        #groups.sort()
                        #self.getParent().naked().classes = groups
                        self.getParent().naked().groups.fromDict(dict(self))

        def update(self, aDict):
                # override baseclass so that data is stored in FL classes
                super(RGroups, self).update(aDict)
                self._setFLGroups()

        def clear(self):
                # override baseclass so that data is stored in FL classes
                super(RGroups, self).clear()
                self._setFLGroups()

        def pop(self, key):
                # override baseclass so that data is stored in FL classes
                i = super(RGroups, self).pop(key)
                self._setFLGroups()
                return i

        def popitem(self):
                # override baseclass so that data is stored in FL classes
                i = super(RGroups, self).popitem()
                self._setFLGroups()
                return i

        def setdefault(self, key, value=None):
                # override baseclass so that data is stored in FL classes
                i = super(RGroups, self).setdefault(key, value)
                self._setFLGroups()
                return i


class RKerning(BaseKerning):

        """RoboFab wrapper for FontGate Kerning data"""

        _title = "FontGateKerning"

        def __init__(self, font):
                BaseKerning.__init__(self)
                self._kerning = font.kerning

        def __getitem__(self, key):
                if isinstance(key, tuple):
                        pair = key
                        return self.get(pair)
                elif isinstance(key, str):
                        raise RoboFabError, 'kerning pair must be a tuple: (left, right)'
                else:
                        keys = self.keys()
                        if key > len(keys):
                                raise IndexError
                        keys.sort()
                        pair = keys[key]
                if not self._kerning.has_key(pair):
                        raise IndexError
                else:
                        return pair

        def __setitem__(self, pair, value):
                if not isinstance(pair, tuple):
                        raise RoboFabError, 'kerning pair must be a tuple: (left, right)'
                else:
                        if len(pair) != 2:
                                raise RoboFabError, 'kerning pair must be a tuple: (left, right)'
                        else:
                                if value == 0:
                                        if self._kerning.get(pair) is not None:
                                                self._kerning.remove(pair)
                                else:
                                         self._kerning[pair] = value
                                self._hasChanged()


        def asDict(self, returnIntegers=True):
                """return the object as a dictionary"""
                return self._kerning.asDict()

        def clear(self):
                """clear all kerning"""
                self._kerning.clear()

        def __add__(self, other):
                """Math operations on FL Kerning objects return RF Kerning objects
                as they need to be orphaned objects and FL can't deal with that."""
                from sets import Set

                from robofab.objects.objectsRF import RKerning as _RKerning
                new = _RKerning()
                k = Set(self.keys()) | Set(other.keys())
                for key in k:
                        new[key] = self.get(key, 0) + other.get(key, 0)
                return new

        def __sub__(self, other):
                """Math operations on FL Kerning objects return RF Kerning objects
                as they need to be orphaned objects and FL can't deal with that."""
                from sets import Set

                from robofab.objects.objectsRF import RKerning as _RKerning
                new = _RKerning()
                k = Set(self.keys()) | Set(other.keys())
                for key in k:
                        new[key] = self.get(key, 0) - other.get(key, 0)
                return new

        def __mul__(self, factor):
                """Math operations on FL Kerning objects return RF Kerning objects
                as they need to be orphaned objects and FL can't deal with that."""
                from robofab.objects.objectsRF import RKerning as _RKerning
                new = _RKerning()
                for name, value in self.items():
                        new[name] = value * factor
                return new

        __rmul__ = __mul__

        def __div__(self, factor):
                """Math operations on FL Kerning objects return RF Kerning objects
                as they need to be orphaned objects and FL can't deal with that."""
                if factor == 0:
                        raise ZeroDivisionError
                return self.__mul__(1.0/factor)


class RLib(BaseLib):

        """RoboFab wrapper for FontGate lib"""

        def __init__(self, aDict):
                self.update(aDict)

        def __setitem__(self, key, value):
                # override baseclass so that data is stored in customdata field
                super(RLib, self).__setitem__(key, value)
                self._stashLib()

        def __delitem__(self, key):
                # override baseclass so that data is stored in customdata field
                super(RLib, self).__delitem__(key)
                self._stashLib()

        def _stashLib(self):
                # write the plist into the customdata field of the FL object
                if self.getParent() is None:
                        return
                if not self:
                        data = None
                elif len(self) == 1 and "org.robofab.fontlab.customdata" in self:
                        data = self["org.robofab.fontlab.customdata"].data
                else:
                        f = StringIO()
                        writePlist(self, f)
                        data = f.getvalue()
                        f.close()
                parent = self.getParent()
                parent.naked().customdata = data

        def update(self, aDict):
                # override baseclass so that data is stored in customdata field
                super(RLib, self).update(aDict)
                self._stashLib()

        def clear(self):
                # override baseclass so that data is stored in customdata field
                super(RLib, self).clear()
                self._stashLib()

        def pop(self, key):
                # override baseclass so that data is stored in customdata field
                i = super(RLib, self).pop(key)
                self._stashLib()
                return i

        def popitem(self):
                # override baseclass so that data is stored in customdata field
                i = super(RLib, self).popitem()
                self._stashLib()
                return i

        def setdefault(self, key, value=None):
                # override baseclass so that data is stored in customdata field
                i = super(RLib, self).setdefault(key, value)
                self._stashLib()
                return i


class RInfo(BaseInfo):

        """RoboFab wrapper for FontGate Font Info"""

        _title = "FontGateInfo"

        def __init__(self, font):
                super(RInfo, self).__init__()
                self._object = font.info


        def _environmentSetAttr(self, attr, value):
                try:
                        setattr(self._object, attr, value)
                except AttributeError:
                        print "The attribute %s is not supported by FontGate. This data will not be set." % attr
                        return


        def _environmentGetAttr(self, attr):
                return getattr(self._object, attr)



class RFeatures(BaseFeatures):

        _title = "FLFeatures"

        def __init__(self, font):
                super(RFeatures, self).__init__()
                self._object = font

        def _get_text(self):
                naked = self._object
                features = []
                if naked.ot_classes:
                        features.append(_normalizeLineEndings(naked.ot_classes))
                for feature in naked.features:
                        features.append(_normalizeLineEndings(feature.value))
                return "".join(features)

        def _set_text(self, value):
                classes, features = splitFeaturesForFontLab(value)
                naked = self._object
                naked.ot_classes = classes
                naked.features.clean()
                for featureName, featureText in features:
                        f = Feature(featureName, featureText)
                        naked.features.append(f)

        text = property(_get_text, _set_text, doc="raw feature text.")
