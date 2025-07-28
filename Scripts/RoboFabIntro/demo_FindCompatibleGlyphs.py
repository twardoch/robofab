#
#
#	make a list of which glyphs in this font could theoretically
#	interpolate with each other.
#
#


from robofab.pens.digestPen import DigestPointPen, DigestPointStructurePen
from robofab.world import CurrentFont

compatibles = {}

f = CurrentFont()
for c in f:
	p = DigestPointStructurePen()
	c.drawPoints(p)
	d = p.getDigest()
	if not compatibles.has_key(d):
		compatibles[d] = []
	compatibles[d].append(c.name)

print
print 'In %s, these glyphs could interpolate:'%(f.info.postscriptFullName)
for d, names in compatibles.items():
	if len(names) > 1:
		print ", ".join(names)