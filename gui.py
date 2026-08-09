import queue
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, simpledialog, ttk

import auxiliar
import chat
import crypto
import scanner
import storage

MAX_INTENTOS = 5
TIMEOUT_MS = 1500
my_ip = auxiliar.obtener_mi_ip()
conversaciones = {}   # {mac: conv}
ip_a_mac = {}         # {ip: mac}
conv_activa = None    # la que se muestra
root = None      # se setea en iniciar_app: global root; root = tk.Tk()
agenda = None    # se carga una vez: global agenda; agenda = storage.load()
esperando_mac = {} # {ip:[raw, ...]}

def resolver_mac(ip):
    return ip_a_mac.get(ip)

def obtener_conv(mac, ip):
    if mac in conversaciones:
        if conversaciones[mac]["ip"] != ip:
            conversaciones[mac]["ip"] = ip # x si cambio la ip btw
        return conversaciones[mac]
    else:
        conv = {
            "mac": mac,
            "ip": ip,
            "fernet": None,  # el Fernet de este peer; None hasta que el hs este finished
            "chat_storage": storage.load_chat(mac),
            "pendientes": [], # FIFO de cifrados que llegaron sin clave
            "intentos": 0,
            "ultimo": None,
            "no_leidos": 0
        }
        conversaciones[mac] = conv

        return conv

def procesar_paquete(conv, raw, ip_origen):
    if conv["fernet"] is None and crypto.leer_tipo(raw) == "cifrado":
        conv["pendientes"].append(raw)      # todavi no puedo descifrarlo → lo guardo
        return

    tipo, payload = crypto.desenvolver(raw, conv["fernet"])
    match tipo:
        case "hs_init":
            chat.send_msg(crypto.envolver_handshake(crypto.my_public, "hs_reply"),ip_origen)
            helper_completar_handshake(conv, payload)
        case "hs_reply":
            helper_completar_handshake(conv, payload)
        case "cifrado":
            procesar_cifrado(conv, payload)
        case _:
            pass

def iniciar_app():
    global root
    global agenda
    root = tk.Tk()
    root.title("LanChat by ZANTO")
    root.minsize(300, 400)

    def on_close():
        chat.cerrar()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    chat.iniciar_socket()

    mostrar_red(root)

    chat.iniciar_receptor()
    agenda = storage.load()
    root.after(100, drenar_cola)

    root.mainloop()


def mostrar_red(root):
    frame = tk.Frame(root)
    frame.pack(fill="both", expand=True)

    tk.Label(frame, text="IPv4 (192.168.x.x/24):").pack(pady=5)
    entrada = tk.Entry(frame)
    entrada.pack(pady=5)

    def escanear():
        red = entrada.get().strip()
        if auxiliar.validate_ipv4(red) == -1:
            return

        tk.Label(frame, text=f"Escaneando la red: {red}").pack()
        boton.config(state="disabled")
        barra = ttk.Progressbar(frame, mode="indeterminate")
        barra.pack(pady=5)
        barra.start()
        threading.Thread(target=worker, args=(red,), daemon=True).start()



    boton = tk.Button(frame, text="Escanear", command=escanear)
    boton.pack(pady=10)

    def worker(red):
        dispositivos = scanner.start_scanner(red)
        root.after(0, lambda:finish(dispositivos))

    def finish(dispositivos):
        frame.destroy()
        mostrar_hosts(root, dispositivos)

def mostrar_hosts(root, dispositivos):
    frame = tk.Frame(root)
    frame.pack(fill="both", expand=True)

    tk.Label(frame, text="Choose with who u chat:").pack(pady=5)

    lista = tk.Listbox(
        frame, height=len(dispositivos)
    )  # todos los widgets d estas pantalals deben colgar del root y no del frame porque sino sobrevive
    lista.pack(fill="both", expand=True)
    idx = None

    for cont, d in enumerate(dispositivos):
        if d["ip"] == my_ip:
            idx= cont
        lista.insert("end", f"{d['ip']} - {d['mac']} - {d['hostname']}")
        ip_a_mac[d["ip"]] = d['mac']

    if idx is not None:
        lista.itemconfig(idx, {"fg": "dark green"}) # podria hacerlo -1 de default y listo pero bueno

    def conectar():
        selection = lista.curselection()
        if not selection:
            return

        idx = selection[0]
        receptor_ip = dispositivos[idx]["ip"]
        receptor_mac = dispositivos[idx]["mac"]
        frame.destroy()
        mostrar_chat(root, receptor_ip, receptor_mac)

    tk.Button(frame, text="Connect", command=conectar).pack(pady=10)


def agendar(conv):
    username = simpledialog.askstring("Agendar", "Nuevo contacto:", initialvalue=storage.get_username(conv["mac"], agenda) or "")
    if not username: return
    storage.set_username(conv["mac"], username, agenda)
    conv["label"].config(text=username)

def escribir(conv, linea, tag):
    conv["historial"].config(state="normal")
    conv["historial"].insert("end", linea + "\n", tag)
    conv["historial"].config(state="disabled")
    conv["historial"].see("end")

def on_enviar(conv):
    texto = conv["entrada"].get().strip()
    if not texto:
        return
    if not conv["fernet"]:
        notificar("NO SECURE CHANNEL YET")
        return
    dic = chat.create_msg(
        my_ip, texto
    )
    time = datetime.now().strftime("%H:%M:%S")
    paquete = crypto.envolver(dic, conv["fernet"])
    chat.send_msg(paquete, conv["ip"])
    pintar(conv, my_ip, dic["id"], formato(time, texto))
    conv["entrada"].delete(0, "end")
    storage.add_msg(conv["chat_storage"], my_ip, dic["id"], texto, time)
    storage.save_chat(conv["mac"], conv["chat_storage"])




def show_msg(conv, dic): #opt 1 de lo q llega
    emisor = dic["emisor"]  # dsp con addr[0] tendria q validar la identidad
    msg = dic["content"]["txt"]
    id = dic["id"]
    time = datetime.now().strftime("%H:%M:%S")
    storage.add_msg(conv["chat_storage"], emisor, id, msg, time)
    storage.save_chat(conv["mac"], conv["chat_storage"])

    if storage.get_notification(conv["mac"], agenda) != False and root.focus_displayof() is None:
        notificar(msg)

    if conv.get("historial"):
        pintar(conv, emisor, id, formato(time, msg))
    else:
        conv["no_leidos"] += 1


def delete_msg(conv, dic): #opt 2 de lo q llega
    tag = get_tag_opt_2_3(dic)
    borrar_local(conv, tag)
    emisor = dic["emisor"]
    id = dic["content"]["idObjetivo"]
    storage.delete_msg(conv["chat_storage"],emisor,id)
    storage.save_chat(conv["mac"], conv["chat_storage"])

def edit_msg(conv, dic): #opt 3 de lo q llega
    tag = get_tag_opt_2_3(dic)
    newMsg = dic["content"]["txt"]
    emisor = dic["emisor"]
    id = dic["content"]["idObjetivo"]
    idx = storage.get_pos(conv["chat_storage"], emisor, id)
    time = conv["chat_storage"][idx]["time"] if idx is not None else "Unreachable"
    linea = formato(time, newMsg)
    editar_local(tag, linea, conv)
    storage.edit_msg(conv["chat_storage"],emisor,id,newMsg)
    storage.save_chat(conv["mac"], conv["chat_storage"])

def procesar_cifrado(conv, dic):
    if chat.validate_dic(dic) == 1:
        match dic["tipo"]:
            case "msg":    show_msg(conv, dic)
            case "delete": delete_msg(conv, dic)
            case "edit":   edit_msg(conv, dic)

def drenar_pendientes(conv):
    for raw in conv["pendientes"]:
        tipo, payload = crypto.desenvolver(raw, conv["fernet"])
        if tipo == "cifrado":
            procesar_cifrado(conv, payload)
    conv["pendientes"].clear()

def helper_completar_handshake(conv, payload):
    conv["fernet"] = crypto.derivar_fernet(payload)
    boton = conv.get("boton")
    if boton:
        boton.config(state="normal", text="Enviar/Send")
    drenar_pendientes(conv)

def drenar_cola():
    while True:
        try:
            raw, addr = chat.cola.get_nowait()

        except queue.Empty:
            break

        mac = resolver_mac(addr[0])
        if not mac:
            if addr[0] in esperando_mac:
                esperando_mac[addr[0]].append(raw)
            else:
                esperando_mac[addr[0]] = [raw]
            continue

        conv = obtener_conv(mac, addr[0])

        procesar_paquete(conv, raw, addr[0])

    root.after(100, drenar_cola)

def borrar_local(conv, tag):
    tupla = conv["historial"].tag_ranges(tag)
    if tupla:
        conv["historial"].config(state="normal")
        conv["historial"].delete(tupla[0], tupla[1])
        conv["historial"].tag_delete(tag)
        conv["historial"].config(state="disabled")
        return True
    else:
        return False

def editar_local(tag, newMsg, conv):
    tupla = conv["historial"].tag_ranges(tag)
    if tupla:
        real_tags = conv["historial"].tag_names(tupla[0])
        conv["historial"].config(state="normal")
        conv["historial"].delete(tupla[0], tupla[1])
        conv["historial"].insert(tupla[0], newMsg+"\n", real_tags)
        conv["historial"].config(state="disabled")
        return True
    else:
        return False

def helper_menu(event, conv):
    idx = conv["historial"].index(f"@{event.x},{event.y}")
    tags = conv["historial"].tag_names(idx)
    tag = next((t for t in tags if "#" in t), None)
    if tag is None:
        return False
    else:
        return tag

def helper_username(conv):
    return storage.get_username(conv["mac"], agenda) or conv["ip"]

def pintar(conv, emisor, id, txt):
    alineacion = "mine" if emisor == my_ip else "others"
    tag= (f"{emisor}#{id}", alineacion)
    escribir(conv, txt, tag)

def formato(time, txt):
    return f"[{time}] --- {txt}"

def get_tag_opt_2_3(dic):
    emisor = dic["emisor"]
    id = dic["content"]["idObjetivo"]
    tag = f"{emisor}#{id}"

    return tag

def notificar(texto):
    ventana = tk.Toplevel(root) # gracias a esto no me bloquea toda la app
    tk.Label(ventana, text=texto).pack(padx=20, pady=10)
    ventana.after(3000, ventana.destroy)

def mostrar_chat(root, receptor_ip, receptor_mac):

    conv = obtener_conv(receptor_mac, receptor_ip)

    paquete = crypto.envolver_handshake(crypto.my_public, "hs_init")
    chat.send_msg(paquete, receptor_ip)

    frame = tk.Frame(root)
    header = tk.Frame(root)
    header.pack(side="top", fill="x")
    frame.pack(fill="both", expand=True)



    def reintentar_handshake():
        if conv["fernet"] is not None:
            return
        if conv["intentos"] >= MAX_INTENTOS:
            conv["boton"].config(text="Sin conexión segura")
            messagebox.showwarning("Sin conexión segura", "No se pudo establecer una conversación cifrada.")
            return
        chat.send_msg(crypto.envolver_handshake(crypto.my_public, "hs_init"), conv["ip"])
        conv["intentos"] += 1
        root.after(TIMEOUT_MS, reintentar_handshake)




    def on_clickl(event):
        tag = helper_menu(event, conv)
        if not tag:
            return
        menu = tk.Menu(root, tearoff=0)
        menu.add_command(label="Borrar para mi", command=lambda: self_delete(tag))
        if tag.split("#")[0] == my_ip:
            menu.add_command(label="Borrar para ambos", command=lambda: all_delete(tag))
        menu.tk_popup(event.x_root, event.y_root)

    def on_clickr(event):
        tag = helper_menu(event, conv)
        if not tag:
            return
        menu = tk.Menu(root, tearoff=0)
        if tag.split("#")[0]== my_ip:
            menu.add_command(label="Editar mensaje", command=lambda: all_edit(tag))
        menu.tk_popup(event.x_root, event.y_root)

    def on_clickRename(event):
        menu = tk.Menu(root, tearoff=0)
        menu.add_command(label="Agendar/Rename", command=lambda: agendar(conv))
        activo = storage.get_notification(conv["mac"], agenda) != False
        menu.add_command(label=f"Notificaciones: {'ON' if activo else 'OFF'}",
                         command=lambda: storage.toggle_notification(conv["mac"], agenda))

        menu.tk_popup(event.x_root, event.y_root) # esto va al final porque sino muestro algo incompleto


    def all_edit(tag):
        newMsg = simpledialog.askstring("Editar", "Nuevo texto:")
        if not newMsg:
            return
        time = "Unreachable"
        emisor, id_str = tag.split("#")
        id = int(id_str)
        idx = storage.get_pos(conv["chat_storage"], emisor, id)
        time = conv["chat_storage"][idx]["time"] if idx is not None else time
        linea = formato(time, newMsg)
        tupla = editar_local(tag, linea, conv)

        if tupla:
            id = int(tag.split("#")[1])
            dic = chat.create_msg(my_ip, txt=newMsg, tipo="edit", idObjetivo=id)
            paquete = crypto.envolver(dic, conv["fernet"])
            chat.send_msg(paquete, conv["ip"])

            storage.edit_msg(conv["chat_storage"], my_ip, id, newMsg)
            storage.save_chat(conv["mac"], conv["chat_storage"])

    def self_delete(tag):
        borrar_local(conv, tag)
        emisor, id_str = tag.split("#")
        id = int(id_str)
        storage.delete_msg(conv["chat_storage"], emisor, id)
        storage.save_chat(conv["mac"], conv["chat_storage"])

    def all_delete(tag):
        rt = borrar_local(conv, tag)
        if rt:
            id = int(tag.split("#")[1])
            dic = chat.create_msg(my_ip, tipo="delete", idObjetivo=id)
            paquete = crypto.envolver(dic, conv["fernet"])
            chat.send_msg(paquete, conv["ip"])
            emisor, id_str = tag.split("#")
            id = int(id_str)
            storage.delete_msg(conv["chat_storage"], emisor, id)
            storage.save_chat(conv["mac"], conv["chat_storage"])



    historial = tk.Text(frame, state="disabled")
    historial.tag_config("mine", justify="right")
    historial.tag_config("others", justify="left")
    historial.pack(fill="both", expand=True)
    historial.bind("<Button-1>", on_clickl)
    historial.bind("<Button-3>", on_clickr)

    entrada = tk.Entry(frame)
    entrada.pack(fill="x")

    boton = tk.Button(frame, text="Conectando..." if not conv["fernet"] else "Send/Enviar", command=lambda : on_enviar(conv), state="disabled" if not conv["fernet"] else "normal")
    boton.pack()
    entrada.bind("<Return>", lambda e: on_enviar(conv))

    def msg_recovery(chat_storage):
        for msg in chat_storage:
            pintar(conv, msg["emisor"], msg["id"], formato(msg["time"], msg["txt"]))


    label = tk.Label(header, text=helper_username(conv))
    label.pack(side="right")
    label.bind("<Button-1>", on_clickRename)

    conv["label"] = label
    conv["historial"] = historial
    conv["entrada"] = entrada
    conv["boton"] = boton

    msg_recovery(conv["chat_storage"])

    root.after(TIMEOUT_MS, reintentar_handshake)
