"""
This file contains all the PCEF QtDesigner plugins
"""
# This only works with PyQt, PySide does not support the QtDesigner module
import os
import pcef
from PyQt4.QtGui import QApplication

os.environ.setdefault("QT_API", "pyqt")
from PyQt4 import QtDesigner


class QCodeEditPlugin(QtDesigner.QPyDesignerCustomWidgetPlugin):
    """Designer plugin for pcef.QCodeEdit.
    Also serves as base class for other custom widget plugins."""

    _module = 'pcef.core.editor'        # path to the widget's module
    _class = 'QCodeEdit'    # name of the widget class
    _icon = None

    def __init__(self, parent=None):
        QtDesigner.QPyDesignerCustomWidgetPlugin.__init__(self)
        self.initialized = False

    def initialize(self, formEditor):
        self.initialized = True

    def isInitialized(self):
        return self.initialized

    def isContainer(self):
        return False

    def icon(self):
        return None

    def domXml(self):
        return '<widget class="%s" name="%s">\n</widget>\n' % (self._class,
                                                               self.name())

    def group(self):
        return 'pcef'

    def includeFile(self):
        return self._module

    def name(self):
        return self._class

    def toolTip(self):
        return ''

    def whatsThis(self):
        return ''

    def createWidget(self, parent):
        return pcef.QCodeEdit(parent)


if __name__ == '__main__': # some tests
    app = QApplication([])
    plugin = QCodeEditPlugin()
    print(plugin)
    print(plugin.includeFile())
    print(plugin.name())
    print(plugin.group())
    widget = plugin.createWidget(None)
    widget.show()
    app.exec_()