import queue
import tkinter as tk

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
        dispositivos = scanner.start_scanner(red)
        frame.destroy()
        mostrar_hosts(root, dispositivos)

    tk.Button(frame, text="Escanear", command=escanear).pack(pady=10)


def mostrar_hosts(root, dispositivos):
    frame = tk.Frame(root)
    frame.pack(fill="both", expand=True)

    tk.Label(frame, text="Choose with who u chat:").pack(pady=5)

    lista = tk.Listbox(
        frame, height=len(dispositivos)
    )  # todos los widgets d estas pantalals deben colgar del root y no del frame porque sino sobrevive
    lista.pack(fill="both", expand=True)
    for d in dispositivos:
        lista.insert("end", f"{d['ip']} - {d['hostname']}")

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
    def on_click(event):
        idx = historial.index(f"@{event.x},{event.y}")
        tags = historial.tag_names(idx)
        tag = next((t for t in tags if "#" in t), None)
        if tag is None:
            return # verifico q este el #
        menu = tk.Menu(root, tearoff=0)
        menu.add_command(label="Borrar para mi", command=lambda: self_delete(tag))
        if tag.split("#")[0] == ip:
            menu.add_command(label="Borrar para ambos", command=lambda: all_delete(tag))
        menu.tk_popup(event.x_root, event.y_root)

    def self_delete(tag):
        borrar_local(tag)

    def all_delete(tag):
        rt = borrar_local(tag)
        if rt:
            id = int(tag.split("#")[1])
            dic = chat.create_msg(ip, id, "delete")
            j = chat.encode_dic(dic)
            chat.send_msg(j, receptor)

    historial = tk.Text(frame, state="disabled")
    historial.pack()
    historial.bind("<Button-1>", on_click)
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
        )  # por ahora no pongo tipo porque eso seria como un boto/checklist q marca el user

        j = chat.encode_dic(dic)
        chat.send_msg(j, receptor)
        tag = f"{ip}#{dic["id"]}"
        escribir(f"Yo: {texto}", tag)
        entrada.delete(0, "end")

    boton = tk.Button(frame, text="Enviar/Send", command=on_enviar)
    boton.pack()
    entrada.bind("<Return>", lambda e: on_enviar())

    def show_msg(dic):
        emisor = dic["emisor"]  # dsp con addr[0] tendria q validar la identidad
        msg = dic["content"]
        id = dic["id"]
        tag = f"{emisor}#{id}"
        escribir(f"{emisor}: {msg} --- id:{id}", tag)

    def delete_msg(dic):
        emisor = dic["emisor"]
        id = dic["content"]
        tag = f"{emisor}#{id}"
        tupla = historial.tag_ranges(tag)
        if tupla:
            historial.delete(tupla[0], tupla[1])
            historial.tag_delete(tag)

    def edit_msg(dic):
        # igual aca solo se puede mensajes que uno envio, esto lo que haria seria obligar al otro editar ese mnsaje asi ambos ven lo mismo
        pass

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
            historial.delete(tupla[0], tupla[1])
            historial.tag_delete(tag)
            return True
        else:
            return False

    chat.iniciar_receptor()
    root.after(100, drenar_cola)
