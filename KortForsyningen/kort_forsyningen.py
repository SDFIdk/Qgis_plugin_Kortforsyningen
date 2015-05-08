# -*- coding: utf-8 -*-
"""
/***************************************************************************
 KortForsyningen
                                 A QGIS plugin
 Nem adgang til kortforsyningens wms
                              -------------------
        begin                : 2015-05-01
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Septima P/S
        email                : kontakt@septima.dk
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtCore import QFileInfo
from PyQt4.QtGui import QAction, QIcon, QMenu
from PyQt4 import QtXml
from qgis.gui import QgsMessageBar
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources_rc
from kort_forsyningen_settings import KFSettings, KFSettingsDialog
import os.path
from urllib2 import urlopen, URLError, HTTPError
import json

from project import QgisProject

CONFIG_FILE_URL = 'http://labs-develop.septima.dk/qgis-kf-knap/themes.json'

class KortForsyningen:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        self.settings = KFSettings()
        self.path = QFileInfo(os.path.realpath(__file__)).path()

        self.kf_path = self.path + '/kf/'
        self.local_config_file = self.kf_path + 'themes.json'

        # List of error strings to be shown
        self.error_list = []

        ## Declare instance attributes
        self.actions = []

        # Categories
        self.categories = []

        # Check if we have a version, and act accordingly
        self.read_config()

    def read_config(self):
        config = self.get_remote_config_file()
        # Fall back to local copy
        if not config:
            config = self.get_local_config_file()
        if not config:
            # TODO: Handle gracefully
            print "Kunne ikke hente konfiguration"
        self.get_qgs_files(config)
        self.categories = config["categories"]


    def check_remote_themes(self, remote_file):
        remote_version = remote_file['version']

        if os.path.exists(self.local_config_file):
            with open(self.local_config_file, 'rU') as f:
                local_config = f.read()
                local_config = json.loads(local_config)

            return local_config['version'] == remote_version

        return False

    def get_local_config_file(self):
        with open(self.local_config_file, 'rU') as f:
            return json.loads( f )


    def get_remote_config_file(self):
        try:
            response = urlopen(CONFIG_FILE_URL)
            response = json.load(response)
            return response
        except HTTPError, e:
            # TODO: Maybe show a dialog?
            print "HTTP Error:", e.code, url
        except URLError, e:
            print "URL Error:", e.reason, url

    def write_config_file(self, response):
        """We only call this function IF we have a new version downloaded"""
        # Remove old versions file
        if os.path.exists(self.local_config_file):
            os.remove(self.local_config_file)

        # Write new version
        with open(self.local_config_file, 'w') as f:
            json.dump(response, f)


    def get_qgs_files(self, config):
        self.categories = config['categories']
        for category in self.categories:
            url = category['url']
            try:
                f = urlopen(url)
                # Write the file as filename to kf_path
                with open(self.kf_path + url.rsplit('/', 1)[-1], "wb") as local_file:
                    local_file.write(f.read())

                # We download new files, write new version file
                self.write_config_file(config)

            except HTTPError, e:
                self.error_list.append('HTTP Error: {} {}'.format(e.code, url))
            except URLError, e:
                self.error_list.append('URL Error: {} {}'.format(e.reason, url))

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('KortForsyningen', message)

    # Taken directly from menu_from_project
    def getFirstChildByTagNameValue(self, elt, tagName, key, value):
        nodes = elt.elementsByTagName(tagName)
        i = 0
        while i < nodes.count():
            node = nodes.at(i)
            idNode = node.namedItem(key)
            if idNode != None:
                id = idNode.firstChild().toText().data()
                # layer founds
                if id == value:
                    return node
            i += 1
        return None

    def open_layer(self, filename, layerid):
        """Opens the specified layerid"""
        xml = file(unicode(filename)).read()
        doc = QtXml.QDomDocument()
        doc.setContent(xml)
        node = self.getFirstChildByTagNameValue(
            doc.documentElement(), 'maplayer', 'id', layerid
        )
        QgsProject.instance().read(node)
        layer = QgsMapLayerRegistry.instance().mapLayer(layerid)
        self.iface.legendInterface().refreshLayerSymbology(layer)
        self.iface.legendInterface().moveLayer(layer, 0)
        self.iface.legendInterface().refreshLayerSymbology(layer)

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/KortForsyningen/icon.png'

        self.menu = QMenu(self.iface.mainWindow().menuBar())
        self.menu.setObjectName('KortForsyningen')
        self.menu.setTitle(self.tr('KortForsyningen'))

        # Add menu object for each theme
        self.category_menus = []
        for elem in self.categories:
            filename = elem['url'].rsplit('/', 1)[-1]
            theme_menu = QMenu()
            theme_menu.setObjectName(filename)
            theme_menu.setTitle(self.tr(elem['name']))
            project = QgisProject(self.kf_path + filename)
            helper = lambda _file, _layerId: lambda: self.open_layer(_file, _layerId)
            for layer in project.layers():
                action = QAction(
                        self.tr(layer['name']), self.iface.mainWindow()
                )
                action.triggered.connect(
                        helper(layer['file'], layer['layerId'])
                )
                theme_menu.addAction(action)
            self.category_menus.append(theme_menu)

        for menu in self.category_menus:
            self.menu.addMenu(menu)

        # Seperate settings from actual content
        self.menu.addSeparator()

        # Add settings
        self.settings_menu = QAction(
                QIcon(icon_path),
                self.tr('Indstillinger'),
                self.iface.mainWindow()
        )
        self.settings_menu.setObjectName('Indstillinger')
        self.settings_menu.triggered.connect(self.settings_dialog)
        self.menu.addAction(self.settings_menu)

        menu_bar = self.iface.mainWindow().menuBar()
        menu_bar.insertMenu(
            self.iface.firstRightStandardMenu().menuAction(), self.menu
        )



    def settings_dialog(self):
        dlg = KFSettingsDialog(self.settings)
        dlg.setWidgetsFromValues()
        dlg.show()
        result = dlg.exec_()

        if result == 1:
            del dlg

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        # Remove settings if user not asked to keep them
        if self.settings.value('remember_settings') is False:
            self.settings.setValue('username', '')
            self.settings.setValue('password', '')
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&KortForsyningen'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the menu bar item
        del self.menu


    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        #self.dlg.show()
        # Run the dialog event loop
        #result = self.dlg.exec_()
        # See if OK was pressed
        #if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            #pass
