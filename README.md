# LanChat

Chat de red local (LAN) con **cifrado extremo a extremo**, escrito en Python con tkinter.
Sin servidor, sin cuentas, sin internet: los mensajes viajan por UDP directamente entre las
dos máquinas, y nadie que capture el tráfico puede leerlos.

> Proyecto personal de aprendizaje. El foco está en la **capa de seguridad** y en el manejo
> de red de bajo nivel, no en competir con un cliente de mensajería.

---

## Qué hace

| Área | Detalle |
|---|---|
| **Descubrimiento** | Escaneo ARP de la subred, resolución de hostname por DNS inverso con fallback a NetBIOS |
| **Cifrado E2E** | X25519 → HKDF-SHA256 → Fernet (AES-128-CBC + HMAC-SHA256), con handshake propio |
| **Mensajería** | Enviar, **editar** y **borrar** (para uno o para ambos), con historial persistente |
| **Multi-conversación** | Barra de contactos ordenada por actividad, con no leídos y estado de alcanzabilidad |
| **Identidad por MAC** | El ruteo es por MAC, no por IP: sobrevive a que el DHCP reasigne direcciones |
| **Agenda** | Alias por contacto y notificaciones configurables individualmente |

---

## Requisitos

- **Python 3.10+** (usa `match`/`case`)
- **Permisos de administrador / root** — scapy necesita acceso crudo a la interfaz de red
- **Windows:** [Npcap](https://npcap.com/) instalado *(marcá "WinPcap API-compatible mode")*.
  Sin esto scapy no puede enviar los ARP.
- **Linux:** `libpcap`, y correr con `sudo`
- Las dos máquinas en la **misma red local**, con el **puerto UDP 40000** abierto en el firewall

## Instalación

```bash
git clone https://github.com/ThiagoFernandez/LanChat.git
cd LanChat
python -m venv .venv
```

```bash
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

## Uso

```bash
python main.py
```

1. Ingresá tu red en formato CIDR — por ejemplo `192.168.0.0/24` — y tocá **Escanear**.
   Solo acepta rangos privados (`10.x`, `172.16-31.x`, `192.168.x`).
2. Elegí un equipo de la lista y tocá **Connect**. El handshake arranca solo.
3. Cuando el botón pasa de *"Conectando…"* a *"Send/Enviar"*, el canal cifrado está listo.

Del lado izquierdo queda la **barra de contactos**: los que ya tienen conversación aparecen
ahí ordenados por el mensaje más reciente, con un contador de no leídos. Los que no están en
el último escaneo se ven en gris — se puede leer su historial, pero no enviarles.

**Atajos:** clic izquierdo sobre un mensaje para borrarlo · clic derecho para editarlo *(solo
los propios)* · clic sobre el nombre en el encabezado para renombrar el contacto o silenciarlo.

---

## Cómo funciona el cifrado

Cada instancia genera un par **X25519 efímero** al arrancar. Al abrir una conversación se
manda un `hs_init` con la clave pública; el otro responde con `hs_reply` y la suya.

Con eso, cada lado hace el intercambio Diffie-Hellman y deriva la misma clave simétrica con
**HKDF-SHA256**, que se usa para instanciar un **Fernet**. A partir de ahí, todo mensaje viaja
como un sobre `{"tipo": "cifrado", "data": <token>}`.

```
Máquina A                                    Máquina B
    │                                            │
    │──────────  hs_init  (pública de A)  ──────▶│
    │◀─────────  hs_reply (pública de B)  ───────│
    │                                            │
    │  DH + HKDF → clave compartida → Fernet     │
    │                                            │
    │◀════════  mensajes cifrados  ═════════════▶│
```

**Claves efímeras por ejecución:** si una de las dos partes reinicia, su par cambia y el
handshake se rehace. Nada de lo cifrado antes se puede descifrar con las claves nuevas.

Todo lo que entra de la red se valida en el borde antes de tocarlo: JSON malformado, base64
inválido, tokens adulterados o campos de más se descartan en silencio en vez de propagar la
excepción.

---

## ⚠️ Limitaciones conocidas

Las digo explícitamente porque son parte del aprendizaje del proyecto:

- **No hay autenticación del peer.** El handshake lo completa quien conteste primero, así que
  el cifrado protege contra un observador pasivo pero **no contra un man-in-the-middle
  activo**. La solución —verificación de fingerprint— está en el roadmap.
- **Sin entrega diferida.** No hay servidor: si el destinatario está apagado, el mensaje se
  pierde.
- **Mensajes limitados a 1024 bytes.** No hay fragmentación todavía.
- **El historial se guarda en claro** en disco. El cifrado es en tránsito, no en reposo.

## Estructura

```
main.py       punto de entrada
gui.py        interfaz, estado de conversaciones y ruteo de paquetes
chat.py       socket UDP, protocolo de mensajes y validación
crypto.py     X25519, HKDF y Fernet — la capa criptográfica, aislada
scanner.py    descubrimiento ARP y resolución de hostnames
storage.py    persistencia de agenda e historiales
auxiliar.py   utilidades varias (validación de IPv4, IP local)
test_crypto.py  tests de la capa cripto, incluidos casos adversariales
```

Los archivos de datos que genera la app —`agenda.json`, los historiales por MAC y
`cont.txt`— quedan fuera del repositorio: contienen direcciones reales de la red donde se
ejecutó.

---

## Roadmap

- [ ] Handshake autenticado por fingerprint *(cierra el MITM)*
- [ ] Bloqueo y desbloqueo de contactos
- [ ] Fragmentación de mensajes largos
- [ ] Transferencia de archivos por TCP
- [ ] Cifrado del historial en reposo
