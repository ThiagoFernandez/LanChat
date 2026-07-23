import json

def load():
    try:
        with open("agenda.json", "r", encoding="UTF-8") as f:
            agenda = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        agenda = create_agenda()
        save(agenda)

    return agenda


def save(agenda):
    with open("agenda.json", "w", encoding="UTF-8") as f:
        json.dump(agenda, f, indent=4, ensure_ascii=False)

def get_username(mac, agenda):
    normalized_mac = normalizar_mac(mac)
    username = agenda.get(normalized_mac)# la gui checkea que no sea None
    return username # aca podria dejar la validacion de si no tiene nombre, crearle uno(no obligo porque talvez no quiere agendarlo)
    # la validacion podria estar en esta llamada o en gui

def set_username(mac, username, agenda):
    normalized_mac = normalizar_mac(mac)
    agenda[normalized_mac] = username # aca no valido ni que eexista la mac ni que el username contenga texto
    save(agenda)

def create_agenda():
    agenda = {
    }

    return agenda

def normalizar_mac(mac):
    return mac.lower().strip()
