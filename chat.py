import socket

PUERTO = 40000  # cada uno pone el q quiere pero mejor si usan uno dentro de este rango: 1024 - 49151
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # IPv4 y protocolo UDP

sock.bind(("0.0.0.0", PUERTO))
# data, addr = sock.recvfrom(1024)  # addr es la ip y el puerto


def send_msg(msg, receptor):
    sock.sendto(msg.encode("utf-8"), (receptor, PUERTO))
