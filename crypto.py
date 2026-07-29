from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey
import base64
import json

my_private = X25519PrivateKey.generate()
my_public = my_private.public_key()

def leer_tipo(raw):
    try:
        return json.loads(raw).get("tipo")
    except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
        return None

def envolver_handshake(public_key, tipo): # tipo seria hs_init o hs_reply
    # 1. clave pública -> bytes crudos
    public_key_bytes = public_key.public_bytes(
        Encoding.Raw,
        PublicFormat.Raw
    )

    # 2. bytes -> base64 -> str
    data = base64.urlsafe_b64encode(public_key_bytes).decode("ascii")

    # 3. paquete exterior
    dict_exterior = {
        "tipo": tipo, # rn es un subtipo de hs y no mas hs solo
        "data": data
    }

    # 4. dict -> JSON -> bytes
    return json.dumps(dict_exterior).encode("UTF-8")

def envolver(dict_interior, fernet):
    json_string = json.dumps(dict_interior).encode("UTF-8")
    token = fernet.encrypt(json_string)
    resultado = token.decode("ascii")
    dict_exterior = {
        "tipo": "cifrado",
        "data": resultado
    }
    dict_exterior_json = json.dumps(dict_exterior).encode("UTF-8")

    return dict_exterior_json

def desenvolver(dict_exterior_json, fernet):
    try:
        # Paso 5 inverso: bytes -> dict exterior
        dict_exterior = json.loads(dict_exterior_json)

        tipo = dict_exterior.get("tipo")

        if tipo == "cifrado":
            # Paso 4 inverso
            data = dict_exterior.get("data")
            if data is None:
                return (None, None)

            # Paso 3 inverso: str -> bytes
            token = data.encode("ascii")

            # Paso 2 inverso: descifrar
            json_bytes = fernet.decrypt(token)

            # Paso 1 inverso: bytes -> dict interior
            dict_interior = json.loads(json_bytes)

            return ("cifrado", dict_interior)

        elif tipo in ("hs_init", "hs_reply"):
            data = dict_exterior.get("data")
            if data is None:
                return (None, None)

            public_key_bytes = base64.urlsafe_b64decode(data.encode("ascii"))
            public_key = X25519PublicKey.from_public_bytes(public_key_bytes)

            return (tipo, public_key)

        else:
            return (None, None)

    except (json.JSONDecodeError, UnicodeError, InvalidToken, AttributeError, TypeError, ValueError):
        return (None, None)

def derivar_fernet(public_key):
    secret = my_private.exchange(public_key)
    key = HKDF(algorithm=SHA256(), length=32, salt=None, info=None).derive(secret) # ts has to be identic
    return Fernet(base64.urlsafe_b64encode(key))
