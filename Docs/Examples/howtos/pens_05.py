from robofab.pens.filterPen import spikeGlyph
from robofab.world import CurrentGlyph

segmentLength = 20
spikeLength = 100
spikeGlyph(CurrentGlyph(), segmentLength, spikeLength)
