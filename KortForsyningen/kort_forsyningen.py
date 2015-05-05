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
# Initialize Qt resources from file resources.py
import resources_rc
from kort_forsyningen_settings import KFSettings, KFSettingsDialog
import os.path
from urllib2 import urlopen, URLError, HTTPError
import json

KF_FILES_URL = 'http://telling.xyz/uploads/FyfOyBvzU8.json'

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

        # Check if we have stored settings, if so, load them.
        self.kf_path = self.path + '/kf/'
        if os.path.exists(self.kf_path + 'kfs.txt'):
            self.settings.setValue('remember_settings', True)
            with open(self.kf_path + 'kfs.txt', 'rU') as f:
                self.settings.setValue('username', f.readline().strip())
                self.settings.setValue('password', f.readline().strip())

        # Get json file with information about themes
        try:
            response = urlopen(KF_FILES_URL)
            response = json.load(response)
            self.themes = response['themes']
            self.download_qgs_files(self.themes)
        except HTTPError, e:
            # TODO: Maybe show a dialog?
            print "HTTP Error:", e.code, url
        except URLError, e:
            print "URL Error:", e.reason, url

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # Create the dialog (after translation) and keep reference
        #self.dlg = KortForsyningenDialog()
        #self.dlg = KFSettingsDialog()

        ## Declare instance attributes
        self.actions = []
        #self.menu = self.tr(u'&Kort Forsyningen')
        ## TODO: We are going to let the user set this up in a future iteration
        #self.toolbar = self.iface.addToolBar(u'KortForsyningen')
        #self.toolbar.setObjectName(u'KortForsyningen')

    def download_qgs_files(self, themes):
        for theme in themes:
            url = theme['url']
            try:
                f = urlopen(url)
                with open(self.kf_path + url.rsplit('/',1)[-1], "wb") as local_file:
                    local_file.write(f.read())

            except HTTPError, e:
                # TODO: Maybe show a dialog?
                print "HTTP Error:", e.code, url
            except URLError, e:
                print "URL Error:", e.reason, url


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


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/KortForsyningen/icon.png'

        self.menu = QMenu(self.iface.mainWindow().menuBar())
        self.menu.setObjectName('KortForsyningen')
        self.menu.setTitle(self.tr('KortForsyningen'))

        # Add menu object for each theme
        self.theme_menus = []
        for elem in self.themes:
            theme_menu = QMenu()
            theme_menu.setObjectName(elem['url'])
            theme_menu.setTitle(self.tr(elem['name']))
            self.theme_menus.append(theme_menu)

        for menu in self.theme_menus:
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

        # We get 1 if ok, 0 if cancel
        success = dlg.exec_()
        if success:
            if self.settings.value('remember_settings'):
                with open(self.kf_path + '/kfs.txt', 'w') as f:
                    f.write(self.settings.value('username') + '\n')
                    f.write(self.settings.value('password') + '\n')

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Kort Forsyningen'),
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
