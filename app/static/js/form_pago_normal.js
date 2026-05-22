// 1. Selección de elementos
const formRegistro = document.getElementById('formulario');
const paso1 = document.getElementById('seccion-paso1');
const paso2 = document.getElementById('seccion-paso2');
const btnAtras = document.getElementById('atras');
const mainContainer = document.querySelector('.container');

// 2. Función para pasar al Paso 2
if (formRegistro) {
    formRegistro.addEventListener('submit', function(e) {
        e.preventDefault(); 

        // 1. CAPTURAMOS TODO EL FORMULARIO
        // Sacamos los valores de los inputs del Paso 1
        
        const email = document.getElementById('f-email').value;
        const nombre = document.getElementById('f-nombre').value;
        const apellidos = document.getElementById('f-apellidos').value;
        const pais = document.getElementById('f-pais').value;
        const paisTexto = document.getElementById('f-pais').options[document.getElementById('f-pais').selectedIndex].text;
        const direccion = document.getElementById('f-dir').value;
        const ciudad = document.getElementById('f-ciudad').value;
        const cp = document.getElementById('f-cp').value;

        // 2. LOS PASAMOS AL RESUMEN DEL PASO 2
        // Buscamos los SPAN que creamos en el HTML y les ponemos el texto
        document.getElementById('r-email').innerText = email;
        document.getElementById('r-nombre').innerText = nombre;
        document.getElementById('r-apellidos').innerText = apellidos;
        document.getElementById('r-pais').innerText = paisTexto;
        document.getElementById('r-dir').innerText = direccion;
        document.getElementById('r-cp').innerText = cp;
        document.getElementById('r-ciudad').innerText = ciudad;
        

        // 3. EFECTO VISUAL
        paso1.style.display = 'none';
        paso2.style.display = 'block';
        mainContainer.style.maxWidth = '900px';

        window.scrollTo(0, 0); 
    });
}

// 3. Función para volver atrás a editar
if (btnAtras) {
    btnAtras.addEventListener('click', function(e) {
        e.preventDefault();
        paso2.style.display = 'none';
        paso1.style.display = 'block';
        
        // Volvemos el contenedor al ancho original (flaquito)
        mainContainer.style.maxWidth = '600px';
    });
}

function simularPago(tipo) {
    const selectPais = document.getElementById('f-pais');

    let datos = {
        email: document.getElementById('f-email').value,
        nombre: document.getElementById('f-nombre').value,
        apellidos: document.getElementById('f-apellidos').value,
        pais_id: selectPais.value,
        direccion: document.getElementById('f-dir').value,
        ciudad: document.getElementById('f-ciudad').value,
        cp: document.getElementById('f-cp').value,
        metodo_pago: tipo,
        plan_id: document.getElementById('plan_id').value,
    }; // Agregamos el tipo de pago al objeto de datos

    if (tipo === 'nequi') {
        const telefono = document.getElementById("pago-nequi").value;
        if (!telefono) {
            alert("Por favor, ingresa tu número de celular para Nequi.");
            return;
        }
        datos.telefono = telefono; //Agregamos el número de teléfono al objeto de datos
        datos.metodo_pago = 1; //Asignamos un número para identificar el método de pago en el backend
    }

    if (tipo=='tarjeta') {
        const tarjeta = document.getElementById("input-tarjeta").value;
        if (!tarjeta) {
            alert("Por favor, ingresa tu número de tarjeta.");
            return;
        }
        datos.tarjeta = tarjeta; //Agregamos el número de tarjeta al objeto de datos
        datos.metodo_pago = 4; //Asignamos un número para identificar el método de pago en el backend
    }

    if (tipo=='paypal') {
        const emailPaypal = document.querySelector("#dinamico-pago input[type='email']").value;
        if (!emailPaypal) {
            alert("Por favor, ingresa tu correo electrónico de PayPal.");
            return;
        }
        datos.emailPaypal = emailPaypal; //Agregamos el correo de PayPal al objeto de datos
        datos.metodo_pago = 3; //Asignamos un número para identificar el método de pago en el backend
    }

    if (tipo=='bancolombia') {
        const usuarioBanco = document.querySelector("#dinamico-pago input[type='text']").value;
        if (!usuarioBanco) {
            alert("Por favor, ingresa tu usuario o documento para Bancolombia.");
            return;
        }
        datos.usuarioBanco = usuarioBanco; //Agregamos el usuario o documento al objeto de datos
        datos.metodo_pago = 2; //Asignamos un número para identificar el método de pago en el backend
    }

    fetch('/simular_pago', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(datos)
    })
    .then(async response => {
    const text = await response.text();

        try {
            return JSON.parse(text);
        } catch {
            console.error("Respuesta no es JSON:", text);
            throw new Error("El servidor devolvió HTML (error 500)");
        }
    })
    .then(data => {
        console.log(data);

        if (data.status === "aprobado") {
            mostrarMensajeExito();
        } else {
            mostrarMensajeError();
        }
    })
    .catch(error => console.error(error));
}

// 4. Función para cambiar entre Tarjeta, Nequi y Bancolombia
function cambiarFormulario(tipo) {
    const contenedor = document.getElementById('dinamico-pago');
    const tituloCard = document.querySelector('#card-preguntas h2');

    if (tipo === 'nequi') {
        tituloCard.innerText = "2. Pagar Número";
        contenedor.innerHTML = `
            <label>Número de celular</label>
            <input type="text" placeholder="xxx xxx xxxx" id="pago-nequi">
            <p style="font-size:12px; color:gray; margin-top:5px;">Recibirás una notificación en tu celular.</p>
            <button type="button" class="btn-comprar" onclick="simularPago('nequi')">Pagar con Nequi</button>
        `;
    } else if (tipo === 'tarjeta') {
        tituloCard.innerText = "2. Información de Tarjeta";
        contenedor.innerHTML = `
            <label>Número de tarjeta</label>
            <input type="text" id="input-tarjeta" placeholder="0000 0000 0000 0000">
            <div class="row" style="display:flex; gap:10px;">
                <div style="flex:1">
                    <label>Expiración</label>
                    <input type="text" placeholder="MM/AA">
                </div>
                <div style="flex:1">
                    <label>CVV</label>
                    <input type="text" placeholder="123">
                </div>
            </div>
            <button type="button" class="btn-comprar" onclick="simularPago('tarjeta')">Comprar ahora</button>
        `;
        // Reactivamos la máscara de espacios para la tarjeta
        aplicarMascaraTarjeta();
    } else if (tipo === 'bancolombia') {
        tituloCard.innerText = "2. Transferencia Bancolombia";
        contenedor.innerHTML = `
            <label>Usuario o Documento</label>
            <input type="text" placeholder="Ingresa tu usuario">
            <button type="button" class="btn-comprar" onclick="simularPago('bancolombia')">Ir a Bancolombia</button>
        `;
    }
        else if (tipo === 'paypal') {
        tituloCard.innerText = "2. Pagar con PayPal";
        contenedor.innerHTML = `
            <label>Correo electrónico</label>
            <input type="email" placeholder="usuario@paypal.com">
            <label>Correo de PayPal</label>
            <label>Contraseña</label>
            <input type="password" placeholder="********">
            <button type="button" class="btn-comprar" onclick="simularPago('paypal')">Pagar con PayPal</button>
            
        `;
    }
}


// 5. Truco para los espacios automáticos en la tarjeta
function aplicarMascaraTarjeta() {
    const inputTarjeta = document.getElementById('input-tarjeta');
    if (inputTarjeta) {
        inputTarjeta.addEventListener('input', function (e) {
            let valor = e.target.value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
            let valorAcortado = valor.substring(0, 16);
            let grupos = valorAcortado.match(/.{1,4}/g);
            e.target.value = grupos ? grupos.join(' ') : valorAcortado;
        });
    }
}

// Lo ejecutamos la primera vez por si el default es tarjeta
document.addEventListener('DOMContentLoaded', aplicarMascaraTarjeta);


function mostrarMensajeExito() {
    // Creamos un div con JS
    const cartel = document.createElement('div');
    
    // Le damos estilo directamente para no enredarnos con el CSS
    cartel.style.position = 'fixed';
    cartel.style.top = '50%';
    cartel.style.left = '50%';
    cartel.style.transform = 'translate(-50%, -50%)';
    cartel.style.backgroundColor = '#112250'; // Tu color Royal
    cartel.style.color = 'white';
    cartel.style.padding = '30px';
    cartel.style.borderRadius = '12px';
    cartel.style.border = '2px solid #E0C58F'; // Tu color Gold
    cartel.style.boxShadow = '0 0 20px rgba(0,0,0,0.5)';
    cartel.style.zIndex = '1000';
    cartel.style.textAlign = 'center';
    
    // Creamos el contenido del cartel
    const titulo = document.createElement('h3');
    titulo.style.marginTop = '0';
    titulo.textContent = '¡Éxito! 🎉';
    
    const parrafo = document.createElement('p');
    parrafo.textContent = 'Pago realizado correctamente recibiras tu factura por correo electrónico.';
    
    const boton = document.createElement('button');
    boton.style.background = '#E0C58F';
    boton.style.color = '#112250';
    boton.style.marginTop = '10px';
    boton.style.padding = '10px 20px';
    boton.style.width = 'auto';
    boton.textContent = 'Aceptar';
    
    // Añadimos el event listener al botón
    boton.addEventListener('click', function() {
        cartel.remove();
        window.location.href = "/menu"; // Redirige al menú después de cerrar el mensaje
    });
    
    // Añadimos los elementos al cartel
    cartel.appendChild(titulo);
    cartel.appendChild(parrafo);
    cartel.appendChild(boton);
    
    document.body.appendChild(cartel);
}

function mostrarMensajeError() {
    const cartel = document.createElement('div');

    cartel.style.position = 'fixed';
    cartel.style.top = '50%';
    cartel.style.left = '50%';
    cartel.style.transform = 'translate(-50%, -50%)';
    cartel.style.backgroundColor = '#112250';
    cartel.style.color = 'white';
    cartel.style.padding = '30px';
    cartel.style.borderRadius = '12px';
    cartel.style.border = '2px solid #E0C58F';
    cartel.style.boxShadow = '0 0 20px rgba(0,0,0,0.5)';
    cartel.style.zIndex = '1000';
    cartel.style.textAlign = 'center';
    
    // Creamos el contenido del cartel
    const titulo = document.createElement('h3');
    titulo.style.marginTop = '0';
    titulo.textContent = '¡Error! ❌';
    
    const parrafo = document.createElement('p');
    parrafo.textContent = 'Hubo un problema al guardar tus respuestas. Por favor, inténtalo de nuevo.';
    
    const boton = document.createElement('button');
    boton.style.background = '#E0C58F';
    boton.style.color = '#112250';
    boton.style.marginTop = '10px';
    boton.style.padding = '10px 20px';
    boton.style.width = 'auto';
    boton.textContent = 'Aceptar';
    
    // Añadimos el event listener al botón
    boton.addEventListener('click', function() {
        cartel.remove();
    });
    
    // Añadimos los elementos al cartel
    cartel.appendChild(titulo);
    cartel.appendChild(parrafo);
    cartel.appendChild(boton);
    
    document.body.appendChild(cartel);
}



