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

def save_chat(mac, chat):
    file_name = f"{clean_mac(mac)}.json"
    with open(file_name, "w", encoding="UTF-8") as f:
        json.dump(chat, f, indent=4, ensure_ascii=False)

def create_chat():
    return []

def add_msg(chat, emisor, id, texto, hora):
    chat.append({
        "emisor": emisor,
        "id": id,
        "txt": texto,
        "time": hora
    })

def edit_msg(chat, emisor, id, new_txt):
    idx = get_pos(chat, emisor, id)
    if idx is not None:
        chat[idx]["txt"] = new_txt
    #save_chat() estp se llama dsp de esto pero no en esta funcion

def delete_msg(chat, emisor, id):
    idx = get_pos(chat, emisor, id)
    if idx is not None:
        chat.pop(idx)
            #save_chat() estp se llama dsp de esto pero no en esta funcion

def load_chat(mac):
    file_name = f"{clean_mac(mac)}.json"
    try:
        with open(file_name, "r", encoding="UTF-8") as f:
            chat = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        chat = create_chat()
        save_chat(mac, chat)
    return chat

def clean_mac(mac):
    mm = [m if m != ":" else "-" for m in mac]
    return "".join(mm).lower()

def restore_mac(mac):
    mm = [m if m != "-" else ":" for m in mac]
    return "".join(mm).lower()

def get_pos(chat, emisor, id):
    for i, c in enumerate(chat):
        if c["emisor"] == emisor and c["id"] == id:
            return i
