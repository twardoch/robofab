# robofab manual
# Usepens howto
# attribute examples

from robofab.pens.digestPen import DigestPointPen
from robofab.world import OpenFont

f = OpenFont()

myPen = DigestPointPen()
f['period'].drawPoints(myPen)

print myPen.getDigest()
