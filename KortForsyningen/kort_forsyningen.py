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
from PyQt4.QtGui import QAction, QIcon, QMenu, QPushButton
from PyQt4 import QtXml
from qgis.gui import QgsMessageBar
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources_rc
from kort_forsyningen_settings import KFSettings, KFSettingsDialog
import os.path
from urllib2 import urlopen, URLError, HTTPError
import json
import codecs

from project import QgisProject

KF_NEDE = 'http://develop.septima.dk/qgis-kf-knap/themes.json'
CONFIG_FILE_URL = 'http://labs-develop.septima.dk/qgis-kf-knap/themes.json'
# CONFIG_FILE_URL = KF_NEDE


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

        # An error menu object, set to None.
        self.error_menu = None

        # Categories
        self.categories = []

        # Check if we have a version, and act accordingly
        self.read_config()

    def read_config(self):
        config = self.get_remote_config_file()
        local_file_exists = os.path.exists(self.local_config_file)
        service_unavailable = config == 'HTTPError' or config == 'URLError'

        if service_unavailable:
            if local_file_exists:
                config = self.get_local_config_file()
            else:
                self.error_menu = QAction(
                    # possibly add an error icon?
                    # QIcon(error_path),
                    self.tr('Ingen kontakt til kortforsyningen'),
                    self.iface.mainWindow()
                )
                return
        else:
            if local_file_exists:
                # We have the latest config file locally
                if self.check_local_config(remote_config=config):
                    config = self.get_local_config_file()
                # We download new config file and qgs files
                else:
                    self.get_qgs_files(config)
            else:
                # We haven't got anything locally
                self.get_qgs_files(config)

        self.categories = config["categories"]

    def check_local_config(self, remote_config):
        remote_version = remote_config['version']

        if os.path.exists(self.local_config_file):
            with codecs.open(self.local_config_file, 'rU', 'utf-8') as f:
                local_config = json.loads(f.read())

            return local_config['version'] == remote_version

        return False

    def get_local_config_file(self):
        with codecs.open(self.local_config_file, 'rU', 'utf-8') as f:
            return json.loads(f.read())

    def get_remote_config_file(self):
        try:
            response = urlopen(CONFIG_FILE_URL)
            response = json.load(response)
            return response
        except HTTPError:
            return 'HTTPError'
        except URLError:
            return 'URLError'

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
                filepath = self.kf_path + url.rsplit('/', 1)[-1]
                # Write the file as filename to kf_path
                with codecs.open(filepath, "wb") as local_file:
                    local_file.write(f.read())

                # We download new files, write new version file
                self.write_config_file(config)

            except HTTPError, e:
                self.error_list.append(
                    'HTTP Error: {} {}'.format(e.code, url)
                )
            except URLError, e:
                self.error_list.append(
                    'URL Error: {} {}'.format(e.reason, url)
                )

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
            if idNode is not None:
                child = idNode.firstChild().toText().data()
                # layer found
                if child == value:
                    return node
            i += 1
        return None

    def replace_variables(self, text):
        """
        :param text: Input text
        :return: text where variables has been replaced
        """
        # TODO: If settings are not set then show the settings dialog
        replace_vars = {}
        replace_vars["kf_username"] = self.settings.value('username')
        replace_vars["kf_password"] = self.settings.value('password')
        for i, j in replace_vars.iteritems():
            text = text.replace("{{" + str(i) + "}}", str(j))
        return text

    def settings_set(self):
        if self.settings.value('username') and self.settings.value('password'):
            return True

        return False

    def open_layer(self, filename, layerid):
        """Opens the specified layerid"""
        # If settings are not set, ask user to set them
        if not self.settings_set():
            widget = self.iface.messageBar().createMessage(
                'Fejl', 'Udfyld venligst brugernavn og kodeord.'
            )
            settings_btn = QPushButton(widget)
            settings_btn.setText("Indstillinger")
            settings_btn.pressed.connect(self.settings_dialog)
            widget.layout().addWidget(settings_btn)
            self.iface.messageBar().pushWidget(widget, QgsMessageBar.CRITICAL)
            return

        with open(filename, 'r') as f:
            xml = f.read()
        xml = self.replace_variables(xml)
        # QtXml takes only bytes. We cant give it unicode.
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

        if self.error_menu:
            self.menu.addAction(self.error_menu)

        # Add menu object for each theme
        self.category_menus = []
        for category in self.categories:
            filename = category['url'].rsplit('/', 1)[-1]
            theme_menu = QMenu()
            theme_menu.setObjectName(filename)
            theme_menu.setTitle(self.tr(category['name']))
            project = QgisProject(self.kf_path + filename)
            helper = lambda _f, _layer: lambda: self.open_layer(_f, _layer)
            for layer in project.layers():
                action = QAction(
                    self.tr(layer['name']), self.iface.mainWindow()
                )
                action.triggered.connect(
                    helper(layer['file'], layer['layerId'])
                )
                theme_menu.addAction(action)
            self.category_menus.append(theme_menu)

        for submenu in self.category_menus:
            self.menu.addMenu(submenu)

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
        # Remove the submenus
        for submenu in self.category_menus:
            submenu.deleteLater()
        # remove the menu bar item
        self.menu.deleteLater()
