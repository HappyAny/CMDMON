# CmdMon - 命令行监控分析工具

![Python版本](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 功能特性

- ⏱️ 精确记录命令执行时间
- 📝 捕获标准输出和错误输出
- 🤖 集成大模型智能分析
- 📅 按日期自动分割日志
- 🔔 实时通知推送

## 安装指南

1. 克隆仓库：
```bash
git clone https://github.com/happyany/cmdmon.git
cd cmdmon
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置设置：
```json
{
  "openai": {
    "api_key": "your_openai_api_key",
    "model": "gpt-4o",
    "base_url": "https://api.openai.com/v1"
  },
  "pushdeer": {
    "pushkey": "your_pushdeer_pushkey"
  },
  "features": {
    "enable_ai": true,
    "enable_push": true
  },
  "logging": {
    "level": "INFO"
  }
}
```

## 使用示例

基本监控：
```bash
python cmdmon.py your_command_here
```

带通知推送：
```bash
python cmdmon.py --pushkey your_pushkey your_command_here
```

指定配置文件：
```bash
python cmdmon.py --config custom_config.json your_command_here
```

## 依赖说明

- openai: GPT API调用
- requests: HTTP请求处理
- python-dotenv: 环境变量管理
- argparse: 命令行参数解析

## 许可证

MIT License © 2025
