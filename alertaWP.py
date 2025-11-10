import requests
import time
from datetime import datetime

# === CONFIGURACIÓN ===
MONEDA = "LTCUSDT"
INTERVALO_MINUTOS = 5

# Estrategia de trading
PRECIO_COMPRA_TARGET = None  # Se define automáticamente
PRECIO_VENTA_TARGET = None   # Se define automáticamente
DIFERENCIA_COMPRA = 5        # Cuánto debe bajar para comprar
DIFERENCIA_VENTA = 5         # Cuánto debe subir para vender
COMISION = 0.001             # 0.1% comisión Binance

# CallMeBot config
NUMERO = "5492914228541"
API_KEY = "7577157"

# Estado del bot
en_posicion = False  # ¿Tenés LTC o USDT?
precio_entrada = None
capital_usdt = 52.0  # Actualizá esto según tu saldo
cantidad_ltc = 0


def obtener_precio():
    """Consulta precio actual en Binance"""
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={MONEDA}"
    data = requests.get(url).json()
    return float(data["price"])


def obtener_estadisticas_24h():
    """Obtiene precio alto/bajo de las últimas 24h para contexto"""
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={MONEDA}"
    data = requests.get(url).json()
    return {
        'high': float(data['highPrice']),
        'low': float(data['lowPrice']),
        'change_percent': float(data['priceChangePercent'])
    }


def enviar_whatsapp(mensaje):
    """Envía mensaje por WhatsApp"""
    try:
        mensaje_encoded = mensaje.replace(" ", "+").replace("\n", "%0A")
        url = f"https://api.callmebot.com/whatsapp.php?phone={NUMERO}&text={mensaje_encoded}&apikey={API_KEY}"
        r = requests.get(url)
        if r.status_code == 200:
            print(f"✅ WhatsApp enviado: {mensaje}")
        else:
            print(f"⚠️ Error {r.status_code}")
    except Exception as e:
        print(f"❌ Error WhatsApp: {e}")


def calcular_ganancia_potencial(precio_compra, precio_venta, capital):
    """Calcula ganancia neta considerando comisiones"""
    ltc_comprado = (capital * (1 - COMISION)) / precio_compra
    usdt_vendido = ltc_comprado * precio_venta * (1 - COMISION)
    ganancia = usdt_vendido - capital
    return ganancia, (ganancia / capital) * 100


def analizar_oportunidad(precio_actual, stats):
    """Analiza si hay oportunidad de compra o venta"""
    global en_posicion, precio_entrada, PRECIO_COMPRA_TARGET, PRECIO_VENTA_TARGET
    
    ahora = datetime.now().strftime("%H:%M:%S")
    
    # Si NO tenemos posición (tenemos USDT) -> buscamos COMPRAR
    if not en_posicion:
        if PRECIO_COMPRA_TARGET is None:
            PRECIO_COMPRA_TARGET = precio_actual - DIFERENCIA_COMPRA
            print(f"🎯 Target de COMPRA: ${PRECIO_COMPRA_TARGET:.2f}")
        
        # ¿Llegamos al precio de compra?
        if precio_actual <= PRECIO_COMPRA_TARGET:
            ganancia_potencial, porcentaje = calcular_ganancia_potencial(
                precio_actual, 
                precio_actual + DIFERENCIA_VENTA,
                capital_usdt
            )
            
            mensaje = (f"🟢 SEÑAL DE COMPRA [{ahora}]\n"
                      f"Precio actual: ${precio_actual:.2f}\n"
                      f"Bajo ${DIFERENCIA_COMPRA} desde referencia\n"
                      f"24h: Alto ${stats['high']:.2f} | Bajo ${stats['low']:.2f}\n"
                      f"Ganancia potencial: ${ganancia_potencial:.2f} ({porcentaje:.1f}%)")
            enviar_whatsapp(mensaje)
            
            # Actualizamos estado (simulado)
            en_posicion = True
            precio_entrada = precio_actual
            PRECIO_VENTA_TARGET = precio_actual + DIFERENCIA_VENTA
            PRECIO_COMPRA_TARGET = None
            print(f"✅ Posición ABIERTA en ${precio_actual:.2f}")
            print(f"🎯 Nuevo target de VENTA: ${PRECIO_VENTA_TARGET:.2f}")
    
    # Si TENEMOS posición (tenemos LTC) -> buscamos VENDER
    else:
        if PRECIO_VENTA_TARGET is None:
            PRECIO_VENTA_TARGET = precio_entrada + DIFERENCIA_VENTA
            print(f"🎯 Target de VENTA: ${PRECIO_VENTA_TARGET:.2f}")
        
        # ¿Llegamos al precio de venta?
        if precio_actual >= PRECIO_VENTA_TARGET:
            ganancia, porcentaje = calcular_ganancia_potencial(
                precio_entrada,
                precio_actual,
                capital_usdt
            )
            
            mensaje = (f"🔴 SEÑAL DE VENTA [{ahora}]\n"
                      f"Precio actual: ${precio_actual:.2f}\n"
                      f"Subió ${DIFERENCIA_VENTA} desde entrada (${precio_entrada:.2f})\n"
                      f"Ganancia: ${ganancia:.2f} ({porcentaje:.1f}%)\n"
                      f"24h: Alto ${stats['high']:.2f} | Bajo ${stats['low']:.2f}")
            enviar_whatsapp(mensaje)
            
            # Actualizamos estado
            en_posicion = False
            precio_entrada = None
            PRECIO_COMPRA_TARGET = precio_actual - DIFERENCIA_COMPRA
            PRECIO_VENTA_TARGET = None
            print(f"✅ Posición CERRADA en ${precio_actual:.2f} - Ganancia: ${ganancia:.2f}")
            print(f"🎯 Nuevo target de COMPRA: ${PRECIO_COMPRA_TARGET:.2f}")


# === CONFIGURACIÓN INICIAL ===
print("🚀 Iniciando bot de trading LTC/USDT")
print(f"📊 Estrategia: Comprar cuando baje ${DIFERENCIA_COMPRA}, vender cuando suba ${DIFERENCIA_VENTA}")

# Preguntá al usuario el estado inicial
print("\n¿En qué estado estás actualmente?")
print("1. Tengo USDT (busco comprar LTC)")
print("2. Tengo LTC (busco vender por USDT)")
estado = input("Elegí 1 o 2: ").strip()

if estado == "2":
    en_posicion = True
    precio_entrada = float(input("¿A qué precio compraste el LTC?: "))
    print(f"✅ Configurado: Tenés LTC comprado a ${precio_entrada:.2f}")
else:
    print(f"✅ Configurado: Tenés ${capital_usdt} USDT esperando para comprar")

enviar_whatsapp(f"🤖 Bot LTC iniciado. Estado: {'CON LTC' if en_posicion else 'CON USDT'}")

# === LOOP PRINCIPAL ===
while True:
    try:
        precio_actual = obtener_precio()
        stats = obtener_estadisticas_24h()
        
        estado_emoji = "🟢" if en_posicion else "⚪"
        print(f"\n{estado_emoji} [{datetime.now().strftime('%H:%M:%S')}] Precio: ${precio_actual:.2f} | "
              f"24h: {stats['change_percent']:+.1f}%")
        
        analizar_oportunidad(precio_actual, stats)
        
        time.sleep(INTERVALO_MINUTOS * 60)
        
    except KeyboardInterrupt:
        print("\n👋 Bot detenido por el usuario")
        break
    except Exception as e:
        print(f"⚠️ Error: {e}")
        time.sleep(60)