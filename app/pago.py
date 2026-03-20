from flask import Flask, render_template, request

import os, uuid, datetime

app= Flask(__name__)


#Datos bancarios de la persona que va a recibir el dinero

DATOS_PAGO ={

    #Nequi

    "nequi":{
        "numero":"3215272622",
        "titular":"Mamá de Yessica",
    },

    #Transferencia bancaria

    "banco":{
        "banco":"#",
        "numero":"#",
        "tipo":"#",
        "titular":"#",
        "cedula":"#"  
    },

    #Paypal 

    "paypal":{
        "correo":"#",
        "titular":"#",

    },

    #PSE son los datos con lo que suelen trabajar WOmpi, PayU o ePayco ya que no se paga directamente con PSE realmente

    "pse":{
        "ide_tienda":"#", #Es como el identificador de la tienda que va a recibir el dinero
        "key":"#", #Es uuna clave secreta no debe verse en otro lugar es lo que permite la comunicación entre ambas
        "public_key":"#", #Es una llave que si se puede usar de forma pública sirve para conextar pago desde la web

    }

}

PLANES={

    "alertas en alta prioridad":{
        "nombre del plan":"#",
        "descripción del plan":"#",
        "costo del plan":"20.000 COP"
    },

    "#":{
        "nombre del plan":"#",
        "descripción":"#",
    },

    
    "Combo":{
        "nombre del plan":"Plan todo en 1 + usuario verificado",
        "descripción":"Este plan ofece las alertas prioritarias, verificación del usuario y como extra la verificación para el usuario",
        "Costo del plan":"30.000 COP"
    }
}