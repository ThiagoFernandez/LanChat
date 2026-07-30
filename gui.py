import queue
import tkinter as tk
from tkinter import simpledialog, ttk, messagebox
from datetime import datetime
import threading
import auxiliar
import chat
import scanner
import storage
import crypto

MAX_INTENTOS = 5
TIMEOUT_MS = 1500
ip = auxiliar.obtener_mi_ip()



def iniciar_app():

    root = tk.Tk()
    root.title("LanChat by ZANTO")
    root.minsize(300, 400)

    def on_close():
        chat.cerrar()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    chat.iniciar_socket()
    mostrar_red(root)
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
        if d["ip"] == ip:
            idx= cont
        lista.insert("end", f"{d['ip']} - {d['mac']} - {d['hostname']}")

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


def mostrar_chat(root, receptor_ip, receptor_mac):
    pendientes = []   # FIFO de cifrados que llegaron sin clave
    intentos = 0
    fernet_peer = None   # el Fernet de este peer; None hasta que el hs este finished
    paquete = crypto.envolver_handshake(crypto.my_public, "hs_init")
    chat.send_msg(paquete, receptor_ip)
    agenda = storage.load()
    chat_storage = storage.load_chat(receptor_mac)
    frame = tk.Frame(root)
    header = tk.Frame(root)
    header.pack(side="top", fill="x")
    frame.pack(fill="both", expand=True)

    def reintentar_handshake():
        nonlocal intentos
        if fernet_peer is not None:
            return
        if intentos >= MAX_INTENTOS:
            boton.config(text="Sin conexión segura")
            messagebox.showwarning("Sin conexión segura", "No se pudo establecer una conversación cifrada.")
            return
        chat.send_msg(crypto.envolver_handshake(crypto.my_public, "hs_init"), receptor_ip)
        intentos += 1
        root.after(TIMEOUT_MS, reintentar_handshake)

    def notificar(texto):
        ventana = tk.Toplevel(root) # gracias a esto no me bloquea toda la app
        tk.Label(ventana, text=texto).pack(padx=20, pady=10)
        ventana.after(3000, ventana.destroy)

    def on_clickl(event):
        tag = helper_menu(event)
        if not tag:
            return
        menu = tk.Menu(root, tearoff=0)
        menu.add_command(label="Borrar para mi", command=lambda: self_delete(tag))
        if tag.split("#")[0] == ip:
            menu.add_command(label="Borrar para ambos", command=lambda: all_delete(tag))
        menu.tk_popup(event.x_root, event.y_root)

    def on_clickr(event):
        tag = helper_menu(event)
        if not tag:
            return
        menu = tk.Menu(root, tearoff=0)
        if tag.split("#")[0]== ip:
            menu.add_command(label="Editar mensaje", command=lambda: all_edit(tag))
        menu.tk_popup(event.x_root, event.y_root)

    def on_clickRename(event):
        menu = tk.Menu(root, tearoff=0)
        menu.add_command(label="Agendar/Rename", command=agendar)
        activo = storage.get_notification(receptor_mac, agenda) != False
        menu.add_command(label=f"Notificaciones: {'ON' if activo else 'OFF'}",
                         command=lambda: storage.toggle_notification(receptor_mac, agenda))

        menu.tk_popup(event.x_root, event.y_root) # esto va al final porque sino muestro algo incompleto


    def all_edit(tag):
        newMsg = simpledialog.askstring("Editar", "Nuevo texto:")
        if not newMsg:
            return
        time = "Unreachable"
        emisor, id_str = tag.split("#")
        id = int(id_str)
        idx = storage.get_pos(chat_storage, emisor, id)
        time = chat_storage[idx]["time"] if idx is not None else time
        linea = formato(time, newMsg)
        tupla = editar_local(tag, linea)

        if tupla:
            id = int(tag.split("#")[1])
            dic = chat.create_msg(ip, txt=newMsg, tipo="edit", idObjetivo=id)
            paquete = crypto.envolver(dic, fernet_peer)
            chat.send_msg(paquete, receptor_ip)

            storage.edit_msg(chat_storage, ip, id, newMsg)
            storage.save_chat(receptor_mac, chat_storage)

    def self_delete(tag):
        borrar_local(tag)
        emisor, id_str = tag.split("#")
        id = int(id_str)
        storage.delete_msg(chat_storage, emisor, id)
        storage.save_chat(receptor_mac, chat_storage)

    def all_delete(tag):
        rt = borrar_local(tag)
        if rt:
            id = int(tag.split("#")[1])
            dic = chat.create_msg(ip, tipo="delete", idObjetivo=id)
            paquete = crypto.envolver(dic, fernet_peer)
            chat.send_msg(paquete, receptor_ip)
            emisor, id_str = tag.split("#")
            id = int(id_str)
            storage.delete_msg(chat_storage, emisor, id)
            storage.save_chat(receptor_mac, chat_storage)

    def agendar():
        username = simpledialog.askstring("Agendar", "Nuevo contacto:", initialvalue=storage.get_username(receptor_mac, agenda) or "")
        if not username: return
        storage.set_username(receptor_mac, username, agenda)
        label.config(text=username)

    historial = tk.Text(frame, state="disabled")
    historial.tag_config("mine", justify="right")
    historial.tag_config("others", justify="left")
    historial.pack(fill="both", expand=True)
    historial.bind("<Button-1>", on_clickl)
    historial.bind("<Button-3>", on_clickr)

    entrada = tk.Entry(frame)
    entrada.pack(fill="x")

    def escribir(linea, tag):
        historial.config(state="normal")
        historial.insert("end", linea + "\n", tag)
        historial.config(state="disabled")
        historial.see("end")

    def on_enviar():
        texto = entrada.get().strip()
        if not texto:
            return
        dic = chat.create_msg(
            ip, texto
        )
        time = datetime.now().strftime("%H:%M:%S")
        paquete = crypto.envolver(dic, fernet_peer)
        chat.send_msg(paquete, receptor_ip)
        pintar(ip, dic["id"], formato(time, texto))
        entrada.delete(0, "end")
        storage.add_msg(chat_storage, ip, dic["id"], texto, time)
        storage.save_chat(receptor_mac, chat_storage)



    boton = tk.Button(frame, text="Conectando...", command=on_enviar, state="disabled")
    boton.pack()
    entrada.bind("<Return>", lambda e: on_enviar())

    def show_msg(dic): #opt 1 de lo q llega
        emisor = dic["emisor"]  # dsp con addr[0] tendria q validar la identidad
        msg = dic["content"]["txt"]
        id = dic["id"]
        time = datetime.now().strftime("%H:%M:%S")
        pintar(emisor, id, formato(time, msg))
        storage.add_msg(chat_storage, emisor, id, msg, time)
        storage.save_chat(receptor_mac, chat_storage)

        if storage.get_notification(receptor_mac, agenda) != False and root.focus_displayof() is None:
            notificar(msg)

    def delete_msg(dic): #opt 2 de lo q llega
        tag = get_tag_opt_2_3(dic)
        borrar_local(tag)
        emisor = dic["emisor"]
        id = dic["content"]["idObjetivo"]
        storage.delete_msg(chat_storage,emisor,id)
        storage.save_chat(receptor_mac, chat_storage)

    def edit_msg(dic): #opt 3 de lo q llega
        tag = get_tag_opt_2_3(dic)
        newMsg = dic["content"]["txt"]
        emisor = dic["emisor"]
        id = dic["content"]["idObjetivo"]
        idx = storage.get_pos(chat_storage, emisor, id)
        time = chat_storage[idx]["time"] if idx is not None else "Unreachable"
        linea = formato(time, newMsg)
        editar_local(tag, linea)
        storage.edit_msg(chat_storage,emisor,id,newMsg)
        storage.save_chat(receptor_mac, chat_storage)

    def procesar_cifrado(dic):
        if chat.validate_dic(dic) == 1:
            match dic["tipo"]:
                case "msg":    show_msg(dic)
                case "delete": delete_msg(dic)
                case "edit":   edit_msg(dic)

    def drenar_pendientes():
        for raw in pendientes:
            tipo, payload = crypto.desenvolver(raw, fernet_peer)
            if tipo == "cifrado":
                procesar_cifrado(payload)
        pendientes.clear()

    def drenar_cola():
        nonlocal fernet_peer
        while True:
            try:
                raw, addr = chat.cola.get_nowait()

            except queue.Empty:
                break

            if fernet_peer is None and crypto.leer_tipo(raw) == "cifrado":
                pendientes.append(raw)      # todavi no puedo descifrarlo → lo guardo
                continue

            tipo, payload = crypto.desenvolver(raw, fernet_peer)
            match tipo:
                case "hs_init":
                    fernet_peer = crypto.derivar_fernet(payload)
                    chat.send_msg(crypto.envolver_handshake(crypto.my_public, "hs_reply"), addr[0])
                    boton.config(state="normal", text="Enviar/Send")
                    drenar_pendientes()
                case "hs_reply":
                    fernet_peer = crypto.derivar_fernet(payload)
                    boton.config(state="normal", text="Enviar/Send")
                    drenar_pendientes()
                case "cifrado":
                    procesar_cifrado(payload)
                case _:
                    pass
        root.after(100, drenar_cola)

    def borrar_local(tag):
        tupla = historial.tag_ranges(tag)
        if tupla:
            historial.config(state="normal")
            historial.delete(tupla[0], tupla[1])
            historial.tag_delete(tag)
            historial.config(state="disabled")
            return True
        else:
            return False

    def editar_local(tag, newMsg):
        tupla = historial.tag_ranges(tag)
        if tupla:
            real_tags = historial.tag_names(tupla[0])
            historial.config(state="normal")
            historial.delete(tupla[0], tupla[1])
            historial.insert(tupla[0], newMsg+"\n", real_tags)
            historial.config(state="disabled")
            return True
        else:
            return False

    def helper_menu(event):
        idx = historial.index(f"@{event.x},{event.y}")
        tags = historial.tag_names(idx)
        tag = next((t for t in tags if "#" in t), None)
        if tag is None:
            return False
        else:
            return tag

    def get_tag_opt_2_3(dic):
        emisor = dic["emisor"]
        id = dic["content"]["idObjetivo"]
        tag = f"{emisor}#{id}"

        return tag

    def helper_username():
        return storage.get_username(receptor_mac, agenda) or receptor_ip

    def pintar(emisor, id, txt):
        alineacion = "mine" if emisor == ip else "others"
        tag= (f"{emisor}#{id}", alineacion)
        escribir(txt, tag)

    def msg_recovery(chat_storage):
        for msg in chat_storage:
            pintar(msg["emisor"], msg["id"], formato(msg["time"], msg["txt"]))

    def formato(time, txt):
        return f"[{time}] --- {txt}"

    label = tk.Label(header, text=helper_username())
    label.pack(side="right")
    label.bind("<Button-1>", on_clickRename)


    msg_recovery(chat_storage)
    chat.iniciar_receptor()
    root.after(100, drenar_cola)
    root.after(TIMEOUT_MS, reintentar_handshake)
