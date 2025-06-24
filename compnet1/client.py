
import socket, sys, random
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

def split_file(filepath, Lmin, Lmax):
    with open(filepath, 'r') as f:
        data = f.read()
    blocks = []
    i = 0
    while i < len(data):
        L = random.randint(Lmin, Lmax)
        blocks.append(data[i:i+L])
        i += L
    return blocks

def main():
    if len(sys.argv) != 5:
        print("Usage: python client.py <server_ip> <server_port> <Lmin> <Lmax>")
        return

    ip, port = sys.argv[1], int(sys.argv[2])
    Lmin, Lmax = int(sys.argv[3]), int(sys.argv[4])
    blocks = split_file('test.txt', Lmin, Lmax)
    N = len(blocks)

    reversed_full = ''

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((ip, port))

    # Initialization
    client.send(pack_message(TYPE_INIT, N.to_bytes(4, 'big')))
    msg_type, data = unpack_message(client)
    if msg_type != TYPE_AGREE:
        print("Server did not agree.")
        return

    for i, block in enumerate(blocks):
        client.send(pack_message(TYPE_REQUEST, block.encode()))
        msg_type, data = unpack_message(client)
        if msg_type != TYPE_RESPONSE:
            break
        reversed_text = data.decode()
        print(f"{i+1}: {reversed_text}")
        reversed_full = reversed_text + reversed_full

    with open('reversed_output.txt', 'w') as f:
        f.write(reversed_full)

    client.close()

if __name__ == '__main__':
    main()
