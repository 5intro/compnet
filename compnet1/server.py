
import socket
import threading
import struct

TYPE_INIT = 1
TYPE_AGREE = 2
TYPE_REQUEST = 3
TYPE_RESPONSE = 4

def pack_message(msg_type: int, data: bytes) -> bytes:
    return struct.pack('!BI', msg_type, len(data)) + data

def unpack_message(sock):
    header = sock.recv(5)
    if not header:
        return None, None
    msg_type, length = struct.unpack('!BI', header)
    data = b''
    while len(data) < length:
        packet = sock.recv(length - len(data))
        if not packet:
            break
        data += packet
    return msg_type, data

def handle_client(conn, addr):
    print(f"[+] New connection from {addr}")
    try:
        msg_type, data = unpack_message(conn)
        if msg_type != TYPE_INIT:
            return
        N = int.from_bytes(data, 'big')
        conn.send(pack_message(TYPE_AGREE, b'OK'))

        for i in range(N):
            msg_type, data = unpack_message(conn)
            if msg_type != TYPE_REQUEST:
                break
            reversed_data = data.decode()[::-1].encode()
            conn.send(pack_message(TYPE_RESPONSE, reversed_data))
    except Exception as e:
        print("[-] Error:", e)
    finally:
        conn.close()

def main():
    host = '0.0.0.0'
    port = 12345
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    print(f"[*] Server listening on {port}...")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr)).start()

if __name__ == '__main__':
    main()
