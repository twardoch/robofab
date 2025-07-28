"""Pens for creating glyphs in FontGate."""

__all__ = ["FGPen", "FGPointPen", "drawFGGlyphOntoPointPen"]


from fontgate import *

from robofab.pens.adapterPens import SegmentToPointPen
# from robofab.tools.toolsFL import NewGlyph
from robofab.pens.pointPen import AbstractPointPen


def roundInt(x):
    return int(round(x))


class FGPen(SegmentToPointPen):
    def __init__(self, glyph):
        SegmentToPointPen.__init__(self, FGPointPen(glyph))


class FGPointPen(AbstractPointPen):
    def __init__(self, glyph):
        self.glyph = glyph.naked()
        self.currentPath = None
        self._glyph_parent = glyph.getParent()

    def beginPath(self):
        self.currentPath = []

    def endPath(self):
        # Love is... abstracting away FL's madness.
        path = self.currentPath
        self.currentPath = None
        glyph = self.glyph
        if len(path) == 1 and path[0][3] is not None:
            # Single point on the contour, it has a name. Make it an anchor.
            x, y = path[0][0]
            name = path[0][3]
            glyph.anchors.append((x, y), name)
            return
        newcontour = glyph.createContour()
        if len(path) == 0:
            return
        firstOnCurveIndex = None
        for i in range(len(path)):
            if path[i][1] is not None:
                firstOnCurveIndex = i
                break
        if firstOnCurveIndex is None:
            # TT special case: on-curve-less contour. FG doesn't support that,
            # so we insert an implied point at the end.
            x1, y1 = path[0][0]
            x2, y2 = path[-1][0]
            impliedPoint = 0.5 * (x1 + x2), 0.5 * (y1 + y2)
            path.append((impliedPoint, "qcurve", True, None))
            firstOnCurveIndex = 0
        path = path[firstOnCurveIndex + 1 :] + path[: firstOnCurveIndex + 1]
        firstPoint, segmentType, smooth, name = path[-1]
        closed = True
        if segmentType == "move":
            path = path[:-1]
            closed = False
            # XXX The contour is not closed, but I can't figure out how to
            # create an open contour in FG. Creating one by hand shows type"0x8011"
            # for a move node in an open contour, but I'm not able to access
            # that flag.
        elif segmentType == "line":
            # The contour is closed and ends in a lineto, which is redundant
            # as it's implied by closepath.
            path = path[:-1]
        # node = Node("Move", Point(roundInt(x), roundInt(y)))
        smoothFlags = False
        if smooth and closed:
            if segmentType == "line" or path[0][1] == "line":
                smoothFlags = False  # node.alignment = nFIXED
            else:
                smoothFlags = True  #  node.alignment = nSMOOTH
        newcontour.appendNode("Move", firstPoint, smoothFlags)
        segment = []
        nPoints = len(path)
        for i in range(nPoints):
            pt, segmentType, smooth, name = path[i]
            segment.append(pt)
            if segmentType is None:
                continue
            if segmentType == "curve":
                if len(segment) < 2:
                    segmentType = "line"
                elif len(segment) == 2:
                    segmentType = "qcurve"
            if segmentType == "qcurve":
                for x, y in segment[:-1]:
                    newcontour.appendNode("Off", (x, y))
                x, y = segment[-1]
                newcontour.appendNode("On", (x, y))
            elif segmentType == "curve":
                if len(segment) == 3:
                    cubicSegments = [segment]
                else:
                    from fontTools.pens.basePen import \
                        decomposeSuperBezierSegment

                    cubicSegments = decomposeSuperBezierSegment(segment)
                nSegments = len(cubicSegments)
                for i in range(nSegments):
                    pt1, pt2, pt3 = cubicSegments[i]
                    newcontour.appendNode("Curve", pt3, i != nSegments - 1)
                    newcontour.appendNode("Off", pt1)
                    newcontour.appendNode("Off", pt2)
            elif segmentType == "line":
                assert len(segment) == 1, segment
                newcontour.appendNode("On", segment[0])
            else:
                assert 0, "unsupported curve type (%s)" % segmentType
            if smooth:
                if i + 1 < nPoints or closed:
                    # Can't use existing node, as you can't change node attributes
                    # AFTER it's been appended to the glyph.
                    node = newcontour[-1]
                    if segmentType == "line" or path[(i + 1) % nPoints][1] == "line":
                        # tangent
                        node.smooth = False
                    else:
                        # curve
                        node.smooth = True
            segment = []
        if closed:
            # we may have output a node too much
            node = newcontour[-1]
            if node.type == "On" and (node.x, node.y) == (firstPoint[0], firstPoint[1]):
                newcontour.deleteNode(len(newcontour) - 1)

    def addPoint(self, pt, segmentType=None, smooth=None, name=None, **kwargs):
        self.currentPath.append((pt, segmentType, smooth, name))

    def addComponent(self, baseName, transformation):
        assert self.currentPath is None
        self.glyph.components.append(baseName, transformation)


def drawFGGlyphOntoPointPen(fgGlyph, pen):
    """Draw a FontGate glyph onto a PointPen."""
    for anchor in fgGlyph.anchors:
        pen.beginPath()
        pen.addPoint(anchor.position, name=anchor.name)
        pen.endPath()
    for fgContour in fgGlyph:
        ufo_nodes = fgContour.getUFONodesList()
        pen.beginPath()
        for pt, segmentType, smooth in ufo_nodes:
            pen.addPoint(pt, segmentType=segmentType, smooth=smooth)
        pen.endPath()
    components = fgGlyph.components.getAsList()
    for baseGlyph, tranform in components:
        pen.addComponent(baseGlyph, tranform)


class FGPointContourPen(FGPointPen):
    """Same as FGPointPen, except that it ignores components."""

    def addComponent(self, baseName, transformation):
        pass


def _simplifyValues(*values):
    """Given a set of numbers, convert items to ints if they are
    integer float values, eg. 0.0, 1.0."""
    newValues = []
    for v in values:
        i = int(v)
        if v == i:
            v = i
        newValues.append(v)
    return newValues


if __name__ == "__main__":
    pass
