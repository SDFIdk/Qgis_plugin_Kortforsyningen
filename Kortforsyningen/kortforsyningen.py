# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Kortforsyningen
                                 A QGIS plugin
 Easy access to WMS from Kortforsyningen (A service by The Danish geodataservice. Styrelsen for Dataforsyning og Effektivisering)
                              -------------------
        begin                : 2015-05-01
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Septima P/S
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
from PyQt4.QtCore import QCoreApplication
from PyQt4.QtCore import QFileInfo
from PyQt4.QtCore import QUrl
from PyQt4.QtGui import QAction, QIcon, QMenu, QPushButton
from PyQt4 import QtXml
from qgis.gui import QgsMessageBar
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources_rc
from kortforsyningen_settings import KFSettings, KFSettingsDialog
import os.path
import datetime
from urllib2 import urlopen, URLError, HTTPError
import json
import codecs
from kortforsyningen_about import KFAboutDialog
from PyQt4.QtCore import QSettings, QTranslator, qVersion

from project import QgisProject
CONFIG_FILE_URL = 'http://apps2.kortforsyningen.dk/qgis_knap_config/Kortforsyningen/themes.json'
ABOUT_FILE_URL = 'http://labs-develop.septima.dk/qgis-kf-knap/about.html'
FILE_MAX_AGE = datetime.timedelta(hours=12)


def log_message(message):
    QgsMessageLog.logMessage(message, 'Kortforsyningen plugin')


class Kortforsyningen:
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
        if not os.path.exists(self.kf_path):
            os.makedirs(self.kf_path)

        self.local_config_file = self.kf_path + 'themes.json'
        self.local_about_file = self.kf_path + 'about.html'

        # An error menu object, set to None.
        self.error_menu = None

        # Categories
        self.categories = []

        # Read the about page
        self.read_about_page()

        # Check if we have a version, and act accordingly
        self.read_config()

        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.path,
            'i18n',
            '{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

    def read_about_page(self):
        load_remote_about = True

        local_file_exists = os.path.exists(self.local_about_file)
        if local_file_exists:
            local_file_time = datetime.datetime.fromtimestamp(
                os.path.getmtime(self.local_about_file)
            )
            load_remote_about = local_file_time < datetime.datetime.now() - FILE_MAX_AGE

        if load_remote_about:
            try:
                response = urlopen(ABOUT_FILE_URL)
                about = response.read()
            except Exception, e:
                log_message('No contact to the configuration at ' + ABOUT_FILE_URL + '. Exception: ' + str(e))
                if not local_file_exists:
                    self.error_menu = QAction(
                        self.tr('No contact to Kortforsyning'),
                        self.iface.mainWindow()
                    )
                return
            self.write_about_file(about)

    def write_about_file(self, content):
        if os.path.exists(self.local_about_file):
            os.remove(self.local_about_file)

        with codecs.open(self.local_about_file, 'w') as f:
            f.write(content)

    def read_config(self):
        config = None
        load_remote_config = True

        local_file_exists = os.path.exists(self.local_config_file)
        if local_file_exists:
            config = self.get_local_config_file()
            local_file_time = datetime.datetime.fromtimestamp(
                os.path.getmtime(self.local_config_file)
            )
            load_remote_config = local_file_time < datetime.datetime.now() - FILE_MAX_AGE

        if load_remote_config:
            try:
                config = self.get_remote_config_file()
            except Exception, e:
                log_message(u'No contact to the configuration at ' + CONFIG_FILE_URL + '. Exception: ' + str(e))
                if not local_file_exists:
                    self.error_menu = QAction(
                        self.tr('No contact to Kortforsyningen'),
                        self.iface.mainWindow()
                    )
                return
            self.write_config_file(config)

        self.categories = config["categories"]
        self.update_qgs_files(config)

    def get_local_config_file(self):
        with codecs.open(self.local_config_file, 'rU', 'utf-8') as f:
            return json.loads(f.read())

    def get_remote_config_file(self):
        response = urlopen(CONFIG_FILE_URL)
        content = response.read()
        return json.loads(content)

    def write_config_file(self, response):
        """We only call this function IF we have a new version downloaded"""
        # Remove old versions file
        if os.path.exists(self.local_config_file):
            os.remove(self.local_config_file)

        # Write new version
        with codecs.open(self.local_config_file, 'w', 'utf-8') as f:
            json.dump(response, f)

    def update_qgs_files(self, config):
        self.categories = config['categories']
        for category in self.categories:
            url = category['url']
            filepath = self.kf_path + url.rsplit('/', 1)[-1]
            if os.path.exists(filepath):
                file_time = datetime.datetime.fromtimestamp(
                    os.path.getmtime(filepath)
                )
                if file_time > datetime.datetime.now() - FILE_MAX_AGE:
                    continue

            try:
                f = urlopen(url)
                # Write the file as filename to kf_path
                with codecs.open(filepath, "wb") as local_file:
                    local_file.write(f.read())
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
        return QCoreApplication.translate('Kortforsyningen', message)

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
                self.tr('Error'), self.tr('Please, fill out username and password')
            )
            settings_btn = QPushButton(widget)
            settings_btn.setText(self.tr('Settings'))
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
        if layer:
            self.iface.legendInterface().refreshLayerSymbology(layer)
            self.iface.legendInterface().moveLayer(layer, 0)
            self.iface.legendInterface().refreshLayerSymbology(layer)
            return layer
        else:
            print "Could not load layer"
            widget = self.iface.messageBar().createMessage(
                self.tr('Error'), self.tr('Could not load the layer. Is username and password correct?')
            )
            settings_btn = QPushButton(widget)
            settings_btn.setText(self.tr("Settings"))
            settings_btn.pressed.connect(self.settings_dialog)
            widget.layout().addWidget(settings_btn)
            self.iface.messageBar().pushWidget(widget, QgsMessageBar.CRITICAL)
            return None


    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/Kortforsyningen/icon.png'

        self.menu = QMenu(self.iface.mainWindow().menuBar())
        self.menu.setObjectName(self.tr('Kortforsyningen'))
        self.menu.setTitle(self.tr('Kortforsyningen'))

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
            self.tr('Settings'),
            self.iface.mainWindow()
        )
        self.settings_menu.setObjectName(self.tr('Settings'))
        self.settings_menu.triggered.connect(self.settings_dialog)
        self.menu.addAction(self.settings_menu)

        # Add about
        self.about_menu = QAction(
            self.tr('About the plugin'),
            self.iface.mainWindow()
        )
        self.about_menu.setObjectName(self.tr('About the plugin'))
        self.about_menu.triggered.connect(self.about_dialog)
        self.menu.addAction(self.about_menu)

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

    def about_dialog(self):
        dlg = KFAboutDialog()
        dlg.webView.setUrl(QUrl(self.local_about_file))
        dlg.webView.urlChanged
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