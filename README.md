# 呼叫中心录音系统

一个用于呼叫中心的双路音频录制系统，可以同时录制坐席和客户的声音。

## 功能特性

- 🎙️ 双路音频录制（麦克风 + 系统音频）
- 🖥️ 图形化界面操作
- 📝 通话信息记录（坐席手机号、客户姓名、客户ID）
- 📁 智能文件命名
- 🔧 设备自动检测和选择

## 系统要求

- Windows 10/11
- Python 3.8+
- VB-Cable 虚拟音频设备

## 快速安装

### 方法1：一键安装（推荐）

1. 下载项目文件
2. 双击运行 `installer.py`
3. 按提示完成安装

### 方法2：手动安装

1. 安装 VB-Cable：https://vb-audio.com/Cable/
2. 安装 Python 依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 启动程序：
   ```bash
   python run_ui.py
   ```

## 使用说明

### 1. VB-Cable 配置

**安装 VB-Cable 后需要配置音频路由：**

1. **设置系统输出为 CABLE Input：**
   - Windows 设置 → 系统 → 声音
   - 输出设备选择：`CABLE Input (VB-Audio Virtual Cable)`

2. **设置音频监听（让你能听到声音）：**
   - 右键任务栏音量图标 → 打开声音设置
   - 点击"声音控制面板"
   - 切换到"录制"选项卡
   - 找到"CABLE Output"，右键 → 属性
   - 切换到"侦听"选项卡
   - 勾选"侦听此设备"
   - 选择你的耳机/扬声器

### 2. 程序使用

1. **启动程序**
2. **选择设备：**
   - 麦克风设备：选择物理麦克风
   - 系统音频：选择 CABLE Output
3. **填写信息：**
   - 坐席手机号（建议填写）
   - 客户姓名（可选）
   - 客户ID（可选）
4. **开始录音**
5. **停止录音** - 自动保存文件

### 3. 文件命名格式

```
mic_20241220_143022_Agent_13800138000_Customer_张三_ID_12345.wav
system_20241220_143022_Agent_13800138000_Customer_张三_ID_12345.wav
```

## 打包发布

### 打包成 .exe 文件

```bash
# 安装打包工具
pip install -r build_requirements.txt

# 执行打包
python build.py
```

生成的 `.exe` 文件位于 `dist/` 目录。

## 故障排除

### 1. 录不到系统音频
- 检查系统默认输出是否设为 CABLE Input
- 检查程序中是否选择了 CABLE Output

### 2. 听不到声音
- 检查 CABLE Output 的"侦听此设备"是否开启
- 检查侦听输出设备是否正确

### 3. 找不到设备
- 确认 VB-Cable 已正确安装
- 重启电脑后再试

## 技术架构

- **UI框架：** tkinter
- **音频处理：** sounddevice + numpy
- **虚拟音频：** VB-Cable
- **配置管理：** PyYAML

## 开发环境

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 运行程序
python run_ui.py
```