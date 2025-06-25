# robothon06
# interpolate two fonts

from robofab.interface.all.dialogs import AskString
from robofab.world import NewFont, SelectFont

font1 = SelectFont("Select font 1")
font2 = SelectFont("Select font 2")

value = AskString("What percentage?")
value = int(value) * 0.01

destination = NewFont()

# this interpolates the glyphs
destination.interpolate(value, font1, font2, doProgress=True)

# this interpolates the kerning
# comment this line out of you're just testing
destination.kerning.interpolate(font1.kerning, font2.kerning, value)

destination.update()
