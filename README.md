# WebSocketTest
# 币安WebSocket连接稳定性测试工具
这个工具用于测试与币安交易所WebSocket服务器的连接稳定性。它可以帮助您监控WebSocket连接的状态、消息接收情况、错误率以及自动重连功能。

## 功能特点

- 支持直接连接和HTTP代理连接
- 支持同时订阅多个交易对数据
- 定期显示每个交易对的最新数据和延迟
- 自动重连机制（指数退避策略）
- 详细的连接状态日志
- 定期统计报告（每分钟）
- 支持自定义交易对和K线间隔
- 监控PING/PONG心跳消息

## 安装依赖

在使用此工具前，请确保已安装必要的依赖：

```bash
pip install websocket-client
```

## 使用方法

### 基本用法

```bash
python binance_ws_test.py
```

这将使用默认设置（BTCUSDT、ETHUSDT、BNBUSDT的1分钟K线，不使用代理）启动测试。

### 使用HTTP代理

```bash
python binance_ws_test.py --proxy
```

这将使用默认的代理设置（192.168.8.66:6152）。

### 自定义交易对

```bash
python binance_ws_test.py --symbols btcusdt,ethusdt,dogeusdt,xrpusdt
```

### 自定义参数

```bash
python binance_ws_test.py --proxy --proxy-host 127.0.0.1 --proxy-port 7890 --symbols ethusdt,btcusdt --interval 5m
```

### 所有可用选项

```
选项:
  --proxy                使用HTTP代理
  --proxy-host PROXY_HOST  HTTP代理主机 (默认: 192.168.8.66)
  --proxy-port PROXY_PORT  HTTP代理端口 (默认: 6152)
  --symbols SYMBOLS      交易对，用逗号分隔 (默认: btcusdt,ethusdt,bnbusdt)
  --interval INTERVAL    K线间隔 (默认: 1m)
  --log-level {DEBUG,INFO,WARNING,ERROR}
                        日志级别 (默认: INFO)
```

## 日志说明

程序运行时会输出以下类型的日志：

1. 连接状态日志 - 显示连接建立、关闭和重连信息
2. 交易对数据日志 - 每10秒显示一次每个交易对的最新数据和延迟
3. 消息接收日志 - 每接收50条消息会记录一次
4. 统计信息 - 每分钟显示一次运行统计
5. 错误日志 - 显示连接过程中的任何错误

## 测试网络稳定性

要全面测试网络稳定性，建议：

1. 在不同的网络环境下运行测试（家庭网络、公司网络、移动网络等）
2. 使用不同的代理设置进行对比测试
3. 长时间运行测试（至少几小时）以观察连接的稳定性
4. 关注重连次数和错误计数，这些是评估连接稳定性的重要指标
5. 监控数据延迟，这是评估连接质量的重要指标

## 注意事项

- 此工具仅用于测试网络连接稳定性，不提供交易功能
- 长时间运行可能会产生大量日志，请注意磁盘空间
- 币安WebSocket服务器可能有连接限制，请勿过于频繁地重连
