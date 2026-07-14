import queue
import tkinter as tk
from tkinter import simpledialog, ttk

import threading
import auxiliar
import chat
import scanner

ip = auxiliar.obtener_mi_ip()


def iniciar_app():

    root = tk.Tk()
    root.title("LanChat by ZANTO")
    root.minsize(300, 400)

    def on_close():
        chat.cerrar()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
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
    idx = 0
    cont=-1
    for d in dispositivos:
        cont+=1
        if d["ip"] == ip:
            idx= cont
        lista.insert("end", f"{d['ip']} - {d['hostname']}")

    lista.itemconfig(idx, {"fg": "dark green"})

    def conectar():
        selection = lista.curselection()
        if not selection:
            return

        idx = selection[0]
        receptor = dispositivos[idx]["ip"]
        frame.destroy()
        mostrar_chat(root, receptor)

    tk.Button(frame, text="Connect", command=conectar).pack(pady=10)


def mostrar_chat(root, receptor):
    frame = tk.Frame(root)
    frame.pack()
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

    def all_edit(tag):
        newMsg = simpledialog.askstring("Editar", "Nuevo texto:")
        if not newMsg:
            return
        linea = f"Yo: {newMsg}"
        tupla = editar_local(tag, linea)

        if tupla:
            id = int(tag.split("#")[1])
            dic = chat.create_msg(ip, txt=newMsg, tipo="edit", idObjetivo=id)
            j = chat.encode_dic(dic)
            chat.send_msg(j, receptor)

    def self_delete(tag):
        borrar_local(tag)

    def all_delete(tag):
        rt = borrar_local(tag)
        if rt:
            id = int(tag.split("#")[1])
            dic = chat.create_msg(ip, tipo="delete", idObjetivo=id)
            j = chat.encode_dic(dic)
            chat.send_msg(j, receptor)

    historial = tk.Text(frame, state="disabled")
    historial.pack()
    historial.bind("<Button-1>", on_clickl)
    historial.bind("<Button-3>", on_clickr)
    entrada = tk.Entry(frame)
    entrada.pack()

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

        j = chat.encode_dic(dic)
        chat.send_msg(j, receptor)
        tag = f"{ip}#{dic["id"]}"
        escribir(f"Yo: {texto}", tag)
        entrada.delete(0, "end")

    boton = tk.Button(frame, text="Enviar/Send", command=on_enviar)
    boton.pack()
    entrada.bind("<Return>", lambda e: on_enviar())

    def show_msg(dic): #opt 1 de lo q llega
        emisor = dic["emisor"]  # dsp con addr[0] tendria q validar la identidad
        msg = dic["content"]["txt"]
        id = dic["id"]
        tag = f"{emisor}#{id}"
        # if emisor == ip:
        #     emisor = "Yo"
        escribir(f"{emisor}: {msg}", tag)

    def delete_msg(dic): #opt 2 de lo q llega
        tag = get_tag_opt_2_3(dic)
        borrar_local(tag)

    def edit_msg(dic): #opt 3 de lo q llega
        tag = get_tag_opt_2_3(dic)
        newMsg = dic["content"]["txt"]
        emisor = dic["emisor"]
        # if emisor == ip:
            # emisor = "Yo"
        linea = f"{emisor}: {newMsg}"
        editar_local(tag, linea)


    def drenar_cola():
        while True:
            try:
                dic, addr = chat.cola.get_nowait()
            except queue.Empty:
                break

            match dic["tipo"]:
                case "msg":
                    show_msg(dic)
                case "delete":
                    delete_msg(dic)
                case "edit":
                    edit_msg(dic)
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
            historial.config(state="normal")
            historial.delete(tupla[0], tupla[1])
            historial.insert(tupla[0], newMsg+"\n", tag)
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


    chat.iniciar_receptor()
    root.after(100, drenar_cola)
