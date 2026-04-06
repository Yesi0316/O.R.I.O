import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

def enviar_factura(email, nombre, apellidos, direccion, cp, ciudad, pais, metodo, plan, precio):
    # Configuración del servidor SMTP

    emisor= "yesickrivera@gmail.com"
    clave= "elnc gzzt rsdx hedl"
    servidor = "smtp.gmail.com"
    port= 587

    mensaje = MIMEMultipart()
    mensaje['From'] = emisor
    mensaje['To'] = email
    mensaje['Subject'] = 'Factura de Compra - O.R.I.O'

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cuerpo = f"""
    <html>
    <body>
        <h2>Factura de Compra</h2>
        <p><strong>Fecha:</strong> {fecha}</p>
        <p><strong>Nombre:</strong> {nombre} {apellidos}</p>
        <p><strong>Dirección:</strong> {direccion}, {ciudad}, {cp}, {pais}</p>
        <p><strong>Método de Pago:</strong> {metodo}</p>
        <p><strong>Plan Adquirido:</strong> {plan}</p>
        <p><strong>Precio Total:</strong> ${precio:.2f}</p>
        <br>
        <p>Gracias por su compra en O.R.I.O. ¡Disfrute de su plan!</p>
    </body>
    </html>
    """
    mensaje.attach(MIMEText(cuerpo, 'html'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as servidor: #conectar al servidor de correo de Gmail
            servidor.starttls() #iniciar conexión segura
            servidor.login(emisor, clave) #autenticar con el correo y la contraseña
            servidor.send_message(mensaje) #enviar el mensaje
            print(f"Factura enviada a {email}")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")