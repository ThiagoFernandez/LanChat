import json
import re
import socket
import sys
from datetime import datetime


def save_file(dic):
    now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    with open(f"arp_results_{now}.json", "w", encoding="UTF-8") as f:
        json.dump(dic, f, indent=4)


def validate_ipv4(ip):  # -1 si es invalido
    # solo una barra
    if ip.count("/") != 1:
        return -1
    # tiene que tener si o si 3 puntos
    if ip.count(".") != 3:
        return -1
    # no puede haber letras
    if re.search("[a-zA-z]", ip):
        return -1

    mascara_idx = ip.index("/")  # busco donde comienza la barra
    try:
        mascara = int(ip[mascara_idx + 1 :])  # solo el numero de la mascara
    except ValueError:
        return -1
    ipv4 = ip[:mascara_idx]  # solo la parte de la ip

    octetos = []  # lista de octetos
    octeto = ""  # octeto vacio el cual voy sumando caracter x caracter
    for i in range(len(ipv4)):
        if ipv4[i] == ".":
            if (
                int(octeto) > 255 or int(octeto) < 0
            ):  # el octeto no puede sr menor a 0 o mayor a 255
                return -1
            octetos.append(int(octeto))  # lo guardo
            octeto = ""  # lo reinicio
        else:
            octeto += ipv4[i]
    octetos.append(int(octeto))

    if mascara > 32 or mascara < 0:  # la mascara no puedee ser menor q 0 ni mayor qq 32
        return -1

    match octetos[0]:
        case 10:
            pass  # este caso ya esta validado con lo anterior
        case 172:
            if (
                octetos[1] < 16 or octetos[1] > 31
            ):  # segundo octeto tiene q ser ntre 16-31
                return -1
            if mascara < 12:  # la mascara no puede ser menor a 12
                return -1
        case 192:
            if (
                octetos[1] != 168
            ):  # si o si el 2do octeto es 168 --- una de las redes priv + comunes
                return -1
            if (
                mascara < 16
            ):  # la mascara si o si 16, si se dan cuenta la mascara va creciendo de a 4 bits
                return -1
        case _:  # cualquier otro caso es invalido porque no es privada o no cumple el formato ipv4
            return -1

            #       8               16                  24              32

    # donde hay 1 conserva el bit de la ip, si hay 0 pone 0 sin importar el bit de la ip

    return mascara, ipv4


def validat_args():
    if len(sys.argv) != 2:
        print("Uso: python main.py <red base u host/mascara>")
        return -1
    usr_input = sys.argv[1]
    resultado = validate_ipv4(usr_input)
    if resultado == -1:
        return -1
    mask, ipv4 = resultado
    print(f"ip: {ipv4} --- mascara: {mask}")
    return usr_input


def validate_input():
    usr_input = input("Write your IP and Mask (192.168.x.x/24): ")
    if usr_input == "":
        return -1
    resultado = validate_ipv4(usr_input)
    if resultado == -1:
        return -1
    mask, ipv4 = resultado
    print(f"ip: {ipv4} --- mascara: {mask}")
    return usr_input


def show_options(options):
    for idx, value in enumerate(options):
        print(f"{idx + 1}. {value}")
    print(f"{len(options) + 1}. Exit")


def validate_number(options):
    while True:
        try:
            option = int(input("Choose an option: "))
        except ValueError:
            print("The value must be a number | Try again")
        else:
            if option < 1 or option > len(options) + 1:
                print(f"The option must be between 1-{len(options) + 1} | Try again")
            elif option == len(options) + 1:
                return -1
            else:
                return option


def is_integer(s):
    try:
        int(s)
        return True
    except ValueError:
        return False
    except TypeError:
        return False


def validate_numberv2():
    while True:
        try:
            option = int(input("Write a number(-1 to exit): "))
        except ValueError:
            print("The value must be a number | Try again")
        else:
            if option == -1:
                return -1
            else:
                if option < 0:
                    print("The value cannot be negative | Try again")
                else:
                    return option


def validate_string(options, text, type):
    while True:
        string = input(f"{text}('*' to go back to the menu): ")
        if string.strip() == "":
            print("Only blank space as text is invalid | Try again")
        elif string.strip() == "*":
            return -1
        elif string in options:
            print("There is one with the same name | Try again")
        elif not string.endswith(".mp3") and type == 0:
            print(f"The name needs to end with a '.mp3' | Try again")
        else:
            return string


def greeting_text(text):
    print(f"{' ' + text + ' ':-^60}")


def validate_string_v2(text):
    while True:
        string = input(f"{text}('*' to go back to the menu): ")
        if string.strip() == "":
            print("Only blank space as text is invalid | Try again")
        elif string.strip() == "*":
            return -1
        else:
            return string



def obtener_mi_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()

    return ip
