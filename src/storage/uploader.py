import requests
import os
import threading
from datetime import datetime

class FileUploader:
    def __init__(self, settings):
        self.settings = settings
        self.upload_config = settings.upload
        
    def upload_files(self, mic_file, system_file, call_info, callback=None):
        """
        上传录音文件到服务器
        
        Args:
            mic_file: 麦克风录音文件路径
            system_file: 系统音频录音文件路径
            call_info: 通话信息字典 {'agent_phone': '', 'customer_name': '', 'customer_id': ''}
            callback: 上传完成回调函数
        """
        if not self.upload_config.get('enabled', False):
            if callback:
                callback(False, "上传功能未启用")
            return
        
        # 异步上传
        upload_thread = threading.Thread(
            target=self._upload_worker,
            args=(mic_file, system_file, call_info, callback)
        )
        upload_thread.daemon = True
        upload_thread.start()
    
    def _upload_worker(self, mic_file, system_file, call_info, callback):
        """上传工作线程"""
        try:
            upload_url = self.upload_config.get('url')
            if not upload_url:
                raise Exception("未配置上传服务器地址")
            
            # 准备上传数据
            files = {}
            data = {
                'timestamp': datetime.now().isoformat(),
                'agent_phone': call_info.get('agent_phone', ''),
                'customer_name': call_info.get('customer_name', ''),
                'customer_id': call_info.get('customer_id', ''),
            }
            
            # 添加文件
            if mic_file and os.path.exists(mic_file):
                files['mic_file'] = open(mic_file, 'rb')
                data['mic_filename'] = os.path.basename(mic_file)
            
            if system_file and os.path.exists(system_file):
                files['system_file'] = open(system_file, 'rb')
                data['system_filename'] = os.path.basename(system_file)
            
            # 发送请求
            response = requests.post(
                upload_url,
                files=files,
                data=data,
                timeout=self.upload_config.get('timeout', 60)
            )
            
            # 关闭文件
            for f in files.values():
                f.close()
            
            if response.status_code == 200:
                result = response.json()
                if callback:
                    callback(True, f"上传成功: {result.get('message', '')}")
                
                # 上传成功后删除本地文件（如果配置了自动删除）
                if self.upload_config.get('auto_delete', False):
                    self._delete_local_files(mic_file, system_file)
                    
            else:
                if callback:
                    callback(False, f"上传失败: HTTP {response.status_code}")
                    
        except Exception as e:
            if callback:
                callback(False, f"上传错误: {str(e)}")
    
    def _delete_local_files(self, *files):
        """删除本地文件"""
        for file_path in files:
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"删除文件失败 {file_path}: {e}")
    
    def test_connection(self):
        """测试服务器连接"""
        try:
            test_url = self.upload_config.get('url', '').replace('/upload', '/health')
            response = requests.get(test_url, timeout=5)
            return response.status_code == 200
        except:
            return False