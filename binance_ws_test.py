#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import time
import logging
import argparse
import websocket
import threading
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class BinanceWSClient:
    def __init__(self, use_proxy=False, proxy_host="192.168.8.66", proxy_port=6152, symbols=None, interval="1m"):
        """
        初始化币安WebSocket客户端
        
        Args:
            use_proxy: 是否使用代理
            proxy_host: 代理主机地址
            proxy_port: 代理端口
            symbols: 交易对列表
            interval: K线间隔
        """
        self.symbols = symbols if symbols else ["btcusdt"]
        self.interval = interval
        self.use_proxy = use_proxy
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.ws = None
        self.connected = False
        self.last_msg_time = None
        self.connection_time = None
        self.message_count = 0
        self.ping_count = 0
        self.pong_count = 0
        self.error_count = 0
        self.reconnect_count = 0
        self.keep_running = True
        
        # 每个交易对的最新数据
        self.latest_data = {}
        
        # 统计数据
        self.stats_thread = None
        self.start_time = None
        
    def connect(self):
        """连接到币安WebSocket服务器"""
        # 构建WebSocket URL
        stream_names = [f"{symbol.lower()}@kline_{self.interval}" for symbol in self.symbols]
        
        # 如果是单个交易对，使用简单的URL
        if len(stream_names) == 1:
            ws_url = f"wss://stream.binance.com:9443/ws/{stream_names[0]}"
        else:
            # 多个交易对使用组合streams
            streams_param = "/".join(stream_names)
            ws_url = f"wss://stream.binance.com:9443/stream?streams={streams_param}"
        
        # WebSocket连接选项
        ws_options = {
            "on_open": self.on_open,
            "on_message": self.on_message,
            "on_error": self.on_error,
            "on_close": self.on_close,
            "on_ping": self.on_ping,
            "on_pong": self.on_pong,
        }
        
        # 如果使用代理，添加代理配置
        if self.use_proxy:
            http_proxy_url = f"http://{self.proxy_host}:{self.proxy_port}"
            ws_options["http_proxy_host"] = self.proxy_host
            ws_options["http_proxy_port"] = self.proxy_port
            logger.info(f"使用HTTP代理: {http_proxy_url}")
        
        # 创建WebSocket连接
        self.ws = websocket.WebSocketApp(ws_url, **ws_options)
        
        # 设置开始时间
        self.start_time = time.time()
        
        # 启动统计线程
        self.stats_thread = threading.Thread(target=self.print_stats)
        self.stats_thread.daemon = True
        self.stats_thread.start()
        
        # 启动数据打印线程
        self.data_print_thread = threading.Thread(target=self.print_latest_data)
        self.data_print_thread.daemon = True
        self.data_print_thread.start()
        
        # 启动WebSocket
        logger.info(f"正在连接到币安WebSocket: {ws_url}")
        logger.info(f"订阅的交易对: {', '.join(self.symbols)}")
        self.ws.run_forever(ping_interval=20, ping_timeout=10)
    
    def on_open(self, ws):
        """WebSocket连接打开时的回调"""
        self.connected = True
        self.connection_time = datetime.now()
        logger.info(f"WebSocket连接已建立! 连接时间: {self.connection_time}")
        
    def on_message(self, ws, message):
        """接收到WebSocket消息时的回调"""
        self.last_msg_time = datetime.now()
        self.message_count += 1
        
        try:
            data = json.loads(message)
            
            # 处理组合streams的消息格式
            if "stream" in data and "data" in data:
                stream = data["stream"]
                data = data["data"]
                # 从stream名称中提取交易对
                parts = stream.split('@')
                symbol = parts[0].upper()
            elif "s" in data:
                # 单个stream直接包含交易对信息
                symbol = data["s"]
            else:
                logger.warning(f"无法识别的消息格式: {message[:100]}...")
                return
                
            # 存储最新数据
            self.latest_data[symbol] = {
                "time": self.last_msg_time,
                "data": data
            }
            
            # 每50条消息记录一次日志
            if self.message_count % 50 == 0:
                logger.info(f"已接收 {self.message_count} 条消息")
                
        except Exception as e:
            logger.error(f"解析消息失败: {e}")
    
    def on_error(self, ws, error):
        """WebSocket错误时的回调"""
        self.error_count += 1
        logger.error(f"WebSocket错误: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """WebSocket连接关闭时的回调"""
        self.connected = False
        disconnect_time = datetime.now()
        
        # 计算连接持续时间
        if self.connection_time:
            duration = disconnect_time - self.connection_time
            logger.info(f"WebSocket连接已关闭! 持续时间: {duration}")
            logger.info(f"关闭状态码: {close_status_code}, 关闭消息: {close_msg}")
        else:
            logger.info("WebSocket连接已关闭，但未成功建立过连接")
        
        # 如果需要继续运行，则重新连接
        if self.keep_running:
            self.reconnect_count += 1
            reconnect_delay = min(30, 2 ** min(self.reconnect_count, 5))  # 指数退避，最大30秒
            logger.info(f"将在 {reconnect_delay} 秒后尝试重新连接 (第 {self.reconnect_count} 次)")
            time.sleep(reconnect_delay)
            
            # 创建新的线程进行重连
            threading.Thread(target=self.connect).start()
    
    def on_ping(self, ws, message):
        """接收到ping时的回调"""
        self.ping_count += 1
        logger.debug(f"收到PING: {message}")
    
    def on_pong(self, ws, message):
        """接收到pong时的回调"""
        self.pong_count += 1
        logger.debug(f"收到PONG: {message}")
    
    def print_latest_data(self):
        """定期打印最新数据"""
        while self.keep_running:
            time.sleep(10)  # 每10秒打印一次最新数据
            
            if not self.connected or not self.latest_data:
                continue
                
            logger.info("=== 最新交易对数据 ===")
            current_time = datetime.now()
            
            for symbol, data_info in self.latest_data.items():
                last_update_time = data_info["time"]
                data = data_info["data"]
                
                # 计算数据延迟
                delay = (current_time - last_update_time).total_seconds()
                
                # 提取K线数据（如果有的话）
                if "k" in data:
                    kline = data["k"]
                    interval = kline["i"]
                    close_price = kline["c"]
                    logger.info(f"{symbol} ({interval}): 价格={close_price}, 延迟={delay:.2f}秒")
                else:
                    logger.info(f"{symbol}: 最后更新={last_update_time}, 延迟={delay:.2f}秒")
            
            logger.info("======================")
    
    def print_stats(self):
        """定期打印统计信息"""
        while self.keep_running:
            time.sleep(60)  # 每分钟打印一次统计信息
            
            if not self.connected:
                continue
                
            current_time = time.time()
            elapsed_time = current_time - self.start_time
            hours, remainder = divmod(elapsed_time, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            logger.info("=== WebSocket连接统计 ===")
            logger.info(f"运行时间: {int(hours)}小时 {int(minutes)}分钟 {int(seconds)}秒")
            logger.info(f"连接状态: {'已连接' if self.connected else '未连接'}")
            logger.info(f"接收消息数: {self.message_count}")
            logger.info(f"PING计数: {self.ping_count}")
            logger.info(f"PONG计数: {self.pong_count}")
            logger.info(f"错误计数: {self.error_count}")
            logger.info(f"重连次数: {self.reconnect_count}")
            logger.info(f"订阅交易对数: {len(self.symbols)}")
            
            # 计算每分钟消息率
            if elapsed_time > 0:
                msg_rate = self.message_count / (elapsed_time / 60)
                logger.info(f"消息率: {msg_rate:.2f} 消息/分钟")
            
            logger.info("========================")
    
    def stop(self):
        """停止WebSocket客户端"""
        logger.info("正在停止WebSocket客户端...")
        self.keep_running = False
        if self.ws:
            self.ws.close()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='币安WebSocket连接稳定性测试工具')
    parser.add_argument('--proxy', action='store_true', help='使用HTTP代理')
    parser.add_argument('--proxy-host', default='192.168.8.66', help='HTTP代理主机 (默认: 192.168.8.66)')
    parser.add_argument('--proxy-port', type=int, default=6152, help='HTTP代理端口 (默认: 6152)')
    parser.add_argument('--symbols', default='btcusdt,ethusdt,bnbusdt', help='交易对，用逗号分隔 (默认: btcusdt,ethusdt,bnbusdt)')
    parser.add_argument('--interval', default='1m', help='K线间隔 (默认: 1m)')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                        help='日志级别 (默认: INFO)')
    
    args = parser.parse_args()
    
    # 设置日志级别
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # 解析交易对列表
    symbols = [s.strip() for s in args.symbols.split(',')]
    
    try:
        # 创建并启动WebSocket客户端
        client = BinanceWSClient(
            use_proxy=args.proxy,
            proxy_host=args.proxy_host,
            proxy_port=args.proxy_port,
            symbols=symbols,
            interval=args.interval
        )
        
        logger.info(f"启动币安WebSocket测试 - 交易对: {', '.join(symbols)}, 间隔: {args.interval}")
        logger.info(f"代理设置: {'启用' if args.proxy else '禁用'}")
        
        # 连接到WebSocket
        client.connect()
        
    except KeyboardInterrupt:
        logger.info("接收到键盘中断，正在退出...")
    except Exception as e:
        logger.error(f"发生错误: {e}")
    finally:
        if 'client' in locals():
            client.stop()

if __name__ == "__main__":
    main()
