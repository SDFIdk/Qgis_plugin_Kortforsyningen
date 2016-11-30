from kf_config import KfConfig
from local_config import LocalConfig

class Config:

    def __init__(self, settings):
        self.settings = settings
        self.kf_config = KfConfig(settings)
        self.local_config = LocalConfig(settings)
        self.reload()
        
    def reload(self):
        self.categories = []
        if self.settings.value('use_custom_qlr_file') and self.settings.value('kf_only_background'):
            self.kf_categories = []
            background_category = self.kf_config.get_background_category()
            if background_category:
                self.kf_categories.append(background_category)
        else:
            self.kf_categories = self.kf_config.get_categories()
        self.local_categories = self.local_config.get_categories()
        self.categories = self.kf_categories + self.local_categories

    def get_categories(self):
        return self.categories

    def get_kf_maplayer_node(self, id):
        return self.kf_config.get_maplayer_node(id)
    
    def get_local_maplayer_node(self, id):
        return self.local_config.get_maplayer_node(id)
