import codecs
import os.path
import datetime
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
from PyQt4.QtNetwork import *
from functools import partial
from PyQt4.QtGui import (
    QAction,
    QIcon,
    QMenu,
    QPushButton
)

from PyQt4 import (
    QtCore,
    QtXml
)
import json

# Initialize Qt resources from file resources.py
from kortforsyningen_settings import(
    KFSettings
)
import resources_rc
from qlr_file import QlrFile
from qgislogger import QgisLogger

FILE_MAX_AGE = datetime.timedelta(hours=0)
KF_SERVICES_URL = 'http://services.kortforsyningen.dk/service?request=GetServices&login={{kf_username}}&password={{kf_password}}'

def log_message(message):
    QgsMessageLog.logMessage(message, 'Kortforsyningen plugin')

class KfConfig(QtCore.QObject):
    
    kf_con_success = QtCore.pyqtSignal()
    kf_con_error = QtCore.pyqtSignal(str)
    kf_settings_warning = QtCore.pyqtSignal()

    def __init__(self, settings, networkManager):
        super(KfConfig, self).__init__()
        self.settings = settings
        self.networkManager = networkManager
        self.allowed_kf_services = None
        self.kf_qlr_file = None

    def load(self):
        self.cached_kf_qlr_filename = self.settings.value('cache_path') + 'kortforsyning_data.qlr'
        self.allowed_kf_services = {}
        if self.settings.is_set():
            self.get_allowed_kf_services()
        else:
            self.kf_settings_warning.emit()
            self.background_category = None
            self.categories = []

    def get_allowed_kf_services(self):
        try:
            url_to_get = self.replace_variables(KF_SERVICES_URL)
            reply = self.networkManager.get(QNetworkRequest( QUrl(url_to_get) ))
            func = partial(self.got_allowed_kf_services_handler, reply)
            #func = lambda : self.got_allowed_kf_services_handler( reply)
            reply.finished.connect(func)
            #reply.error.connect(self.report_network_error)
        except Exception as e:
            log_message("get_allowed_kf_services.except: " + str(e))
        #reply.error.connect(self.report_network_error)
        
    def report_network_error(self, message):
        full_msg = "Network Error: " + message
        self.kf_con_error.emit(full_msg)
        self.background_category = None
        self.categories = []
        
    def got_allowed_kf_services_handler(self, reply):
        if reply.error() == QNetworkReply.NoError:
            #log_message("got_allowed_kf_services_handler")
            allowed_kf_services = {}
            allowed_kf_services['any_type'] = {'services': []}
            xml = str(reply.readAll())
            #reponse = self.get_allowed_kf_services_reply.readAll()
            #reponse = networkReply.readAll()
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
            self.allowed_kf_services = allowed_kf_services
            self.debug_write_allowed_services()
            self.get_kf_qlr_file()
        else:
            self.report_network_error("allowed services" + reply.errorString())

    def get_kf_qlr_file(self):
        #log_message("get_kf_qlr_file")
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
            self.get_remote_kf_qlr()
        else:
            config = self.read_cached_kf_qlr()
            self.kf_qlr_file =  QlrFile(config)
            self.background_category, self.categories = self.get_kf_categories()
            self.kf_con_success.emit()

    def get_remote_kf_qlr(self):
        #log_message("get_remote_kf_qlr: " + self.settings.value('kf_qlr_url'))
        reply = self.networkManager.get(QNetworkRequest(  QUrl(self.settings.value('kf_qlr_url')) ))
        func = partial(self.got_remote_kf_qlr, reply)
        #func = lambda: self.got_remote_kf_qlr( reply)
        reply.finished.connect(func)
        #reply.error.connect(self.report_network_error)

    def got_remote_kf_qlr(self, reply):
        if reply.error() == QNetworkReply.NoError:
            content = reply.readAll()
            content = unicode(content, 'utf-8')
            content = self.replace_variables(content)
    
            self.write_cached_kf_qlr(content)
            config = self.read_cached_kf_qlr()
            self.kf_qlr_file =  QlrFile(config)
            self.background_category, self.categories = self.get_kf_categories()
            self.kf_con_success.emit()
        else:
            self.report_network_error("Remote qlr" + reply.errorString())

    def get_categories(self):
         return self.categories
         
    def get_background_category(self):
         return self.background_category

    def get_maplayer_node(self, id):
         return self.kf_qlr_file.get_maplayer_node(id)
     
    def get_kf_categories(self):
        kf_categories = []
        kf_background_category = None
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
                if group['name'] == 'Baggrundskort':
                    kf_background_category = kf_category
        return kf_background_category, kf_categories

    def user_has_access(self, service_name):
        return service_name in self.allowed_kf_services['any_type']['services']

    def get_custom_categories(self):
        return []

    def read_cached_kf_qlr(self):
        #return file(unicode(self.cached_kf_qlr_filename)).read()
        f = QFile(self.cached_kf_qlr_filename)
        f.open(QIODevice.ReadOnly)
        return f.readAll()

        #with codecs.open(self.cached_kf_qlr_filename, 'r', 'utf-8') as f:
        #    return f.read()

    def write_cached_kf_qlr(self, contents):
        """We only call this function IF we have a new version downloaded"""
        # Remove old versions file
        if os.path.exists(self.cached_kf_qlr_filename):
            os.remove(self.cached_kf_qlr_filename)

        # Write new version
        with codecs.open(self.cached_kf_qlr_filename, 'w', 'utf-8') as f:
            f.write(contents)

    def debug_write_allowed_services(self):
        try:
            debug_filename = self.settings.value('cache_path') + self.settings.value('username') + '.txt'
            if os.path.exists(debug_filename):
                os.remove(debug_filename)
            with codecs.open(debug_filename, 'w', 'utf-8') as f:
                f.write(json.dumps(self.allowed_kf_services['any_type']['services'], indent=2).replace('[', '').replace(']', ''))
        except Exception, e:
            pass

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



