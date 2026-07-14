import socket
from concurrent.futures import ThreadPoolExecutor

from nmb.NetBIOS import NetBIOS

import colorama
from scapy.all import ARP, Ether, srp

import auxiliar

colorama.init()


def get_paquete(red):

    arp = ARP(pdst=red)  # yo le paso la subred y scapy la expande a todo su dominio
    ether = Ether(
        dst="ff:ff:ff:ff:ff:ff"
    )  # Es la MAC de broadcast, con esto todos los dipositivos reciben el broadcast
    return ether / arp


def enviar_paquete(paquete):
    return srp(
        paquete, timeout=2, verbose=0
    )  # el 2 es a eleccion y el 0 es porque no necesito lo q me devuelve eso


def get_hostname(ip):
    try:
        hostname = socket.gethostbyaddr(ip)[0]
    except socket.herror:
        rt = get_netbios_name(ip)
        if rt is not None:
            hostname = rt
        else:
            hostname = "N/A"
    return hostname

def get_netbios_name(ip, timeout=2):
    nb = NetBIOS()
    try:
        names = nb.queryIPForName(ip, timeout=timeout)   #por lo q vi, esto va al udp puerto num 137
        return names[0] if names else None
    finally:
        nb.close()

def get_hosts(dispositivos):
    hosts = []
    for d in dispositivos:
        host = (d["ip"], d["mac"])
        hosts.append(host)
    return hosts


def get_resultados(si_rta):
    dispositivos = []
    for enviado, recibido in si_rta:
        dispositivos.append(
            {
                "ip": recibido[ARP].psrc,
                "mac": recibido[Ether].src,
                "hostname": None,
            }
        )

    # hostnames en paralelo
    ips = [d["ip"] for d in dispositivos]
    with ThreadPoolExecutor(max_workers=10) as executor:
        hostnames = list(executor.map(get_hostname, ips))
    for d, hostname in zip(dispositivos, hostnames):
        d["hostname"] = hostname

    dispositivos.sort(key=lambda d: tuple(int(oct) for oct in d["ip"].split(".")))
    return dispositivos


def ver_resultados(resultados):
    if not resultados:
        print("No encontro nada")
        return

    # ancho max x col
    anchos = {
        "ip": max(len(d["ip"]) for d in resultados),
        "mac": max(len(d["mac"]) for d in resultados),
        "hostname": max(len(d["hostname"]) for d in resultados),
    }

    # que no sean menores que el header porque sino es cualquier cosa
    anchos["ip"] = max(anchos["ip"], len("IP"))
    anchos["mac"] = max(anchos["mac"], len("MAC"))
    anchos["hostname"] = max(anchos["hostname"], len("Hostname"))

    # header
    print(
        f"{'#':<4} {'IP':<{anchos['ip']}} {'MAC':<{anchos['mac']}} {'Hostname':<{anchos['hostname']}}"
    )
    print("-" * (4 + anchos["ip"] + anchos["mac"] + anchos["hostname"] + 4))

    # filas
    mi_ip = auxiliar.obtener_mi_ip()
    for idx, d in enumerate(resultados, 1):
        if mi_ip == d["ip"]:
            print(
                f"{colorama.Fore.GREEN}{idx:<4} {d['ip']:<{anchos['ip']}} {d['mac']:<{anchos['mac']}} {d['hostname']:<{anchos['hostname']}}{colorama.Style.RESET_ALL}"
            )
        else:
            print(
                f"{idx:<4} {d['ip']:<{anchos['ip']}} {d['mac']:<{anchos['mac']}} {d['hostname']:<{anchos['hostname']}}"
            )


def start_scanner(red):
    paquete = get_paquete(red)
    si_rta, _ = enviar_paquete(paquete)
    return get_resultados(si_rta)
