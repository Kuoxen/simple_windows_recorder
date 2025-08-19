#!/usr/bin/env python3
"""
自动录制功能测试脚本
"""

import sys
import os
import time
import logging

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config.settings import Settings
from audio.auto_recorder import AutoAudioRecorder
from audio.enhanced_device_manager import EnhancedDeviceManager

def test_auto_recording():
    """测试自动录制功能"""
    
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    try:
        # 初始化组件
        config_path = "config.yaml"
        settings = Settings(config_path)
        device_manager = EnhancedDeviceManager()
        auto_recorder = AutoAudioRecorder(settings)
        
        # 设置状态回调
        def status_callback(message):
            logger.info(f"录制器状态: {message}")
        
        auto_recorder.set_status_callback(status_callback)
        
        # 获取推荐设备
        recommendations = device_manager.get_recommended_devices()
        mic_device = recommendations['microphone']
        system_device = recommendations['system_audio']
        
        if mic_device is None:
            logger.error("未找到可用的麦克风设备")
            return
        
        if system_device is None:
            logger.error("未找到可用的系统音频设备")
            return
        
        logger.info(f"使用设备 - 麦克风: {mic_device}, 系统音频: {system_device}")
        
        # 设置设备和通话信息
        auto_recorder.set_devices(mic_device, system_device)
        auto_recorder.set_call_info("13800138000", "测试客户", "TEST001")
        
        # 开始监听
        logger.info("开始自动录制监听...")
        if not auto_recorder.start_monitoring():
            logger.error("无法开始监听")
            return
        
        # 监听30秒
        logger.info("监听30秒，请说话测试...")
        for i in range(30):
            time.sleep(1)
            status = auto_recorder.get_status()
            
            if i % 5 == 0:  # 每5秒输出一次状态
                logger.info(f"状态: {status['state']}, 麦克风活跃: {status.get('mic_active', False)}, "
                          f"系统音频活跃: {status.get('system_active', False)}")
        
        # 停止监听
        logger.info("停止监听...")
        auto_recorder.stop_monitoring()
        
        logger.info("测试完成")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_auto_recording()