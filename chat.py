import queue
import socket
import threading

PUERTO = 40000  # rango registrado: 1024 - 49151

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # IPv4 + UDP
sock.bind(("0.0.0.0", PUERTO))  # 0.0.0.0 = todas las interfaces

cola = queue.Queue()


def send_msg(msg, receptor):
    sock.sendto(msg.encode("utf-8"), (receptor, PUERTO))


def loop_red():
    while True:
        try:
            data, addr = sock.recvfrom(
                1024
            )  # estos son 1024 bytes lo cual me puede dejar corto en un futuro
        except OSError:
            break
        try:
            texto = data.decode("utf-8")
            cola.put((texto, addr))  # tupla mejor que lista para un registro fijo
        except UnicodeDecodeError:
            pass


def cerrar():
    sock.close()


def iniciar_receptor():
    hilo = threading.Thread(target=loop_red, daemon=True)
    hilo.start()
