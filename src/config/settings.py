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
    
    @property
    def auto_recording(self):
        return self.config.get('auto_recording', {})
    
    @property
    def post_processing(self):
        return self.config.get('post_processing', {})
    
    def update_auto_recording(self, key, value):
        """更新自动录制配置"""
        if 'auto_recording' not in self.config:
            self.config['auto_recording'] = {}
        self.config['auto_recording'][key] = value