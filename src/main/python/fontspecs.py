from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable

def fetchFontSpec(path):
    font = TTFont(path)
    cmap = font['cmap']
    t = cmap.getcmap(3,1).cmap
    s = font.getGlyphSet()
    unitsPerEm = font['head'].unitsPerEm

    return {
        'font' : font,
        't' : t,
        's' : s,
        'upm' : unitsPerEm
    }

def getCharDimensions(char, ptSize, fontSpec):
    t = fontSpec['t']
    s = fontSpec['s']
    upm = fontSpec['upm']

    oc = ord(char)
    if oc in t and t[oc] in s:
        w = s[t[oc]].width
    else:
        w = s['.notdef'].width

    return [w*ptSize/upm, ptSize]

def getTextDimensions(text, ptSize, fontSpec, dim=[0,0]):
    lines = text.split('\n')

    if len(lines) == 1:
        w = 0

        t = fontSpec['t']
        s = fontSpec['s']
        upm = fontSpec['upm']

        for c in text:
            oc = ord(c)
            if oc in t and t[oc] in s:
                w += s[t[oc]].width
            else:
                w += s['.notdef'].width

        dim0_new = w*ptSize/upm
        if dim0_new > dim[0]:
            dim[0] = dim0_new

        dim[1] += ptSize
    else:
        for line in lines:
            dim = getTextDimensions(line, ptSize, fontSpec, dim)
        
    return dim

HALF2FULLWIDTH = dict((i, i + 0xFEE0) for i in range(0x21, 0x7F))
FULL2HALFWIDTH = dict((i + 0xFEE0, i) for i in range(0x21, 0x7F))

def half2fullWidth(txt:str):
    return txt.translate(HALF2FULLWIDTH)

def full2halfWidth(txt:str):
    return txt.translate(FULL2HALFWIDTH)

class FontGeom(object):
    def __init__(self, path, ptSize=12):
        self.path = path
        self.fontSpec = fetchFontSpec(path)
        self.ptSize = ptSize

    def getTextDimensions(self, text, ptSize=None):
        if not ptSize:
            ptSize = self.ptSize

        return getTextDimensions(text, ptSize, self.fontSpec, [0,0])

    def getTextWidth(self, text, ptSize=None):
        self.getTextDimensions(text, ptSize)[0]

    def getTextHeight(self, text, ptSize=None):
        self.getTextDimensions(text, ptSize)[1]

    def getTextAspectRatio(self, text, ptSize=None, order='w/h'):
        w, h = self.getTextDimensions(text, ptSize)
        return eval(order)

    def getCharDimensions(self, char, ptSize=None):
        if not ptSize:
            ptSize = self.ptSize

        return getCharDimensions(char, ptSize, self.fontSpec)

    def getCharAspectRatio(self, char, ptSize=None, order='w/h'):
        w, h = self.getTextDimensions(char, ptSize)
        return eval(order)

if __name__ == "__main__":
    text = 'This is a test\nABCDEFGHIJKLMNOPQRSTUVW'
    fontSpec = fetchFontSpec('/Library/Fonts/Courier New.ttf')
    print(getTextDimensions(text, 12, fontSpec, [0,0]))

    fg = FontGeom('/Library/Fonts/Courier New.ttf', 12)
    print(fg.getTextDimensions(text))

    