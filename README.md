# LanChat

Chat punto a punto para redes locales, escrito en Python. Descubre los hosts de la LAN con un escaneo ARP propio, establece un canal cifrado de extremo a extremo con cada peer mediante un handshake X25519, y expone todo en una interfaz gráfica de escritorio.

Proyecto extra del roadmap de Python para ciberseguridad — reutiliza el ARP scanner de la Fase 1 y aplica criptografía asimétrica sobre un protocolo de mensajes propio.

> **Estado: funcional, en desarrollo.** Todo lo listado en *Features* anda de punta a punta. Lo que falta está en [Roadmap](#roadmap), y las limitaciones de diseño conocidas están documentadas en [Limitaciones conocidas](#limitaciones-conocidas) — leerlas antes de usarlo para algo que importe.

---

## Por qué

La motivación original fue tener la certeza de que un mensaje enviado en mi propia red es efectivamente mío y de nadie más: sin servidor intermedio, sin nube, sin cuenta. La primera versión mandaba JSON en texto plano por UDP — lo verifiqué con [mi propio sniffer](https://github.com/ThiagoFernandez/Sniffer), que mostraba cada mensaje legible en la captura. Esa comprobación fue la que motivó la capa de cifrado que tiene hoy.

---

## Features

- **Descubrimiento automático de la LAN** — escaneo ARP con Scapy sobre el rango que indiques (`192.168.1.0/24`)
- **Resolución de nombres en dos pasos** — DNS inverso y, si falla, consulta NetBIOS (UDP/137)
- **Cifrado de extremo a extremo** — intercambio de claves X25519, derivación con HKDF-SHA256 y cifrado del payload con Fernet (AES-128-CBC + HMAC-SHA256)
- **Claves efímeras por sesión** — el par X25519 se genera al iniciar el programa; al cerrarlo, la clave desaparece
- **Handshake con reintentos** — hasta 5 intentos cada 1,5 s; si vence, la UI avisa que no hay canal seguro en vez de mandar en claro
- **Cola de pendientes** — los mensajes cifrados que llegan antes de que termine el handshake se guardan y se procesan cuando la clave está lista, en vez de descartarse
- **Historial persistente por peer** — un JSON por MAC, que se recarga al reabrir la conversación
- **Editar y borrar mensajes** — borrar solo para uno mismo, o para ambos lados (solo los propios); la edición se propaga al otro extremo
- **Agenda de contactos** — nombre asignado a cada MAC, editable, con notificaciones activables por contacto
- **Notificaciones no bloqueantes** — ventana `Toplevel` que se cierra sola a los 3 s y solo aparece si la app no tiene foco
- **Validación estricta de mensajes** — todo lo que entra pasa por un validador de esquema antes de tocar la UI

---

## Instalación

```bash
git clone https://github.com/ThiagoFernandez/LanChat.git
cd LanChat
pip install scapy pysmb
```

En Windows se necesita además [Npcap](https://npcap.com/) para que Scapy pueda mandar tramas ARP.

---

## Uso

```bash
# Linux/macOS: hace falta root para los sockets crudos del escaneo ARP
sudo python main.py

# Windows: ejecutar la terminal como administrador
python main.py
```

El flujo de la aplicación es:

1. Ingresar la red a escanear en formato CIDR (`192.168.1.0/24`) y presionar **Escanear**
2. Elegir de la lista con quién chatear — la fila verde es tu propia máquina
3. Esperar el handshake: el botón pasa de *Conectando...* a *Enviar/Send* cuando el canal quedó cifrado
4. Chatear. Clic izquierdo sobre un mensaje para borrarlo, clic derecho para editarlo, clic sobre el nombre del contacto para renombrarlo o silenciarlo

Ambos extremos tienen que estar corriendo LanChat en la misma LAN, con el puerto **UDP 40000** libre.

---

## Arquitectura

| Módulo | Responsabilidad |
|--------|-----------------|
| `main.py` | Punto de entrada; solo levanta la GUI |
| `gui.py` | Interfaz tkinter, máquina de estados de la conversación y bombeo de la cola de red |
| `chat.py` | Socket UDP, construcción y validación del esquema de mensajes, hilo receptor |
| `crypto.py` | Handshake X25519, derivación HKDF y envoltura/desenvoltura Fernet |
| `scanner.py` | Escaneo ARP, resolución de hostnames y NetBIOS |
| `storage.py` | Persistencia: agenda de contactos, historial por peer y contador de IDs |
| `auxiliar.py` | Validaciones de entrada y utilidades compartidas |

El hilo de red escribe en una `queue.Queue` y la GUI la drena cada 100 ms con `root.after()`. Así ningún paquete entrante toca widgets de tkinter desde un hilo secundario, que es la causa clásica de cuelgues en aplicaciones tkinter con red.

---

## Protocolo

Todo viaja como JSON sobre UDP/40000. Hay un sobre exterior que indica el tipo, y un sobre interior cifrado.

**Handshake** (en claro, es una clave pública):

```json
{ "tipo": "hs_init", "data": "<clave pública X25519 en base64>" }
```

El receptor responde con `hs_reply` y su propia clave pública. Ambos lados derivan el mismo secreto compartido con `exchange()` y lo pasan por HKDF-SHA256 para obtener la clave Fernet.

**Mensaje** (cifrado):

```json
{ "tipo": "cifrado", "data": "<token Fernet>" }
```

Dentro del token viaja el mensaje real:

```json
{
  "tipo": "msg",
  "id": 42,
  "emisor": "192.168.1.35",
  "content": { "txt": "hola", "idObjetivo": null }
}
```

Los tipos internos son `msg`, `edit` y `delete`. En `edit` y `delete`, `idObjetivo` apunta al ID del mensaje afectado.

---

## Limitaciones conocidas

Son limitaciones de diseño asumidas, no bugs pendientes:

- **El handshake no está autenticado.** X25519 sin verificación de identidad protege contra un atacante pasivo que escucha, pero no contra uno activo: quien pueda interceptar y reenviar tráfico en la LAN (por ejemplo vía ARP spoofing) puede montarse en el medio y hacer un handshake con cada punta. Resolverlo requiere autenticar las claves — huellas verificadas fuera de banda o un secreto previamente compartido.
- **La identidad se apoya en la MAC**, que es trivialmente falsificable. Sirve para organizar contactos, no como control de acceso.
- **UDP sin confirmación de entrega ni orden.** Un mensaje perdido se pierde en silencio.
- **`recvfrom(1024)`**: los mensajes que superan ese tamaño se truncan. No hay fragmentación ni reensamblado.
- **El historial se guarda en claro** en disco. El cifrado protege el mensaje en tránsito, no en reposo.
- **Solo redes privadas** — el validador acepta rangos `10.x`, `172.16-31.x` y `192.168.x`.
- **Requiere privilegios de administrador** por los sockets crudos del escaneo ARP.
- **Sin IPv6.**

---

## Roadmap

- [ ] Autenticar el handshake para cerrar el MITM (verificación de huellas)
- [ ] Bloqueo y desbloqueo de contactos por nombre, sin exponer IP ni MAC
- [ ] Modo efímero: conversación que no toca el disco
- [ ] Fragmentación de mensajes largos
- [ ] Cifrado del historial en reposo

---

## Consideraciones legales

El escaneo ARP solo debe usarse en redes propias o con autorización explícita del responsable.

---

*Parte del roadmap de Python para Ciberseguridad*
