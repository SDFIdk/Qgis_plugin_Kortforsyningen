from kf_config import KfConfig
from local_config import LocalConfig
from PyQt4 import (
    QtCore
)

class Config(QtCore.QObject):

    con_loaded = QtCore.pyqtSignal()
    kf_con_error = QtCore.pyqtSignal(str)
    kf_settings_warning = QtCore.pyqtSignal()
            
    def __init__(self, settings, networkManager):
        super(Config, self).__init__()
        self.settings = settings
        self.kf_config = KfConfig(settings, networkManager)
        self.kf_config.kf_con_error.connect(self.propagate_kf_con_error)
        self.kf_config.kf_con_success.connect(self.kf_config_loaded)
        self.kf_config.kf_settings_warning.connect(self.propagate_kf_settings_warning)

        self.local_config = LocalConfig(settings)

    def propagate_kf_settings_warning(self):
        self.kf_settings_warning.emit()
        self.con_loaded.emit()
        
    def propagate_kf_con_error(self, message):
        self.kf_con_error.emit(message)
        self.con_loaded.emit()
        
    def load(self):
        self.categories = []
        self.categories_list = []
        self.local_config.load()
        self.kf_config.load()

    def kf_config_loaded(self):
        if self.settings.value('use_custom_qlr_file') and self.settings.value('kf_only_background'):
            self.kf_categories = []
            background_category = self.kf_config.get_background_category()
            if background_category:
                self.kf_categories.append(background_category)
        else:
            self.kf_categories = self.kf_config.get_categories()
        self.local_categories = self.local_config.get_categories()
        
        self.categories = self.kf_categories + self.local_categories
        
        self.categories_list.append(self.kf_categories)
        self.categories_list.append(self.local_categories)
        self.con_loaded.emit()
        
    def get_category_lists(self):
        return self.categories_list
    
    def get_categories(self):
        return self.categories

    def get_kf_maplayer_node(self, id):
        return self.kf_config.get_maplayer_node(id)
    
    def get_local_maplayer_node(self, id):
        return self.local_config.get_maplayer_node(id)
