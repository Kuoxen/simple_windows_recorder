import requests
import os
import threading
from datetime import datetime
import oss2

class FileUploader:
    def __init__(self, settings):
        self.settings = settings
        self.upload_config = settings.upload
        self.oss_config = {
            'endpoint': 'https://oss-cn-beijing.aliyuncs.com',
            'bucket': 'rocksilicon-aliyun-oss-01',
            'region': 'cn-beijing'
        }
        
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
            # 1. 获取STS临时凭证
            sts_token = self._get_sts_token(call_info)
            if not sts_token:
                raise Exception("获取上传凭证失败")
            
            # 2. 创建OSS客户端
            auth = oss2.StsAuth(
                sts_token['access_key_id'],
                sts_token['access_key_secret'],
                sts_token['security_token']
            )
            bucket = oss2.Bucket(auth, self.oss_config['endpoint'], self.oss_config['bucket'])
            
            # 3. 上传文件
            uploaded_files = []
            
            if mic_file and os.path.exists(mic_file):
                key = self._generate_oss_key(mic_file, call_info, 'mic')
                bucket.put_object_from_file(key, mic_file)
                uploaded_files.append({'type': 'mic', 'key': key, 'file': mic_file})
            
            if system_file and os.path.exists(system_file):
                key = self._generate_oss_key(system_file, call_info, 'system')
                bucket.put_object_from_file(key, system_file)
                uploaded_files.append({'type': 'system', 'key': key, 'file': system_file})
            
            # 4. 通知服务器上传完成
            self._notify_upload_complete(uploaded_files, call_info)
            
            if callback:
                callback(True, f"成功上传 {len(uploaded_files)} 个文件到OSS")
            
            # 上传成功后删除本地文件
            if self.upload_config.get('auto_delete', False):
                self._delete_local_files(mic_file, system_file)
                
        except Exception as e:
            if callback:
                callback(False, f"OSS上传错误: {str(e)}")
    
    def _delete_local_files(self, *files):
        """删除本地文件"""
        for file_path in files:
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"删除文件失败 {file_path}: {e}")
    
    def _get_sts_token(self, call_info):
        """从服务器获取STS临时凭证"""
        try:
            token_url = self.upload_config.get('token_url')
            if not token_url:
                raise Exception("未配置凭证获取地址")
            
            response = requests.post(token_url, json={
                'agent_phone': call_info.get('agent_phone', ''),
                'customer_name': call_info.get('customer_name', ''),
                'customer_id': call_info.get('customer_id', '')
            }, timeout=10)
            
            if response.status_code == 200:
                return response.json().get('credentials')
            else:
                raise Exception(f"HTTP {response.status_code}")
                
        except Exception as e:
            print(f"获取STS凭证失败: {e}")
            return None
    
    def _generate_oss_key(self, file_path, call_info, file_type):
        """生成OSS对象键名：公司ID/日期/坐席手机号/文件"""
        company_id = self.upload_config.get('company_id', '1')
        date_str = datetime.now().strftime('%Y/%m/%d')
        agent_phone = call_info.get('agent_phone', 'unknown')
        filename = os.path.basename(file_path)
        
        return f"recordings/{company_id}/{date_str}/{agent_phone}/{file_type}_{filename}"
    
    def _notify_upload_complete(self, uploaded_files, call_info):
        """通知服务器上传完成"""
        try:
            notify_url = self.upload_config.get('notify_url')
            if not notify_url:
                return
            
            data = {
                'timestamp': datetime.now().isoformat(),
                'company_id': self.upload_config.get('company_id', '1'),
                'agent_phone': call_info.get('agent_phone', ''),
                'customer_name': call_info.get('customer_name', ''),
                'customer_id': call_info.get('customer_id', ''),
                'files': [{'type': f['type'], 'oss_key': f['key']} for f in uploaded_files]
            }
            
            requests.post(notify_url, json=data, timeout=10)
            
        except Exception as e:
            print(f"通知服务器失败: {e}")
    
    def test_connection(self):
        """测试服务器连接"""
        try:
            token_url = self.upload_config.get('token_url', '')
            if not token_url:
                return False
            response = requests.get(token_url.replace('/get-upload-token', '/health'), timeout=5)
            return response.status_code == 200
        except:
            return False