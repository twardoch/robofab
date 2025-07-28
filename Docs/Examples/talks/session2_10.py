# use a point pen

from robofab.pens.pointPen import PrintingPointPen
from robofab.world import CurrentFont

font = CurrentFont()
glyph = font["A"]

pen = PrintingPointPen()
glyph.drawPoints(pen)
