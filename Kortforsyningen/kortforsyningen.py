# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Kortforsyningen
                                 A QGIS plugin
 Easy access to WMS from Kortforsyningen (A service by The Danish geodataservice. Styrelsen for Dataforsyning og Effektivisering)
                              -------------------
        begin                : 2015-05-01
        git sha              : $Format:%H$
        copyright            : (C) 2015 Agency for Data supply and Efficiency
        email                : kortforsyningen@gmail.com
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
import json
import codecs
import os.path
import datetime
from urllib2 import (
    urlopen,
    URLError,
    HTTPError
)
from qgis.gui import QgsMessageBar
from qgis.core import *
from PyQt4.QtCore import (
    QCoreApplication,
    QFileInfo,
    QUrl,
    QSettings,
    QTranslator,
    qVersion
)

from PyQt4.QtGui import (
    QAction,
    QIcon,
    QMenu,
    QPushButton
)
from PyQt4 import QtXml
# Initialize Qt resources from file resources.py
from kortforsyningen_settings import(
    KFSettings,
    KFSettingsDialog
)
from kortforsyningen_about import KFAboutDialog
import resources_rc
from qlr_file import QlrFile

# CONFIG_FILE_URL = 'http://apps2.kortforsyningen.dk/qgis_knap_config/Kortforsyningen/themes.json'
CONFIG_FILE_URL = 'http://labs.septima.dk/qgis-kf-knap/kortforsyning_data.qlr'
ABOUT_FILE_URL = 'http://apps2.kortforsyningen.dk/qgis_knap_config/Kortforsyningen/about.html'
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

        self.local_config_file = self.kf_path + 'kortforsyning_data.qlr'
        self.local_about_file = self.kf_path + 'about.html'

        # An error menu object, set to None.
        self.error_menu = None

        # Categories
        self.category_menu_items = []
        self.nodes_by_index = {}
        self.node_count = 0

        # Read the about page
        self.read_about_page()

        # Check if we have a version, and act accordingly
        #self.read_config()

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
        self.category_menu_items = []
        config = self.get_config()
        if config:
            self.qlr_file = QlrFile(config)
            groups_with_layers = self.qlr_file.get_groups_with_layers()
            for group in groups_with_layers:
                category_menu_item = {
                    'name': group['name'],
                    'actions': []
                }
                for layer in group['layers']:
                    if self.user_has_access(layer['service']):
                        category_menu_item['actions'].append({
                            'name': layer['name'],
                            'id': layer['id']
                            }
                        )
                self.category_menu_items.append(category_menu_item)

    def user_has_access(self, service_name):
        #http://services.kortforsyningen.dk/service?request=GetServices&login=septima&password=fgd4Septima
        return True

    def read_config_org(self):
        self.category_menu_items = []
        config = self.get_config()
        if config:
            doc = QtXml.QDomDocument()
            if doc.setContent(config):
                group = QgsLayerTreeGroup()
                #TBD This restarts project 
                QgsLayerDefinition.loadLayerDefinition(doc, group)
                top_nodes = group.children()
                for top_node in top_nodes:
                    category_nodes = top_node.children()
                    for category_node in category_nodes:
                        #Only show categories...
                        if isinstance(category_node, QgsLayerTreeGroup):
                            #... if they are a group 
                            qlr_items = category_node.children()
                            if qlr_items:
                                #... and have children
                                category_menu_item = {
                                    'name': category_node.name(),
                                    'actions': []
                                }
                                for qlr_item in qlr_items:
                                    category_node.takeChild(qlr_item)
                                    name = ""
                                    index = str(self.node_count)
                                    self.nodes_by_index[index] = qlr_item
                                    self.node_count = self.node_count + 1
                                    if isinstance(qlr_item, QgsLayerTreeLayer):
                                        layer = qlr_item.layer()
                                        #name = qlr_item.layerName()
                                        #id = qlr_item.layerId()
                                        name = layer.layerName()
                                        id = layer.layerId()
                                        category_menu_item['actions'].append(
                                            {'name': name,
                                             'node_index': index,
                                             'id': id
                                            }
                                        )
                                    elif isinstance(qlr_item, QgsLayerTreeGroup):
                                        name = qlr_item.name()
                                self.category_menu_items.append(category_menu_item)
                            
    def initGui(self):
        self.read_config()
        self.initMyGui()
        
    def initMyGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/Kortforsyningen/icon.png'

        self.menu = QMenu(self.iface.mainWindow().menuBar())
        self.menu.setObjectName(self.tr('Kortforsyningen'))
        self.menu.setTitle(self.tr('Kortforsyningen'))

        if self.error_menu:
            self.menu.addAction(self.error_menu)

        # Add menu object for each theme
        self.category_menus = []
        for category_menu_item in self.category_menu_items:
            category_menu = QMenu()
            category_menu.setTitle(category_menu_item['name'])
            helper = lambda _id: lambda: self.open_node(_id)
            for action in category_menu_item['actions']:
                q_action = QAction(
                    action['name'], self.iface.mainWindow()
                )
                q_action.triggered.connect(
                    helper(action['id'])
                )
                category_menu.addAction(q_action)
            self.category_menus.append(category_menu)

        for category_menu in self.category_menus:
            self.menu.addMenu(category_menu)

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
        
    def open_node(self, id):
        #node = self.nodes_by_index[node_index]
        #clone = node.clone()
        node = self.qlr_file.get_maplayer_node(id)
        #layers = QgsMapLayerRegistry.instance().mapLayers()
        #layer = QgsMapLayerRegistry.instance().mapLayer(id)
        #QgsProject.instance().layerTreeRoot().addLayer(layer)
        #self.open_layer(self.local_config_file, id)
        QgsProject.instance().read(node)
        layer = QgsMapLayerRegistry.instance().mapLayer(id)
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

    def get_config(self):
        config = None
        load_remote_config = True

        local_file_exists = os.path.exists(self.local_config_file)
        if local_file_exists:
            config = self.read_local_config_file()
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
        return config

    def read_local_config_file(self):
        return file(unicode(self.local_config_file)).read()
        #with codecs.open(self.local_config_file, 'r', 'utf-8') as f:
        #    return f.read()

    def get_remote_config_file(self):
        response = urlopen(CONFIG_FILE_URL)
        content = response.read()
        content = self.replace_variables(content)
        return content

    def write_config_file(self, contents):
        """We only call this function IF we have a new version downloaded"""
        # Remove old versions file
        if os.path.exists(self.local_config_file):
            os.remove(self.local_config_file)

        # Write new version
        with codecs.open(self.local_config_file, 'wU', 'utf-8') as f:
            f.write(contents)

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
        pass
    
    def my_unload(self):
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