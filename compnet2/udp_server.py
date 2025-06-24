import socket
import struct
import threading
import random

# ======================
# 服务器配置参数
# ======================
SERVER_HOST = ''  # 空字符串表示监听所有接口
SERVER_PORT = 8888  # 服务端口
PACKET_LOSS_PROB = 0.2  # 数据包丢失概率


# ======================
# 通信协议定义
# ======================
class PacketTypes:
    CONNECTION_SYN = 0  # 连接请求
    DATA_TRANSFER = 1  # 数据传输
    ACKNOWLEDGE = 2  # 确认响应


# 数据包头结构：类型(1B) + 序列号(2B) + 数据长度(2B)
PACKET_HEADER_FORMAT = '!BHH'
HEADER_LENGTH = struct.calcsize(PACKET_HEADER_FORMAT)


# ======================
# UDP 服务器实现
# ======================
class UDPReceiver:
    def __init__(self, host, port, loss_probability):
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listener.bind((host, port))
        self.packet_loss_rate = loss_probability

        print(f"UDP 服务器已启动，监听地址: {host}:{port}")
        print(f"当前丢包率设置为: {loss_probability * 100}%")

    def begin_service(self):
        """启动服务器主循环"""
        while True:
            raw_data, client_address = self.listener.recvfrom(2048)
            # 使用线程处理接收到的数据包
            threading.Thread(
                target=self.process_incoming_packet,
                args=(raw_data, client_address)
            ).start()

    def process_incoming_packet(self, packet_data, client_addr):
        """处理接收到的数据包"""
        # 检查数据包长度是否有效
        if len(packet_data) < HEADER_LENGTH:
            print(f"来自 {client_addr} 的无效数据包: 长度不足")
            return

        # 解包头部信息
        header_data = packet_data[:HEADER_LENGTH]
        try:
            packet_type, sequence_num, data_size = struct.unpack(
                PACKET_HEADER_FORMAT, header_data)
        except struct.error:
            print(f"包头解析失败: {header_data}")
            return

        # 提取有效载荷
        payload = packet_data[HEADER_LENGTH:HEADER_LENGTH + data_size]

        # 处理连接请求
        if packet_type == PacketTypes.CONNECTION_SYN:
            print(f"收到来自 {client_addr} 的连接请求")
            self._send_acknowledgement(client_addr, 0)

        # 处理数据传输
        elif packet_type == PacketTypes.DATA_TRANSFER:
            # 模拟随机丢包
            if random.random() < self.packet_loss_rate:
                print(f"模拟丢包: 序列号 {sequence_num} 的数据包被丢弃")
                return

            print(f"收到数据包 #{sequence_num}, 大小: {data_size} 字节")
            self._send_acknowledgement(client_addr, sequence_num)

    def _send_acknowledgement(self, destination, sequence_num):
        """发送确认响应到客户端"""
        ack_header = struct.pack(
            PACKET_HEADER_FORMAT,
            PacketTypes.ACKNOWLEDGE,
            sequence_num,
            0
        )
        self.listener.sendto(ack_header, destination)
        print(f"已发送 ACK 响应: 序列号 {sequence_num}")


# ======================
# 主程序入口
# ======================
if __name__ == "__main__":
    server = UDPReceiver(
        host=SERVER_HOST,
        port=SERVER_PORT,
        loss_probability=PACKET_LOSS_PROB
    )
    server.begin_service()