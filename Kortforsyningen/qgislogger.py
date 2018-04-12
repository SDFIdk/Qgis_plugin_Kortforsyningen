from qgis.core import (
    QgsMessageLog,
    QgsDataSourceURI
)

class QgisLogger(object):
    def __init__(self, plugin_name):
        self.pluginname = plugin_name

    def log(self, message, level=QgsMessageLog.INFO):
        QgsMessageLog.logMessage(
            '{}'.format(message),
            self.pluginname,
            level
        )

    def info(self, message):
        self.log(message, level=QgsMessageLog.INFO)

    def warning(self, message):
        self.log(message, level=QgsMessageLog.WARNING)

    def critical(self, message):
        self.log(message, level=QgsMessageLog.CRITICAL)
