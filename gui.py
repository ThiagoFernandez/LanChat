import queue
import tkinter as tk

import auxiliar
import chat
import scanner


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

    historial = tk.Text(frame, state="disabled")
    historial.pack()
    entrada = tk.Entry(frame)
    entrada.pack()

    def escribir(linea):
        historial.config(state="normal")
        historial.insert("end", linea + "\n")
        historial.config(state="disabled")
        historial.see("end")

    def on_enviar():
        texto = entrada.get().strip()
        if not texto:
            return
        chat.send_msg(texto, receptor)
        escribir(f"Yo: {texto}")
        entrada.delete(0, "end")

    boton = tk.Button(frame, text="Enviar/Send", command=on_enviar)
    boton.pack()
    entrada.bind("<Return>", lambda e: on_enviar())

    def drenar_cola():
        while True:
            try:
                msg, addr = chat.cola.get_nowait()
            except queue.Empty:
                break
            escribir(f"{addr[0]}: {msg}")
        root.after(100, drenar_cola)

    chat.iniciar_receptor()
    root.after(100, drenar_cola)
