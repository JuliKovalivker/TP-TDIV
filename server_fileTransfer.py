from socket import *
import sys
import os
from urllib.parse import parse_qs, urlparse
import qrcode
import mimetypes
import gzip
import io

#FUNCIONES AUXILIARES

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
        # Se divide el cuerpo por el boundary para luego poder extraer el nombre y contenido del archivo
        parts = body.split(f'--{boundary}'.encode())
        for part in parts:
            if b'filename=' in part:
                # Se extrae el nombre del archivo
                filename_start = part.find(b'filename="') + len(b'filename="')
                filename_end = part.find(b'"', filename_start)
                filename = part[filename_start:filename_end].decode()

                # Se extrae el contenido del archivo que arranca después de los headers
                header_end = part.find(b'\r\n\r\n')
                if header_end == -1:
                    header_end = part.find(b'\n\n')
                    content_start = header_end + 2
                else:
                    content_start = header_end + 4

                # El contenido va hasta el último CRLF antes del boundary
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

def generar_html_interfaz(modo):
    """
    Genera el HTML de la interfaz principal:
    - Si modo == 'download': incluye un enlace o botón para descargar el archivo.
    - Si modo == 'upload': incluye un formulario para subir un archivo.
    """
    if modo == 'download':
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
    </style>
  </head>
  <body>
    <h1>Subir archivo</h1>
    <form method="POST" enctype="multipart/form-data">
      <input type="file" name="file" required>
      <input type="submit" value="Subir">
    </form>
  </body>
</html>
"""

#CODIGO A COMPLETAR
#Incluimos tambien otras funciones auxiliares implemnetadas por nosotras

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
                    <p><a href="/">Volver a subir otro archivo</a></p>
                </body>
            </html>
            """

def generate_response(status, html=None, from_descarga=False, mime_type=None, comprimido=None, archivo=None):
    """Dado el status, html y otros parametros de ser necesarios genera la response necesaria"""
    if status == 200 and not from_descarga:
        return (    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: text/html; charset=utf-8\r\n"
                    f"Content-Length: {len(html)}\r\n"
                    "Connection: close\r\n"
                    "\r\n"
                ).encode() + html
    elif status == 404:
        return (    "HTTP/1.1 404 Not Found\r\n"
                    "Content-Type: text/plain\r\n"
                    "Connection: close\r\n"
                    "\r\n"
                    "Ruta no encontrada"
                ).encode()
    elif status == 200 and from_descarga:
        return (
                    "HTTP/1.1 200 OK\r\n"
                    f"Content-Type: {mime_type}\r\n"
                    f"Content-Encoding: gzip\r\n"
                    f"Content-Length: {len(comprimido)}\r\n"
                    f"Content-Disposition: attachment; filename=\"{os.path.basename(archivo)}.gz\"\r\n"
                    "Connection: close\r\n"
                    "\r\n"
                )

def service_connection(key, mask, modo, archivo_descarga=None):
    sock = key.fileobj
    data = key.data
    try:
        if mask & selectors.EVENT_READ:
            # Si hay datos recibidos los voy guardando
            recv_data = sock.recv(4096)
            if not recv_data:
                sel.unregister(sock)
                sock.close()
                return
            data.inb += recv_data
            header_end = data.inb.find(b"\r\n\r\n")
            if header_end == -1:
                return
            headers_raw = data.inb[:header_end]
            headers = headers_raw.decode("utf-8", errors="ignore")  # Decodifico el header
            content_length = 0
            for line in headers.split("\r\n"):
                if "Content-Length:" in line:
                    content_length = int(line.split(":")[1].strip())
                    break
            expected_total_length = header_end + 4 + content_length
            if len(data.inb) < expected_total_length:
                return
            request_complete = data.inb
            
            # Separar request_line, headers y body
            request_line = headers.split("\r\n")[0]     # Primera linea del header tiene la request
            method = request_line.split(" ")[0]         # Primer dato del header => metodo
            path = request_line.split(" ")[1]           # Segundo dato del header => path
            body = request_complete[header_end + 4:]    # Segunda linea del header (luego de los dos enters) => body (no debe ser decodificado)

            response = None
            if method == "GET":
                if path == "/":
                    if modo:
                        html = generar_html_interfaz("upload").encode("utf-8")
                    else:
                        html = generar_html_interfaz("download").encode("utf-8")
                    response = generate_response(200, html)
                elif path == "/download" and not modo and archivo_descarga:
                    response = manejar_descarga(archivo_descarga, request_line)
            elif method == "POST" and modo:
                boundary = None
                for line in headers.split("\r\n"):
                    if "Content-Type:" in line and "multipart/form-data" in line:
                        boundary = line.split("boundary=")[1].strip() # Limpiar espacio o caracteres no deseados del boundary
                        break
                html = manejar_carga(body, boundary, directorio_destino="archivos_servidor") # Ya puedo cargar el archivo
                response = generate_response(200, html)
            if response is None:
                response = generate_response(404)
            sock.sendall(response)
            sel.unregister(sock)
            sock.close()
    except:
        print("Se cerró la conexión.")
        try:
            sel.unregister(sock)
        except:
            pass
        sock.close()

def manejar_descarga(archivo, request_line):
    """
    Genera una respuesta HTTP con el archivo solicitado. 
    Si el archivo no existe debe devolver un error.
    Debe incluir los headers: Content-Type, Content-Length y Content-Disposition.
    """
    # COMPLETAR

    mime_type, _ = mimetypes.guess_type(archivo)
    if mime_type is None:
        mime_type = "application/octet-stream"

    with open(archivo, "rb") as f:
        original = f.read()

    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb") as gz:
        gz.write(original)
    comprimido = buffer.getvalue()

    headers = generate_response(200, None, True, mime_type, comprimido, archivo)

    #si sale mal error 404 not found

    # return json.dumps(data)
    return headers.encode("utf-8") + comprimido

def manejar_carga(body, boundary, directorio_destino="."):
    """
    Procesa un POST con multipart/form-data, guarda el archivo y devuelve una página de confirmación.
    """
    if not os.path.exists(directorio_destino):
        os.makedirs(directorio_destino)
    if boundary:
        filename, file_content = parsear_multipart(body, boundary.encode('utf-8')) 
    else:
        return b"<html><body><h1>Error: Boundary no encontrado.</h1></body></html>" 
    if filename and file_content:
        ruta = os.path.join(directorio_destino, os.path.basename(filename)) 
        try:
            with open(ruta, "wb") as f:  # Abrir el archivo en modo binario de escritura ('wb') y escribir el contenido
                f.write(file_content)
            print(f"Archivo recibido: {filename} ({len(file_content)} bytes) guardado en {ruta}")
            html_content = generar_html_aux(filename, file_content)
            return html_content.encode("utf-8")
        except: ################ PONER ERROR 500 INTERNAL SERVER ERROR
            print("Error al guardar el archivo")
            error_html = "<html><body><h1>Error al guardar el archivo</h1><p><a href='/'>Volver</a></p></body></html>"
            return error_html.encode("utf-8")
    else:  ################ PONER ERROR 500 INTERNAL SERVER ERROR
        error_html = "<html><body><h1>Error: No se encontró el archivo o contenido en la solicitud. Asegúrate de haber seleccionado un archivo.</h1><p><a href='/'>Volver</a></p></body></html>"
        return error_html.encode("utf-8")

import selectors
import types
sel = selectors.DefaultSelector()

def accept_wrapper(sock):
    conn, addr = sock.accept()
    print(f"Accepted connection from {addr}") # Borrar
    conn.setblocking(False)
    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)

def start_server(archivo_descarga=None, modo_upload=False):
    """
    Inicia el servidor TCP.
    - Si se especifica archivo_descarga, se inicia en modo 'download'.
    - Si modo_upload=True, se inicia en modo 'upload'.
    """

    # 1. Obtener IP local y poner al servidor a escuchar en un puerto aleatorio

    ip_server = get_wifi_ip()
    server_socket = socket(AF_INET, SOCK_STREAM)
    server_socket.bind((ip_server, 0))       # El SO elige un puerto libre
    puerto = server_socket.getsockname()[1]  # Obtengo el puerto asignado
    server_socket.listen()
    server_socket.setblocking(False)
    sel.register(server_socket, selectors.EVENT_READ, data=None)

    # 2. Mostrar información del servidor y el código QR
    # COMPLETAR: imprimir URL y modo de operación (download/upload)

    #mostrar informacion?
    url = "http://" + ip_server + ":" + str(puerto)
    print(url)
    imprimir_qr_en_terminal(url)

    # 3. Esperar conexiones y atender un cliente
    
    # COMPLETAR:
    # - aceptar la conexión (accept)
    # - recibir los datos (recv)
    # - decodificar la solicitud HTTP
    # - determinar método (GET/POST) y ruta (/ o /download)
    # - generar la respuesta correspondiente (HTML o archivo)
    # - enviar la respuesta al cliente
    # - cerrar la conexión

    while True:
        events = sel.select(timeout=None)
        for key, mask in events:
            if key.data is None:
                accept_wrapper(key.fileobj) #Acepto la conexion
            else:
                service_connection(key, mask, modo_upload, archivo_descarga) #Recibo los datos, genero respuesta, envio respuesta, cierro conexion

    #pass  # Eliminar cuando esté implementado

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python tp.py upload                    # Servidor para subir archivos")
        print("  python tp.py download archivo.txt      # Servidor para descargar un archivo")
        sys.exit(1)

    comando = sys.argv[1].lower()

    if comando == "upload":
        start_server(archivo_descarga=None, modo_upload=True)

    elif comando == "download" and len(sys.argv) > 2:
        archivo = sys.argv[2]
        ruta_archivo = os.path.join("archivos_servidor", archivo)
        start_server(archivo_descarga=ruta_archivo, modo_upload=False)

    else:
        print("Comando no reconocido o archivo faltante")
        sys.exit(1)