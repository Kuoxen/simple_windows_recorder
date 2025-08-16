import yaml
import os

class Settings:
    def __init__(self, config_path="config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
    
    @property
    def audio(self):
        return self.config['audio']
    
    @property
    def recording(self):
        return self.config['recording']
    
    @property
    def upload(self):
        return self.config['upload']