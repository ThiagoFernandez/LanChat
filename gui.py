import queue
import tkinter as tk

import chat


def iniciar_gui(receptor):
    root = tk.Tk()
    root.title("LanChat by ZANTO")
    historial = tk.Text(root, state="disabled")
    historial.pack()
    entrada = tk.Entry(root)
    entrada.pack()

    def escribir(linea):  # helper: te evita repetir el config/insert/config 3 veces
        historial.config(state="normal")
        historial.insert("end", linea + "\n")
        historial.config(state="disabled")
        historial.see("end")

    def on_enviar():
        texto = entrada.get().strip()
        if not texto:
            return
        chat.send_msg(texto, receptor)
        escribir(f"Yo: {texto}")  # eco propio
        entrada.delete(0, "end")

    boton = tk.Button(root, text="Enviar/Send", command=on_enviar)
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
    root.mainloop()