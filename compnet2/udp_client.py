import socket
import struct
import sys
import time
import pandas as pd
import select
import random
from collections import deque

# 协议参数配置
PACKET_HEADER = '!BHH'  # 类型(1B), 序号(2B), 数据长度(2B)
HEADER_LEN = struct.calcsize(PACKET_HEADER)

# 数据包类型标识
SYN_PACKET = 0  # 连接请求
DATA_PACKET = 1  # 数据传输
ACK_PACKET = 2  # 确认接收

# 协议参数
WINDOW_CAPACITY = 5  # 滑动窗口容量
PAYLOAD_SIZE = 80  # 数据负载大小
RETRY_TIMEOUT = 0.3  # 超时重传时间(s)
TOTAL_TO_SEND = 30  # 总发送数据包数量


class GBN_Sender:
    def __init__(self, server_ip, server_port):
        # 配置目标服务器
        self.target = (server_ip, server_port)
        # 创建非阻塞UDP套接字
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setblocking(0)

        # GBN协议状态变量
        self.window_start = 0  # 窗口起始序号
        self.next_to_send = 0  # 下一个待发送序号
        self.ack_received = set()  # 已确认的包序号

        # 性能统计
        self.rtt_history = []  # 存储RTT历史记录
        self.transmit_times = {}  # 包发送时间记录
        self.retry_count = 0  # 重传计数器

    def establish_connection(self):
        """建立连接的三次握手"""
        syn_header = struct.pack(PACKET_HEADER, SYN_PACKET, 0, 0)
        self.udp_socket.sendto(syn_header, self.target)

        print("等待服务器响应...")
        while True:
            # 使用select轮询套接字
            readable, _, _ = select.select([self.udp_socket], [], [], 0.1)
            if readable:
                ack_data, _ = self.udp_socket.recvfrom(HEADER_LEN)
                pkt_type, seq_num, _ = struct.unpack(PACKET_HEADER, ack_data)
                if pkt_type == ACK_PACKET:
                    print("连接已建立")
                    return

    def create_data_packet(self, seq_num):
        """构造数据包"""
        # 使用序列号作为随机种子确保重传时数据一致
        random.seed(seq_num)
        data_content = bytes([random.randint(0, 255) for _ in range(PAYLOAD_SIZE)])
        # 构造包头
        header = struct.pack(PACKET_HEADER, DATA_PACKET, seq_num, PAYLOAD_SIZE)
        return header + data_content

    def transmit_data(self):
        """主发送循环"""
        while len(self.ack_received) < TOTAL_TO_SEND:
            # 填充发送窗口
            while (self.next_to_send < self.window_start + WINDOW_CAPACITY and
                   self.next_to_send < TOTAL_TO_SEND):
                if self.next_to_send not in self.ack_received:
                    packet = self.create_data_packet(self.next_to_send)
                    self.udp_socket.sendto(packet, self.target)
                    self.transmit_times[self.next_to_send] = time.time()
                    byte_start = self.next_to_send * PAYLOAD_SIZE
                    byte_end = (self.next_to_send + 1) * PAYLOAD_SIZE - 1
                    print(f"发送包 {self.next_to_send + 1} (字节 {byte_start}-{byte_end})")
                self.next_to_send += 1

            # 处理ACK和超时
            self.process_responses()

    def process_responses(self):
        """处理响应和超时逻辑"""
        timeout_point = time.time() + RETRY_TIMEOUT
        while time.time() < timeout_point:
            time_left = timeout_point - time.time()
            ready, _, _ = select.select([self.udp_socket], [], [], max(0, time_left))

            if ready:
                response, _ = self.udp_socket.recvfrom(HEADER_LEN)
                pkt_type, ack_num, _ = struct.unpack(PACKET_HEADER, response)

                if pkt_type == ACK_PACKET and ack_num not in self.ack_received:
                    # 计算RTT
                    rtt_ms = (time.time() - self.transmit_times[ack_num]) * 1000
                    self.rtt_history.append(rtt_ms)

                    byte_start = ack_num * PAYLOAD_SIZE
                    byte_end = (ack_num + 1) * PAYLOAD_SIZE - 1
                    print(f"确认包 {ack_num + 1} (字节 {byte_start}-{byte_end}), RTT: {int(rtt_ms)}ms")

                    self.ack_received.add(ack_num)
                    # 移动窗口到下一个未确认位置
                    while self.window_start in self.ack_received:
                        self.window_start += 1

            # 超时检查
            if time.time() >= timeout_point:
                self.handle_retransmission()
                return

    def handle_retransmission(self):
        """处理超时重传"""
        print(f"超时! 重传窗口 {self.window_start} 到 {self.next_to_send - 1}")
        self.retry_count += 1

        # 重置发送指针并重传未确认包
        self.next_to_send = self.window_start
        for seq in range(self.window_start, min(self.window_start + WINDOW_CAPACITY, TOTAL_TO_SEND)):
            if seq not in self.ack_received:
                packet = self.create_data_packet(seq)
                self.udp_socket.sendto(packet, self.target)
                self.transmit_times[seq] = time.time()
                print(f"重发包 {seq + 1}")

    def generate_report(self):
        """生成性能报告"""
        acked_count = len(self.ack_received)
        total_sent = self.next_to_send + self.retry_count
        loss_rate = (self.retry_count / total_sent) * 100


        rtt_series = pd.Series(self.rtt_history)
        stats = {
            "丢包率": f"{loss_rate:.2f}%",
            "重传次数": self.retry_count,
            "最大RTT": f"{int(rtt_series.max())}ms",
            "最小RTT": f"{int(rtt_series.min())}ms",
            "平均RTT": f"{int(rtt_series.mean())}ms",
            "RTT波动": f"{int(rtt_series.std())}ms"
        }

        print("\n===== 传输报告 =====")
        for metric, value in stats.items():
            print(f"{metric}: {value}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"用法: {sys.argv[0]} <服务器IP> <服务器端口>")
        exit(1)

    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])

    sender = GBN_Sender(server_ip, server_port)
    sender.establish_connection()
    sender.transmit_data()
    sender.generate_report()