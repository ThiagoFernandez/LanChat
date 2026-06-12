import auxiliar
import chat
import gui
import scanner


def main():
    dispositivos = scanner.start_scanner()
    if not dispositivos:
        print("No se encontraron dispositivos")
        return

    hosts = scanner.get_hosts(dispositivos)
    auxiliar.show_options(hosts)
    opt = auxiliar.validate_number(hosts)
    if opt == -1:
        return
    receptor = hosts[opt - 1]

    gui.iniciar_gui(receptor[0])  # en un futuro paso la tupla entera


main()
