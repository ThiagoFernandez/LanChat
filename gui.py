import tkinter as tk

import chat


def iniciar_gui(receptor):
    root = tk.Tk()
    root.title("LanChat by ZANTO")

    historial = tk.Text(root, state="disabled")
    historial.pack()
    entrada = tk.Entry(root)
    entrada.pack()

    def on_enviar():
        texto = entrada.get().strip()
        if not texto:
            return
        chat.send_msg(texto, receptor)  # receptor lo ve por el closure
        # TODO: eco en historial (config normal -> insert -> disabled -> see "end")
        entrada.delete(0, "end")

    boton = tk.Button(root, text="Enviar/Send", command=on_enviar)  # SIN parentesis
    boton.pack()
    entrada.bind("<Return>", lambda e: on_enviar())  # CON parentesis

    root.mainloop()
