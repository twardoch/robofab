# robofab manual
# Usepens howto
# DigestPointStructurePen examples

from robofab.pens.digestPen import DigestPointStructurePen
from robofab.world import OpenFont

f = OpenFont()

myPen = DigestPointStructurePen()
f['period'].drawPoints(myPen)

print myPen.getDigest()
