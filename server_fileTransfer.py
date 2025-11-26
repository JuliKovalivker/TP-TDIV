from socket import *
import sys
import os
from urllib.parse import parse_qs, urlparse
import qrcode
import mimetypes
import gzip
import io
import file_stats
from timeit import default_timer as timer
import selectors
import types

# Contraseña hardcodeada para el BONUS de autenticación
PASSWORD_SECRETA = "utdt"

# FUNCIONES AUXILIARES

def imprimir_qr_en_terminal(url):
    """Dada una URL la imprime por terminal como un QR"""
    qr = qrcode.QRCode(
    version=1,
    box_size=2,
    border=1
    )
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)
    pass

def get_wifi_ip():
    """Obtiene la IP local asociada a la interfaz de red (por ejemplo, Wi-Fi)."""
    s = socket(AF_INET, SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip #Devuelve la IP como string

def parsear_multipart(body, boundary):
    """Función auxiliar (ya implementada) para parsear multipart/form-data."""
    try:
        parts = body.split(f'--{boundary}'.encode())
        for part in parts:
            if b'filename=' in part:
                filename_start = part.find(b'filename="') + len(b'filename="')
                filename_end = part.find(b'"', filename_start)
                filename = part[filename_start:filename_end].decode()

                header_end = part.find(b'\r\n\r\n')
                if header_end == -1:
                    header_end = part.find(b'\n\n')
                    content_start = header_end + 2
                else:
                    content_start = header_end + 4

                content_end = part.rfind(b'\r\n')
                if content_end <= content_start:
                    content_end = part.rfind(b'\n')

                file_content = part[content_start:content_end]

                if filename and file_content:
                    return filename, file_content
        return None, None
    except Exception as e:
        print(f"Error al parsear multipart: {e}")
        return None, None

def generar_html_login(error_msg=None):
    """Genera el HTML del formulario de inicio de sesión con mensaje de error opcional."""
    error_display = f'<p class="error">{error_msg}</p>' if error_msg else ''
    return f"""
<html>
  <head>
    <meta charset="utf-8">
    <title>Acceso Restringido</title>
    <style>
      body {{ font-family: sans-serif; max-width: 500px; margin: 50px auto; text-align: center; }}
      form {{ border: 1px solid #ccc; padding: 30px; border-radius: 5px; background: #f9f9f9; }}
      input[type="password"], input[type="submit"] {{ padding: 10px; margin: 5px 0; width: 80%; box-sizing: border-box; border-radius: 3px; border: 1px solid #ddd; }}
      input[type="submit"] {{ background: #007bff; color: white; border: none; cursor: pointer; }}
      .error {{ color: red; font-weight: bold; }}
    </style>
  </head>
  <body>
    <h1>🔒 Acceso Requerido</h1>
    {error_display}
    <form method="POST" action="/">
      <label for="password">Contraseña:</label><br>
      <input type="password" id="password" name="password" required><br><br>
      <input type="submit" value="Ingresar">
    </form>
  </body>
</html>
"""

def generar_html_interfaz(modo):
    """
    Genera el HTML de la interfaz principal.
    CORRECCIÓN: Se revierte a un HTML de descarga más simple.
    """
    if modo == 'download':
        # HTML original/simple para descarga. Contiene el link necesario.
        return """
<html>
  <head>
    <meta charset="utf-8">
    <title>Descargar archivo</title>
    <style>
      body { font-family: sans-serif; max-width: 500px; margin: 50px auto; }
      a { display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }
    </style>
  </head>
  <body>
    <h1>Descargar archivo</h1>
    <p>Haz click en el botón para descargar:</p>
    <a href="/download">Descargar archivo</a>
  </body>
</html>
"""
    
    else:  # upload
        return """
<html>
  <head>
    <meta charset="utf-8">
    <title>Subir archivo</title>
    <style>
      body { font-family: sans-serif; max-width: 500px; margin: 50px auto; }
      form { border: 2px dashed #ccc; padding: 20px; border-radius: 5px; }
      input[type="submit"] { padding: 10px 20px; background: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer; }
      h1 { text-align: center; }
    </style>
  </head>
  <body>
    <h1>📤 Subir archivo</h1>
    <form method="POST" enctype="multipart/form-data">
      <input type="file" name="file" required>
      <input type="submit" value="Subir">
    </form>
  </body>
</html>
"""

def generar_html_aux(filename, file_content):
    """HTML informativo para usar luego de la carga de un archivo, permite volver al HTML original"""
    return f"""
            <html>
                <head>
                    <meta charset="utf-8">
                    <title>Carga Exitosa</title>
                    <style>
                        body {{ font-family: sans-serif; max-width: 500px; margin: 50px auto; text-align: center;}}
                        h1 {{ color: #28a745; }}
                        a {{ display: inline-block; padding: 10px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin-top: 15px;}}
                    </style>
                </head>
                <body>
                    <h1>✅ Archivo Subido con Éxito</h1>
                    <p>Nombre: <strong>{filename}</strong></p>
                    <p>Tamaño: <strong>{len(file_content)} bytes</strong></p>
                    <p><a href="/">Volver a la interfaz principal</a></p>
                </body>
            </html>
            """

def generate_response(status, html=None, from_descarga=False, mime_type=None, archivo_completo=None, archivo=None, zip=False):
    """Dado el status, html y otros parametros de ser necesarios genera la response necesaria"""
    # Manejo de HTML normal (200, 404, 500, 406)
    if not from_descarga:
        if status == 200:
            return (    "HTTP/1.1 200 OK\r\n"
                        "Content-Type: text/html; charset=utf-8\r\n"
                        f"Content-Length: {len(html.encode('utf-8'))}\r\n"
                        "Connection: keep-alive\r\n" # MANTENER CONEXIÓN ABIERTA
                        "\r\n"
                    ).encode() + html.encode("utf-8")
        elif status == 404:
            html_bytes = b"<html><body><h1>Error 404: Ruta no encontrada</h1></body></html>"
            return (    "HTTP/1.1 404 Not Found\r\n"
                        "Content-Type: text/html; charset=utf-8\r\n"
                        f"Content-Length: {len(html_bytes)}\r\n"
                        "Connection: close\r\n"
                        "\r\n"
                    ).encode() + html_bytes
        elif status == 500:
            html_bytes = b"<html><body><h1>Error 500: Error interno del servidor</h1></body></html>"
            return (    "HTTP/1.1 500 Internal Server Error\r\n"
                        "Content-Type: text/html; charset=utf-8\r\n"
                        f"Content-Length: {len(html_bytes)}\r\n"
                        "Connection: close\r\n"
                        "\r\n"
                    ).encode() + html_bytes
        elif status == 406:
            html_bytes = b"<html><body><h1>Error 406: El cliente no acepta gzip</h1></body></html>"
            return (    "HTTP/1.1 406 Not Acceptable\r\n"
                        "Content-Type: text/html; charset=utf-8\r\n"
                        f"Content-Length: {len(html_bytes)}\r\n"
                        "Connection: close\r\n"
                        "\r\n"
                    ).encode() + html_bytes

    # Manejo de Descarga (from_descarga = True)
    else:
        # Aquí se sirve el archivo, la conexión se cierra.
        if status == 200 and zip:
            return (
                        "HTTP/1.1 200 OK\r\n"
                        f"Content-Type: {mime_type}\r\n"
                        f"Content-Length: {len(archivo_completo)}\r\n"
                        f"Content-Disposition: attachment; filename=\"{os.path.basename(archivo)}.gz\"\r\n"
                        "Content-Encoding: gzip\r\n"
                        "Connection: close\r\n" # Cierre de conexión después de servir el archivo
                        "\r\n"
                    ).encode() + archivo_completo
        elif status == 200 and not zip:
            return (
                        "HTTP/1.1 200 OK\r\n"
                        f"Content-Type: {mime_type}\r\n"
                        f"Content-Length: {len(archivo_completo)}\r\n"
                        f"Content-Disposition: attachment; filename=\"{os.path.basename(archivo)}\"\r\n"
                        "Connection: close\r\n" # Cierre de conexión después de servir el archivo
                        "\r\n"
                    ).encode() + archivo_completo
        elif status == 404:
            html_bytes = b"<html><body><h1>Error 404: Archivo no encontrado</h1></body></html>"
            return (    "HTTP/1.1 404 Not Found\r\n"
                        "Content-Type: text/html; charset=utf-8\r\n"
                        f"Content-Length: {len(html_bytes)}\r\n"
                        "Connection: close\r\n"
                        "\r\n"
                    ).encode() + html_bytes

stats = ["", 0, 0, True, 0.0]

timeout_map = {}
auth_state = {}


def service_connection(key, mask, modo, archivo_descarga=None, zip=False):
    sock = key.fileobj
    data = key.data

    # CERRAR CONEXION SI PASARON 300s (solo en modo upload, si no la descarga no funciona)
    if modo and timer() - timeout_map.get(sock, timer()) > 300:
        print("Timeout: cerrando conexión por inactividad")
        try:
            sel.unregister(sock)
        except:
            pass
        sock.close()
        timeout_map.pop(sock, None)
        auth_state.pop(sock, None)
        return

    try:
        if mask & selectors.EVENT_READ:
            recv_data = sock.recv(4096)
            timeout_map[sock] = timer()

            if not recv_data:
                sel.unregister(sock)
                sock.close()
                timeout_map.pop(sock, None)
                auth_state.pop(sock, None)
                return
            data.inb += recv_data
            header_end = data.inb.find(b"\r\n\r\n")
            if header_end == -1:
                return
            headers_raw = data.inb[:header_end]
            headers = headers_raw.decode("utf-8", errors="ignore")
            content_length = 0
            for line in headers.split("\r\n"):
                if "Content-Length:" in line:
                    try:
                        content_length = int(line.split(":")[1].strip())
                        break
                    except:
                        content_length = 0
                        break
            
            expected_total_length = header_end + 4 + content_length
            if len(data.inb) < expected_total_length:
                return
            request_complete = data.inb
            
            start = timer()

            request_line = headers.split("\r\n")[0]
            method = request_line.split(" ")[0]
            path = request_line.split(" ")[1]
            body = request_complete[header_end + 4:]
            
            response = None
            modo_str = "upload" if modo else "download"

            # --- Manejo del GET inicial / Home ---
            if method == "GET" and path == "/":
                if auth_state.get(sock): # Autenticado (aplica a upload y download)
                    html = generar_html_interfaz(modo_str)
                else: # No autenticado
                    html = generar_html_login()
                
                response = generate_response(200, html)
            
            # --- Manejo del POST ---
            elif method == "POST":
                content_type = ""
                for line in headers.split("\r\n"):
                    if "Content-Type:" in line:
                        content_type = line.split(":", 1)[1].strip()
                        break

                # 1. Manejar el POST de LOGIN (application/x-www-form-urlencoded)
                if "application/x-www-form-urlencoded" in content_type:
                    try:
                        form_data = parse_qs(body.decode("utf-8"))
                        password_recibida = form_data.get('password', [''])[0]
                    except Exception:
                        password_recibida = ""

                    if password_recibida == PASSWORD_SECRETA:
                        # Contraseña correcta: Marcar como autenticado y mostrar la interfaz
                        auth_state[sock] = True
                        html = generar_html_interfaz(modo_str)
                        response = generate_response(200, html)
                        # NOTA: La conexión se mantiene abierta (keep-alive) por generate_response.
                    else:
                        # Contraseña incorrecta: Volver a mostrar el formulario con error
                        html = generar_html_login(error_msg="Contraseña incorrecta")
                        response = generate_response(200, html)
                
                # 2. Manejar el POST de CARGA de archivo (multipart/form-data)
                elif "multipart/form-data" in content_type and modo and auth_state.get(sock):
                    # Solo permitir carga si estamos en modo upload Y autenticado
                    boundary = None
                    for line in headers.split("\r\n"):
                        if "Content-Type:" in line and "boundary=" in line:
                            boundary = line.split("boundary=")[1].strip()
                            break
                    html = manejar_carga(body, boundary, directorio_destino="archivos_servidor")
                    response = generate_response(200, html)
                
                else:
                    response = generate_response(404)

            # --- Manejo del GET /download ---
            elif method == "GET" and path == "/download" and not modo and archivo_descarga:
                if auth_state.get(sock):
                    # Autenticado en esta conexión: Servir el archivo
                    response = manejar_descarga(archivo_descarga, request_line, zip, headers)
                    end = timer()
                    file_stats.agregar_archivo(
                        nombre=stats[0],
                        original=stats[1],
                        comprimido=stats[2],
                        esta_comprimido=stats[3],
                        tiempo=end-start
                    )
                else:
                    # No autenticado: Volver a login
                    html = generar_html_login(error_msg="Sesión expirada o acceso no autorizado. Inicie sesión.")
                    response = generate_response(200, html)

            
            # --- Petición no manejada ---
            if response is None:
                response = generate_response(404)
            
            sock.sendall(response)

            # *** CIERRE CONDICIONAL DE CONEXIÓN ***
            # Si se acaba de servir un archivo (GET /download exitoso), cerrar la conexión.
            should_close = False
            if method == "GET" and path == "/download" and not modo and auth_state.get(sock):
                 # Si llegamos aquí y el estado estaba bien, se sirvió el archivo.
                 should_close = True 
            
            if should_close:
                try:
                    sel.unregister(sock)
                except:
                    pass
                sock.close()
                timeout_map.pop(sock, None)
                auth_state.pop(sock, None)
                return

            # Para requests normales (que usan keep-alive) limpiamos el buffer
            try:
                data.inb = b""
            except Exception:
                pass

    except Exception as e:
        print(f"Error en service_connection: {e}")
        try:
            sel.unregister(sock)
        except Exception:
            pass
        try:
            sock.close()
            timeout_map.pop(sock, None)
            auth_state.pop(sock, None)
        except Exception:
            pass


def manejar_descarga(archivo, request_line, zip, headers):
    """
    Genera una respuesta HTTP con el archivo solicitado. 
    """
    try:
        if zip:
            enc_header = None
            for line in headers.split("\r\n"):
                if line.lower().startswith("accept-encoding:"):
                    enc_header = line.split(":", 1)[1].lower()
                    break
            acepta_gzip = enc_header is not None and "gzip" in enc_header
            if not acepta_gzip:
                return generate_response(406)

        mime_type, _ = mimetypes.guess_type(archivo)
        if mime_type is None:
            mime_type = "application/octet-stream"

        with open(archivo, "rb") as f:
            original = f.read()

        if zip:
            buffer = io.BytesIO()
            with gzip.GzipFile(fileobj=buffer, mode="wb") as gz:
                gz.write(original)
            comprimido = buffer.getvalue()
            
            stats[0] = archivo
            stats[1] = len(original)
            stats[2] = len(comprimido)
            stats[3] = True
            
            return generate_response(200, None, True, mime_type, comprimido, archivo, zip=True)
        else:
            
            stats[0] = archivo
            stats[1] = len(original)
            stats[2] = 0
            stats[3] = False
            
            return generate_response(200, None, True, mime_type, original, archivo, zip=False)
            
    except FileNotFoundError:
        return generate_response(404, None, True)
    except Exception as e:
        print(f"Error al manejar la descarga: {e}")
        return generate_response(500)

def manejar_carga(body, boundary, directorio_destino="."):
    """
    Procesa un POST con multipart/form-data, guarda el archivo y devuelve una página de confirmación.
    """
    if not os.path.exists(directorio_destino):
        os.makedirs(directorio_destino)
    if boundary:
        filename, file_content = parsear_multipart(body, boundary.encode('utf-8')) 
    else:
        return generar_html_aux("Error", b"Boundary no encontrado.")
        
    if filename and file_content:
        ruta = os.path.join(directorio_destino, os.path.basename(filename)) 
        try:
            with open(ruta, "wb") as f:
                f.write(file_content)
            print(f"Archivo recibido: {filename} ({len(file_content)} bytes) guardado en {ruta}")
            html_content = generar_html_aux(filename, file_content)
            return html_content
        except Exception as e:
            print(f"Error al guardar el archivo: {e}")
            error_html = "<html><body><h1>Error al guardar el archivo</h1><p><a href='/'>Volver</a></p></body></html>"
            return error_html
    else:
        error_html = "<html><body><h1>Error: No se encontró el archivo o contenido en la solicitud. Asegúrate de haber seleccionado un archivo.</h1><p><a href='/'>Volver</a></p></body></html>"
        return error_html


sel = selectors.DefaultSelector()

def accept_wrapper(sock):
    conn, addr = sock.accept()
    print(f"Accepted connection from {addr}")
    conn.setblocking(False)

    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")

    timeout_map[conn] = timer()
    auth_state[conn] = False 

    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)


def start_server(archivo_descarga=None, modo_upload=False, zip=False):
    """
    Inicia el servidor TCP.
    """

    ip_server = get_wifi_ip()
    server_socket = socket(AF_INET, SOCK_STREAM)
    server_socket.bind((ip_server, 0))
    puerto = server_socket.getsockname()[1]
    server_socket.listen()
    server_socket.setblocking(False)
    sel.register(server_socket, selectors.EVENT_READ, data=None)

    modo_str = "Upload" if modo_upload else "Download"
    archivo_str = f" ({archivo_descarga})" if archivo_descarga else ""
    print(f"Servidor en modo: {modo_str}{archivo_str}")
    
    url = "http://" + ip_server + ":" + str(puerto)
    print(f"URL de acceso: {url}")
    imprimir_qr_en_terminal(url)

    while True:
        try:
            events = sel.select(timeout=None)
            for key, mask in events:
                if key.data is None:
                    accept_wrapper(key.fileobj)
                else:
                    service_connection(key, mask, modo_upload, archivo_descarga, zip)
        except Exception as e:
            print(f"Error principal del servidor: {e}")
            break


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python server_fileTransfer.py upload                    # Servidor para subir archivos")
        print("  python server_fileTransfer.py download archivo.txt      # Servidor para descargar un archivo")
        print("  python server_fileTransfer.py download archivo.txt gzip # Servidor para descargar un archivo con compresión")
        sys.exit(1)

    comando = sys.argv[1].lower()
    
    zip = False

    if len(sys.argv) > 3:
        if sys.argv[3].lower() == "gzip":
            zip = True

    if comando == "upload":
        start_server(archivo_descarga=None, modo_upload=True, zip=zip)

    elif comando == "download" and len(sys.argv) > 2:
        archivo = sys.argv[2]
        ruta_archivo = os.path.join("archivos_servidor", archivo)
        start_server(archivo_descarga=ruta_archivo, modo_upload=False, zip=zip)

    else:
        print("Comando no reconocido o archivo faltante")
        sys.exit(1)