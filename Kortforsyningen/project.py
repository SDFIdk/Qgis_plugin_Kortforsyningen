from qgis.core import *
from PyQt4 import QtXml
from PyQt4.QtCore import *
import os

class QgisProject():

    def __init__(self, filename):
        self.filename = filename
        self.projectpath = QFileInfo(os.path.realpath(filename)).path()
        xml = file(unicode(filename)).read()
        self.doc = QtXml.QDomDocument()
        self.doc.setContent(xml)

    def layers(self):
        # build menu on legend schema
        legends = self.doc.elementsByTagName("legend")
        if (legends.length() > 0):
            node = legends.item(0)
            if (node != None):
                node = node.firstChild()
                i = 0
                while not node.isNull():
                    lyr = self._layer_from_legendnode(node)
                    yield lyr
                    node = node.nextSibling()

    def _layer_from_legendnode(self, node):
        element = node.toElement()
        # if legendlayer tag
        if node.nodeName() == "legendlayer":
            legendlayerfileElt = element.firstChild().firstChildElement("legendlayerfile")
            layerId = legendlayerfileElt.attribute("layerid")
            name = element.attribute("name")
            return {"name":name, "layerId": layerId, "file": self.filename}
