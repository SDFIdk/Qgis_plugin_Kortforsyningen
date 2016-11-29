from kf_config import KfConfig
from local_config import LocalConfig

class Config:

    def __init__(self, settings):
        self.kf_config = KfConfig(settings)
        self.local_config = LocalConfig(settings)
        self.reload()
        
    def reload(self):
        self.categories = []
        self.kf_categories = self.kf_config.get_categories()
        self.local_categories = self.local_config.get_categories()
        self.categories = self.kf_categories + self.local_categories

    def get_categories(self):
        return self.categories

    def get_kf_maplayer_node(self, id):
        return self.kf_config.get_maplayer_node(id)
    
    def get_local_maplayer_node(self, id):
        return self.local_config.get_maplayer_node(id)
