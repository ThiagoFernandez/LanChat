from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey
import base64
import json

def envolver_handshake(public_key):
    # 1. clave pública -> bytes crudos
    public_key_bytes = public_key.public_bytes(
        Encoding.Raw,
        PublicFormat.Raw
    )

    # 2. bytes -> base64 -> str
    data = base64.urlsafe_b64encode(public_key_bytes).decode("ascii")

    # 3. paquete exterior
    dict_exterior = {
        "tipo": "handshake",
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

        elif tipo == "handshake":
            data = dict_exterior.get("data")
            if data is None:
                return (None, None)

            public_key_bytes = base64.urlsafe_b64decode(data.encode("ascii"))
            public_key = X25519PublicKey.from_public_bytes(public_key_bytes)

            return ("handshake", public_key)

        else:
            return (None, None)

    except (json.JSONDecodeError, UnicodeError, InvalidToken, AttributeError, TypeError, ValueError):
        return (None, None)




#ana
private_key_ana = X25519PrivateKey.generate()
public_key_ana = private_key_ana.public_key()

#beto
private_key_beto = X25519PrivateKey.generate()
public_key_beto = private_key_beto.public_key()


#ana
resultado_ana = private_key_ana.exchange(public_key_beto)
#beto
resultado_beto = private_key_beto.exchange(public_key_ana)

if resultado_ana == resultado_beto:
    print("funciona el secreto")

    ana_hkdf = HKDF(algorithm=SHA256(), length=32, salt=None, info=None).derive(resultado_ana) # ana
    beto_hkdf = HKDF(algorithm=SHA256(), length=32, salt=None, info=None).derive(resultado_beto) # beto


    fernet_ana = Fernet(base64.urlsafe_b64encode(ana_hkdf))
    fernet_beto = Fernet(base64.urlsafe_b64encode(beto_hkdf))

    token = fernet_ana.encrypt(b"hola")
    assert fernet_beto.decrypt(token) == b"hola"


    dict_original = {"tipo": "msg", "id": 1, "emisor": "1.2.3.4",
                     "content": {"txt": "hola", "idObjetivo": None}}

    envuelto = envolver(dict_original, fernet_ana)      # Ana envuelve
    tipo, recuperado = desenvolver(envuelto, fernet_beto)     # Beto desenvuelve

    assert tipo == "cifrado"
    assert recuperado == dict_original
    print("round-trip OK")


    paquete = envolver_handshake(public_key_ana)

    tipo, clave = desenvolver(paquete, None)

    assert tipo == "handshake"
    assert clave.public_bytes(Encoding.Raw, PublicFormat.Raw) == \
           public_key_ana.public_bytes(Encoding.Raw, PublicFormat.Raw)
