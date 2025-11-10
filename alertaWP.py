import requests
import time
from datetime import datetime
from flask import Flask
import os
import threading

# === CONFIGURACIÓN ===
MONEDA = "LTCUSDT"
INTERVALO_MINUTOS = 5
DIFERENCIA_COMPRA = 5
DIFERENCIA_VENTA = 5
COMISION = 0.001
NUMERO = "5492914228541"
API_KEY = "7577157"

# === VARIABLES GLOBALES ===
en_posicion = False
precio_entrada = None
PRECIO_COMPRA_TARGET = None
PRECIO_VENTA_TARGET = None
capital_usdt = 52.0
modo = os.getenv("MODO_BOT", "USDT")  # USDT o LTC

# === FUNCIONES ===
def obtener_precio():
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={MONEDA}"
    return float(requests.get(url).json()["price"])

def obtener_estadisticas_24h():
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={MONEDA}"
    data = requests.get(url).json()
    return {
        'high': float(data['highPrice']),
        'low': float(data['lowPrice']),
        'change_percent': float(data['priceChangePercent'])
    }

def enviar_whatsapp(mensaje):
    try:
        mensaje_encoded = mensaje.replace(" ", "+").replace("\n", "%0A")
        url = f"https://api.callmebot.com/whatsapp.php?phone={NUMERO}&text={mensaje_encoded}&apikey={API_KEY}"
        r = requests.get(url)
        print(f"✅ WhatsApp enviado: {mensaje}" if r.status_code == 200 else f"⚠️ Error {r.status_code}")
    except Exception as e:
        print(f"❌ Error WhatsApp: {e}")

def calcular_ganancia_potencial(precio_compra, precio_venta, capital):
    ltc_comprado = (capital * (1 - COMISION)) / precio_compra
    usdt_vendido = ltc_comprado * precio_venta * (1 - COMISION)
    ganancia = usdt_vendido - capital
    return ganancia, (ganancia / capital) * 100

def analizar_oportunidad(precio_actual, stats):
    global en_posicion, precio_entrada, PRECIO_COMPRA_TARGET, PRECIO_VENTA_TARGET

    ahora = datetime.now().strftime("%H:%M:%S")

    if not en_posicion:  # Buscamos COMPRAR
        if PRECIO_COMPRA_TARGET is None:
            PRECIO_COMPRA_TARGET = precio_actual - DIFERENCIA_COMPRA
            print(f"🎯 Target COMPRA: ${PRECIO_COMPRA_TARGET:.2f}")

        if precio_actual <= PRECIO_COMPRA_TARGET:
            ganancia_potencial, porcentaje = calcular_ganancia_potencial(
                precio_actual, precio_actual + DIFERENCIA_VENTA, capital_usdt
            )
            mensaje = (f"🟢 COMPRA [{ahora}]\nPrecio: ${precio_actual:.2f}\n"
                       f"Ganancia pot.: ${ganancia_potencial:.2f} ({porcentaje:.1f}%)")
            enviar_whatsapp(mensaje)
            en_posicion = True
            precio_entrada = precio_actual
            PRECIO_VENTA_TARGET = precio_actual + DIFERENCIA_VENTA
            PRECIO_COMPRA_TARGET = None

    else:  # Buscamos VENDER
        if PRECIO_VENTA_TARGET is None:
            PRECIO_VENTA_TARGET = precio_entrada + DIFERENCIA_VENTA
            print(f"🎯 Target VENTA: ${PRECIO_VENTA_TARGET:.2f}")

        if precio_actual >= PRECIO_VENTA_TARGET:
            ganancia, porcentaje = calcular_ganancia_potencial(precio_entrada, precio_actual, capital_usdt)
            mensaje = (f"🔴 VENTA [{ahora}]\nPrecio: ${precio_actual:.2f}\n"
                       f"Ganancia: ${ganancia:.2f} ({porcentaje:.1f}%)")
            enviar_whatsapp(mensaje)
            en_posicion = False
            precio_entrada = None
            PRECIO_COMPRA_TARGET = precio_actual - DIFERENCIA_COMPRA
            PRECIO_VENTA_TARGET = None


def iniciar_bot():
    print("🚀 Bot iniciado en modo:", modo)
    global en_posicion, precio_entrada
    if modo.upper() == "LTC":
        en_posicion = True
        precio_entrada = float(os.getenv("PRECIO_ENTRADA", "160"))  # opcional
        print(f"🔹 Modo con LTC (entrada ${precio_entrada})")
    else:
        print("🔹 Modo con USDT")

    enviar_whatsapp(f"🤖 Bot LTC activo. Estado: {'CON LTC' if en_posicion else 'CON USDT'}")

    while True:
        try:
            precio_actual = obtener_precio()
            stats = obtener_estadisticas_24h()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Precio: ${precio_actual:.2f} ({stats['change_percent']}%)")
            analizar_oportunidad(precio_actual, stats)
            time.sleep(INTERVALO_MINUTOS * 60)
        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(60)

# === FLASK APP PARA RENDER ===
app = Flask(__name__)

@app.route('/')
def home():
    return f"Bot LTC activo ✅ - Modo: {modo}"

if __name__ == '__main__':
    threading.Thread(target=iniciar_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=10000)
