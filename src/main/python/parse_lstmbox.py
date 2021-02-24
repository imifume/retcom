from collections import defaultdict

class LSTMBox(object):
    def __init__(self, path, vertical=True):
        self.path = path
        self.vertical = vertical

        self.boxParsed = None
        self.boxCleaned = None
        self.boxHashes = None
        self.boxSegmented = None
        self.boxStringDict = None
        self.boxList = None

        self.processBox()


    def processBox(self):
        with open(self.path, encoding="utf8") as f:
            self.box = f.readlines()

        self.boxParsed = self.parseBox(self.box)
        self.boxCleaned = self.cleanBox(self.boxParsed)
        self.boxHashes, self.boxSegmented = self.segmentBox(self.boxCleaned)
        self.boxStringDict = dict([(key, "".join(self.boxSegmented[key])) for key in self.boxSegmented.keys()])
        self.boxList = [["".join(self.boxSegmented[key]), self.boxHashes[key]] for key in self.boxSegmented.keys()]

    def parseBox(self, b):
        box_parsed = []
        for l in [line.replace('\n', '').split(' ') for line in b]:
            box_parsed.append([])
            for idx, val in enumerate(l):
                if idx != 0:
                    if val != '':
                        box_parsed[-1].append(int(val))
                else:
                    box_parsed[-1].append(val)

        return box_parsed

    def cleanBox(self, b):
        if self.vertical:
            return [l for l in b if l[0] not in ['', '\t']]
        else:
            return [[' '] + l[1:] if l[0] == '' else l for l in b if l[0] not in ['\t']]

    def segmentBox(self, b):
        segments = defaultdict(list)
        hashes = {}
        
        for el in b:
            h = hash(tuple(el[1:-1]))
            hashes[h] = el[1:]
            segments[h].append(el[0])
            
        return hashes, segments
