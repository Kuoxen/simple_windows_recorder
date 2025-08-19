#!/usr/bin/env python3
"""
调试自动录制功能
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

def debug_auto_recording():
    """调试自动录制功能"""
    
    # 配置详细日志
    logging.basicConfig(
        level=logging.DEBUG, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("=== 开始调试自动录制功能 ===")
        
        # 初始化组件
        config_path = "config.yaml"
        settings = Settings(config_path)
        device_manager = EnhancedDeviceManager()
        auto_recorder = AutoAudioRecorder(settings)
        
        # 显示配置
        logger.info(f"自动录制配置: {settings.auto_recording}")
        
        # 设置状态回调
        def status_callback(message):
            print(f"[状态] {message}")
        
        auto_recorder.set_status_callback(status_callback)
        
        # 获取设备列表
        logger.info("获取设备列表...")
        physical_mics = device_manager.get_physical_microphones()
        loopback_devices = device_manager.get_loopback_devices()
        
        logger.info(f"找到 {len(physical_mics)} 个麦克风设备:")
        for device_id, device in physical_mics:
            logger.info(f"  [{device_id}] {device['name']}")
        
        logger.info(f"找到 {len(loopback_devices)} 个回环设备:")
        for device_id, device in loopback_devices:
            logger.info(f"  [{device_id}] {device['name']}")
        
        # 获取推荐设备
        recommendations = device_manager.get_recommended_devices()
        mic_device = recommendations['microphone']
        system_device = recommendations['system_audio']
        
        if mic_device is None:
            logger.error("未找到可用的麦克风设备")
            return
        
        if system_device is None:
            logger.warning("未找到可用的系统音频设备，将使用麦克风设备")
            system_device = mic_device
        
        logger.info(f"使用设备 - 麦克风: {mic_device}, 系统音频: {system_device}")
        
        # 设置设备和通话信息
        auto_recorder.set_devices(mic_device, system_device)
        auto_recorder.set_call_info("13800138000", "调试客户", "DEBUG001")
        
        # 开始监听
        logger.info("开始自动录制监听...")
        if not auto_recorder.start_monitoring():
            logger.error("无法开始监听")
            return
        
        # 监听60秒
        logger.info("监听60秒，请说话或播放音频测试...")
        for i in range(60):
            time.sleep(1)
            
            if i % 5 == 0:  # 每5秒输出一次状态
                status = auto_recorder.get_status()
                logger.info(f"[{i}s] 状态: {status['state']}, "
                          f"麦克风活跃: {status.get('mic_active', False)}, "
                          f"系统音频活跃: {status.get('system_active', False)}, "
                          f"静默时长: {status.get('silence_duration', 0):.1f}s")
        
        # 停止监听
        logger.info("停止监听...")
        auto_recorder.stop_monitoring()
        
        logger.info("=== 调试完成 ===")
        
    except Exception as e:
        logger.error(f"调试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_auto_recording()