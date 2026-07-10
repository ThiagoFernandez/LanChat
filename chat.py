import json
import queue
import socket
import threading
from json.decoder import JSONDecodeError

PUERTO = 40000  # rango registrado: 1024 - 49151

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # IPv4 + UDP
sock.bind(("0.0.0.0", PUERTO))  # 0.0.0.0 = todas las interfaces

cola = queue.Queue()


def create_msg(
    emisor, txt=None, tipo="msg"
):  # aunque podria ser sin default todos ya que el user en la gui podria decidir eso
    # todavia no defini d edonde agarrar el contador y guardarlo
    #
    dic = {
        "tipo": tipo,
        "id": 1,  # dsp lo cambio
        "emisor": emisor,
        "content": txt,
    }

    return dic


def encode_dic(dic):
    j = json.dumps(dic)
    msg = j.encode("utf-8")
    return msg


def decode_dic(msg):  # corregido el bug 1
    try:
        j = msg.decode("utf-8")
        dic = json.loads(j)
    except JSONDecodeError:
        return -1
    except UnicodeDecodeError:
        return -1
    else:
        return dic


def validate_dic(dic):
    if not isinstance(dic, dict):
        return -1

    keys = list(dic.keys())
    if len(keys) != 4:  # con esto corrijo el bug 2
        return -1

    # pense q importaban el orden de las claves
    if "tipo" in keys and "id" in keys and "emisor" in keys and "content" in keys:
        if dic["tipo"] in ["msg", "delete", "edit"]:
            if isinstance(dic["id"], int) and not isinstance(dic["id"], bool):
                return 1

    return -1


def send_msg(msg, receptor):
    sock.sendto(msg, (receptor, PUERTO))  # el msg seria lo que devuelve encode_dic(dic)


def loop_red():
    while True:
        try:
            data, addr = sock.recvfrom(
                1024
            )  # estos son 1024 bytes lo cual me puede dejar corto en un futuro
        except OSError:
            break
        dic = decode_dic(data)

        result = validate_dic(dic)
        if result == 1:
            cola.put((dic, addr))  # tupla mejor que lista para un registro fijo


def cerrar():
    sock.close()


def iniciar_receptor():
    hilo = threading.Thread(target=loop_red, daemon=True)
    hilo.start()
