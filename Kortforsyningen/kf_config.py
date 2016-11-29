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
    QFile,
    QUrl,
    QSettings,
    QTranslator,
    qVersion,
    QIODevice
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
    KFSettings
)
import resources_rc
from qlr_file import QlrFile

FILE_MAX_AGE = datetime.timedelta(hours=12)
KF_SERVICES_URL = 'http://services.kortforsyningen.dk/service?request=GetServices&login={{kf_username}}&password={{kf_password}}'

def log_message(message):
    QgsMessageLog.logMessage(message, 'Kortforsyningen plugin')

class KfConfig:

    def __init__(self, settings):
        self.settings = settings
        self.reload()
    
    def reload(self):
        self.cached_kf_qlr_filename = self.settings.value('cache_path') + 'kortforsyning_data.qlr'
        self.allowed_kf_services = {}
        if self.settings.is_set():
            self.allowed_kf_services = self.get_allowed_kf_services()
            
            self.kf_qlr_file = self.get_kf_qlr_file()
            self.categories = self.get_kf_categories()

    def get_allowed_kf_services(self):
        allowed_kf_services = {}
        allowed_kf_services['any_type'] = {'services': []}
        url_to_get = self.replace_variables(KF_SERVICES_URL)
        response = urlopen(url_to_get)
        xml = response.read()
        doc = QtXml.QDomDocument()
        doc.setContent(xml)
        service_types = doc.documentElement().childNodes()
        i = 0
        while i<service_types.count():
            service_type = service_types.at(i)
            service_type_name= service_type.nodeName()
            allowed_kf_services[service_type_name] = {'services': []}
            services = service_type.childNodes()
            j = 0
            while j<services.count():
                service = services.at(j)
                service_name = service.nodeName()
                allowed_kf_services[service_type_name]['services'].append(service_name)
                allowed_kf_services['any_type']['services'].append(service_name)
                j = j + 1
            i = i + 1
        return allowed_kf_services

    def get_categories(self):
         return self.categories
         
    def get_maplayer_node(self, id):
         return self.kf_qlr_file.get_maplayer_node(id)
     
    def get_kf_categories(self):
        kf_categories = []
        groups_with_layers = self.kf_qlr_file.get_groups_with_layers()
        for group in groups_with_layers:
            kf_category = {
                'name': group['name'],
                'selectables': []
            }
            for layer in group['layers']:
                if self.user_has_access(layer['service']):
                    kf_category['selectables'].append({
                        'type': 'layer',
                        'source': 'kf',
                        'name': layer['name'],
                        'id': layer['id']
                        }
                    )
            if len(kf_category['selectables']) > 0:
                kf_categories.append(kf_category)
        return kf_categories

    def user_has_access(self, service_name):
        return service_name in self.allowed_kf_services['any_type']['services']

    def get_custom_categories(self):
        return []

    def get_kf_qlr_file(self):
        config = None
        load_remote_config = True

        local_file_exists = os.path.exists(self.cached_kf_qlr_filename)
        if local_file_exists:
            config = self.read_cached_kf_qlr()
            local_file_time = datetime.datetime.fromtimestamp(
                os.path.getmtime(self.cached_kf_qlr_filename)
            )
            load_remote_config = local_file_time < datetime.datetime.now() - FILE_MAX_AGE

        if load_remote_config:
            try:
                config = self.get_remote_kf_qlr()
            except Exception, e:
                log_message(u'No contact to the configuration at ' + self.settings.value('kf_qlr_url') + '. Exception: ' + str(e))
                if not local_file_exists:
                    self.error_menu = QAction(
                        self.tr('No contact to Kortforsyningen'),
                        self.iface.mainWindow()
                    )
                return
            self.write_cached_kf_qlr(config)
        if config:
            config = self.read_cached_kf_qlr()
            return QlrFile(config)
        else:
            return None

    def read_cached_kf_qlr(self):
        #return file(unicode(self.cached_kf_qlr_filename)).read()
        f = QFile(self.cached_kf_qlr_filename)
        f.open(QIODevice.ReadOnly)
        return f.readAll()

        #with codecs.open(self.cached_kf_qlr_filename, 'r', 'utf-8') as f:
        #    return f.read()

    def get_remote_kf_qlr(self):
        response = urlopen(self.settings.value('kf_qlr_url'))
        content = response.read()
        content = unicode(content, 'utf-8')
        content = self.replace_variables(content)
        return content

    def write_cached_kf_qlr(self, contents):
        """We only call this function IF we have a new version downloaded"""
        # Remove old versions file
        if os.path.exists(self.cached_kf_qlr_filename):
            os.remove(self.cached_kf_qlr_filename)

        # Write new version
        with codecs.open(self.cached_kf_qlr_filename, 'w', 'utf-8') as f:
            f.write(contents)

    def replace_variables(self, text):
        """
        :param text: Input text
        :return: text where variables has been replaced
        """
        # TODO: If settings are not set then show the settings dialog
        result = text
        replace_vars = {}
        replace_vars["kf_username"] = self.settings.value('username')
        replace_vars["kf_password"] = self.settings.value('password')
        for i, j in replace_vars.iteritems():
            result = result.replace("{{" + str(i) + "}}", str(j))
        return result



