import json

def load():
    try:
        with open("agenda.json", "r", encoding="UTF-8") as f:
            agenda = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        agenda = create_agenda()


    for mac, v in agenda.items():
        if isinstance(v, str):          # formato viejardo
            agenda[mac] = {"username": v, "notif": True}
    save(agenda)
    return agenda


def save(agenda):
    with open("agenda.json", "w", encoding="UTF-8") as f:
        json.dump(agenda, f, indent=4, ensure_ascii=False)

def get_username(mac, agenda):
    normalized_mac = normalizar_mac(mac)
    dictt = agenda.get(normalized_mac)# la gui checkea que no sea None
    username = dictt["username"] if dictt is not None else None
    return username

def set_username(mac, username, agenda):
    entry = _get_entry(mac, agenda)   # referencia adentro de agenda
    entry["username"] = username
    save(agenda)

def toggle_notification( mac, agenda):
    entry = _get_entry(mac, agenda)   # referencia adentro de agenda
    entry["notif"] = not entry["notif"]
    save(agenda)

def get_notification( mac, agenda):
    normalized_mac=normalizar_mac(mac)
    dictt = agenda.get(normalized_mac)
    notif = dictt["notif"] if dictt is not None else None
    return notif

def _get_entry(mac, agenda):
    mac = normalizar_mac(mac)
    if mac not in agenda:
        agenda[mac] = {"username": None, "notif": True}
    return agenda[mac]

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

def load_contador():
    try:
        with open("cont.txt", "r", encoding="UTF-8") as f:
            cont = int(f.read().strip())
    except (FileNotFoundError, ValueError):
        cont = 0

    return cont

def save_contador(cont):
    with open("cont.txt", "w", encoding="UTF-8") as f:
        f.write(str(cont))
