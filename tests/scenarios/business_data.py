"""
business_data.py — Definición completa de los 5 negocios de testing.

Cada negocio tiene:
- Perfil del tenant
- Columnas personalizadas para Clientes
- 10+ clientes con datos realistas del negocio
- Stock de productos/insumos
- Movimientos financieros iniciales
- Conversaciones de stress test
"""

# ══════════════════════════════════════════════════════════════════════════════
# NEGOCIO 1 — Valentina Greco, Masajista a domicilio
# ══════════════════════════════════════════════════════════════════════════════

MASAJISTA = {
    "perfil": {
        "nombre_negocio": "Valentina Masajes",
        "email_admin": "valentina.masajes.test@pokeoffice.ar",
        "nombre_jefe": "Valentina",
        "tipo_negocio": "Servicios de masajes a domicilio",
        "moneda": "ARS",
        "sector": "Salud y bienestar",
        "descripcion": "Masajista profesional que brinda servicios a domicilio en CABA y GBA Norte.",
    },
    "columnas_clientes": ["Tipo de masaje", "Lesiones / Contraindicaciones", "Frecuencia de visitas"],
    "clientes": [
        {"nombre": "María",    "apellido": "Fernández", "telefono": "1155443322", "email": "mfernandez@gmail.com",
         "campos": {"Tipo de masaje": "Deportivo", "Lesiones / Contraindicaciones": "Rodilla derecha (lesión menisco)", "Frecuencia de visitas": "Semanal"}},
        {"nombre": "Carlos",   "apellido": "Ruiz",       "telefono": "1166778899", "email": "",
         "campos": {"Tipo de masaje": "Descontracturante", "Lesiones / Contraindicaciones": "Cervicalgia crónica", "Frecuencia de visitas": "Quincenal"}},
        {"nombre": "Ana",      "apellido": "López",      "telefono": "1177889900", "email": "analopez@outlook.com",
         "campos": {"Tipo de masaje": "Piedras calientes", "Lesiones / Contraindicaciones": "Ninguna", "Frecuencia de visitas": "Mensual"}},
        {"nombre": "Diego",    "apellido": "Torres",     "telefono": "1188990011", "email": "",
         "campos": {"Tipo de masaje": "Deportivo", "Lesiones / Contraindicaciones": "Hombro izquierdo (manguito rotador)", "Frecuencia de visitas": "Semanal"}},
        {"nombre": "Laura",    "apellido": "Martín",     "telefono": "1199001122", "email": "lauramartin@gmail.com",
         "campos": {"Tipo de masaje": "Circulatorio", "Lesiones / Contraindicaciones": "Várices en piernas — evitar presión directa", "Frecuencia de visitas": "Quincenal"}},
        {"nombre": "Roberto",  "apellido": "Sánchez",    "telefono": "1100112233", "email": "",
         "campos": {"Tipo de masaje": "Descontracturante", "Lesiones / Contraindicaciones": "Lumbalgia — evitar posición boca arriba", "Frecuencia de visitas": "Semanal"}},
        {"nombre": "Sofía",    "apellido": "García",     "telefono": "1111223344", "email": "sofiagarcia@hotmail.com",
         "campos": {"Tipo de masaje": "Relajación", "Lesiones / Contraindicaciones": "Embarazo 6 meses — masaje prenatal", "Frecuencia de visitas": "Mensual"}},
        {"nombre": "Pablo",    "apellido": "Rodríguez",  "telefono": "1122334455", "email": "",
         "campos": {"Tipo de masaje": "Deportivo", "Lesiones / Contraindicaciones": "Ninguna", "Frecuencia de visitas": "Semanal"}},
        {"nombre": "Elena",    "apellido": "Jiménez",    "telefono": "1133445566", "email": "elena.j@gmail.com",
         "campos": {"Tipo de masaje": "Tejido profundo", "Lesiones / Contraindicaciones": "Fibromialgia — presión moderada", "Frecuencia de visitas": "Quincenal"}},
        {"nombre": "Tomás",    "apellido": "Pérez",      "telefono": "1144556677", "email": "",
         "campos": {"Tipo de masaje": "Relajación", "Lesiones / Contraindicaciones": "Estrés laboral — priorizar cuello y espalda alta", "Frecuencia de visitas": "Mensual"}},
        {"nombre": "Claudia",  "apellido": "Vega",       "telefono": "1155667788", "email": "cvega@empresa.com",
         "campos": {"Tipo de masaje": "Reflexología", "Lesiones / Contraindicaciones": "Diabetes tipo 2 — revisar circulación antes", "Frecuencia de visitas": "Quincenal"}},
    ],
    "stock": [
        {"codigo": "ACEITE-LAV",   "descripcion": "Aceite esencial de lavanda 50ml",  "unidades": 8,  "precio_venta": 2200, "costo_compra": 1200, "proveedor": "Naturalia", "stock_minimo": 3},
        {"codigo": "ACEITE-EUC",   "descripcion": "Aceite de eucalipto 50ml",         "unidades": 6,  "precio_venta": 1800, "costo_compra": 1000, "proveedor": "Naturalia", "stock_minimo": 3},
        {"codigo": "ACEITE-ALM",   "descripcion": "Aceite de almendras 250ml",        "unidades": 4,  "precio_venta": 3500, "costo_compra": 2000, "proveedor": "Naturalia", "stock_minimo": 2},
        {"codigo": "TOALLA-GDE",   "descripcion": "Toalla grande 140x70cm",           "unidades": 6,  "precio_venta": 4500, "costo_compra": 2800, "proveedor": "Hogar Total", "stock_minimo": 4},
        {"codigo": "VELA-AROM",    "descripcion": "Vela aromática soja 200g",         "unidades": 12, "precio_venta": 1500, "costo_compra": 700, "proveedor": "Aromas SA", "stock_minimo": 5},
        {"codigo": "CREMA-HID",    "descripcion": "Crema hidratante corporal 500ml",  "unidades": 5,  "precio_venta": 2800, "costo_compra": 1600, "proveedor": "Naturalia", "stock_minimo": 2},
        {"codigo": "GEL-FRIO",     "descripcion": "Gel frío/calor 250g",              "unidades": 7,  "precio_venta": 1900, "costo_compra": 900, "proveedor": "FarmaMed", "stock_minimo": 3},
    ],
    "finanzas_iniciales": [
        {"desc": "Saldo inicial en efectivo",     "ingreso": 25000, "egreso": 0,     "cat": "Capital", "cuenta": "Efectivo en caja"},
        {"desc": "Compra aceites y cremas",       "ingreso": 0,     "egreso": 18500, "cat": "Insumos", "cuenta": "Efectivo en caja"},
        {"desc": "Sesión masaje — María Fernández","ingreso": 8000, "egreso": 0,     "cat": "Ventas",  "cuenta": "Mercado Pago"},
        {"desc": "Sesión masaje — Carlos Ruiz",   "ingreso": 8000,  "egreso": 0,     "cat": "Ventas",  "cuenta": "Efectivo en caja"},
        {"desc": "Sesión masaje — Diego Torres",  "ingreso": 9500,  "egreso": 0,     "cat": "Ventas",  "cuenta": "Mercado Pago"},
        {"desc": "Nafta semana del 20/05",        "ingreso": 0,     "egreso": 12000, "cat": "Gastos operativos", "cuenta": "Efectivo en caja"},
    ],
    "conversaciones_stress": [
        "Vino María Fernández, masaje deportivo de 60 min, cobré $8000 en Mercado Pago",
        "Comprá 5 aceites de lavanda en Naturalia, $1200 c/u, pagué en efectivo",
        "Actualizá los datos de Elena Jiménez: campo Lesiones / Contraindicaciones = Fibromialgia — presión leve únicamente",
        "Cuánto aceite de eucalipto me queda?",
        "Nuevo cliente: Martín Salazar, tel 1166554433, masaje descontracturante, viene con lumbalgia fuerte",
        "Hice 3 sesiones hoy: María Fernández $8000, Diego Torres $9500 y un nuevo cliente Pedro $7000. Todos pagaron en efectivo",
        "Se me acabaron casi las velas aromáticas. Compré 20 unidades en Aromas SA a $700 cada una",
        "Roberto Sánchez me canceló la cita de hoy, anotá en sus comentarios que canceló sin aviso",
        "Qué clientes tengo que tienen masaje semanal?",
        "Cuánto gané este mes?",
    ],
}

# ══════════════════════════════════════════════════════════════════════════════
# NEGOCIO 2 — Héctor Villanueva, Tornero
# ══════════════════════════════════════════════════════════════════════════════

TORNERO = {
    "perfil": {
        "nombre_negocio": "Tornería Villanueva",
        "email_admin": "hector.tornero.test@pokeoffice.ar",
        "nombre_jefe": "Héctor",
        "tipo_negocio": "Tornería y mecanizado de precisión",
        "moneda": "ARS",
        "sector": "Metal-mecánica",
        "descripcion": "Taller de tornería CNC y manual para industria y particulares.",
    },
    "columnas_clientes": ["Tipo de piezas habituales", "Material preferido", "Tolerancia requerida"],
    "clientes": [
        {"nombre": "Taller Mecánico",  "apellido": "El Rápido",      "telefono": "1122334400", "email": "taller.rapido@gmail.com",
         "campos": {"Tipo de piezas habituales": "Ejes de transmisión", "Material preferido": "Acero 1045", "Tolerancia requerida": "h6"}},
        {"nombre": "Construcciones",   "apellido": "Morales SA",      "telefono": "1133445500", "email": "compras@moralessal.com.ar",
         "campos": {"Tipo de piezas habituales": "Anclajes y tuercas especiales", "Material preferido": "Acero inoxidable 304", "Tolerancia requerida": "H7"}},
        {"nombre": "Juan",             "apellido": "Pérez",           "telefono": "1144556600", "email": "",
         "campos": {"Tipo de piezas habituales": "Piezas para moto", "Material preferido": "Aluminio 6061", "Tolerancia requerida": "js6"}},
        {"nombre": "Fábrica Textil",   "apellido": "Norte",           "telefono": "1155667700", "email": "mantenimiento@texnorte.com",
         "campos": {"Tipo de piezas habituales": "Rodillos y ejes", "Material preferido": "Acero 4140", "Tolerancia requerida": "k6"}},
        {"nombre": "Electrónica",      "apellido": "Omega SRL",       "telefono": "1166778800", "email": "omega@electronica.ar",
         "campos": {"Tipo de piezas habituales": "Carcasas y soportes", "Material preferido": "Aluminio", "Tolerancia requerida": "f7"}},
        {"nombre": "Roberto",          "apellido": "Flores",          "telefono": "1177889900", "email": "",
         "campos": {"Tipo de piezas habituales": "Piezas para tractor", "Material preferido": "Acero dulce", "Tolerancia requerida": "h8"}},
        {"nombre": "Hidráulica",       "apellido": "del Sur",         "telefono": "1188990000", "email": "pedidos@hidrsur.com",
         "campos": {"Tipo de piezas habituales": "Pistones y sellos", "Material preferido": "Bronce fosfórico", "Tolerancia requerida": "H6/f7"}},
        {"nombre": "Carpintería",      "apellido": "Artesanal Ramos", "telefono": "1199001100", "email": "",
         "campos": {"Tipo de piezas habituales": "Ejes para fresadora", "Material preferido": "Acero 1045", "Tolerancia requerida": "g6"}},
        {"nombre": "Metalúrgica",      "apellido": "Ramos Hnos",     "telefono": "1100112200", "email": "metalurgica@ramos.ar",
         "campos": {"Tipo de piezas habituales": "Prototipos varios", "Material preferido": "Indiferente", "Tolerancia requerida": "Según plano"}},
        {"nombre": "Cooperativa",      "apellido": "Agropecuaria",    "telefono": "1111223300", "email": "taller@coop.ar",
         "campos": {"Tipo de piezas habituales": "Repuestos maquinaria agrícola", "Material preferido": "Acero", "Tolerancia requerida": "h8/h9"}},
    ],
    "stock": [
        {"codigo": "BARRA-AC50",  "descripcion": "Barra acero 1045 Ø50mm x 1m",    "unidades": 5,  "precio_venta": 45000, "costo_compra": 30000, "proveedor": "Aceros del Norte", "stock_minimo": 2},
        {"codigo": "BARRA-AL30",  "descripcion": "Barra aluminio 6061 Ø30mm x 1m", "unidades": 8,  "precio_venta": 28000, "costo_compra": 18000, "proveedor": "Aluminios SRL", "stock_minimo": 3},
        {"codigo": "BARRA-BR25",  "descripcion": "Barra bronce Ø25mm x 1m",        "unidades": 4,  "precio_venta": 65000, "costo_compra": 45000, "proveedor": "Bronces SA", "stock_minimo": 2},
        {"codigo": "BROCAS-HSS",  "descripcion": "Juego brocas HSS 1-13mm",        "unidades": 3,  "precio_venta": 18000, "costo_compra": 11000, "proveedor": "Herramientas Pro", "stock_minimo": 1},
        {"codigo": "FRESA-10",    "descripcion": "Fresa de planear 10mm",           "unidades": 6,  "precio_venta": 12000, "costo_compra": 7500, "proveedor": "Herramientas Pro", "stock_minimo": 2},
        {"codigo": "LUBRIC-5L",   "descripcion": "Lubricante de corte 5 litros",   "unidades": 4,  "precio_venta": 8500,  "costo_compra": 5200, "proveedor": "Insumos Ind", "stock_minimo": 2},
        {"codigo": "PIEDRA-AF",   "descripcion": "Piedra de afilar combinada",     "unidades": 2,  "precio_venta": 4500,  "costo_compra": 2800, "proveedor": "Herramientas Pro", "stock_minimo": 1},
    ],
    "finanzas_iniciales": [
        {"desc": "Capital inicial banco",                  "ingreso": 150000, "egreso": 0,      "cat": "Capital",   "cuenta": "Banco cte."},
        {"desc": "Compra barras acero y aluminio",        "ingreso": 0,      "egreso": 78000,  "cat": "Materia prima", "cuenta": "Banco cte."},
        {"desc": "Trabajo ejes — Taller El Rápido",       "ingreso": 45000,  "egreso": 0,      "cat": "Ventas",    "cuenta": "Banco cte."},
        {"desc": "Trabajo pistones — Hidráulica del Sur", "ingreso": 68000,  "egreso": 0,      "cat": "Ventas",    "cuenta": "Efectivo en caja"},
        {"desc": "Compra lubricante y brocas",            "ingreso": 0,      "egreso": 22000,  "cat": "Materia prima", "cuenta": "Efectivo en caja"},
        {"desc": "Servicio eléctrico del taller",        "ingreso": 0,      "egreso": 35000,  "cat": "Gastos fijos", "cuenta": "Banco cte."},
        {"desc": "Trabajo urgente — Fábrica Textil",      "ingreso": 95000,  "egreso": 0,      "cat": "Ventas",    "cuenta": "Banco cte."},
    ],
    "conversaciones_stress": [
        "Terminé el trabajo del Taller El Rápido: 3 ejes de transmisión en acero 1045, cobré $45000 en efectivo",
        "Compré 2 barras de acero 50mm en Aceros del Norte, $30000 cada una, pagué con transferencia",
        "Nuevo cliente: Laboratorio Clínico Ponce, necesitan soportes de aluminio de precisión, tel 1144556677, tolerancia f7",
        "Cuánto lubricante me queda? Y brocas?",
        "Hidráulica del Sur me encargó 8 pistones de bronce, presupuesto $180000, materiales ya los tengo",
        "Terminé los pistones de Hidráulica, cobré $180000 por transferencia bancaria. El material usado fue 2 barras de bronce",
        "La Cooperativa Agropecuaria tiene una cosechadora parada, me mandan el plano hoy. Anotá que es urgente",
        "Gasté $12000 en electricidad del taller este mes",
        "Compré un juego nuevo de brocas HSS en Herramientas Pro a $11000, pagué en efectivo",
        "Qué trabajos tengo pendientes? Haceme un resumen de la semana",
    ],
}

# ══════════════════════════════════════════════════════════════════════════════
# NEGOCIO 3 — Taller Quiroga, Chapa y pintura
# ══════════════════════════════════════════════════════════════════════════════

TALLER_CHAPA = {
    "perfil": {
        "nombre_negocio": "Taller Quiroga Chapa y Pintura",
        "email_admin": "taller.quiroga.test@pokeoffice.ar",
        "nombre_jefe": "Quiroga",
        "tipo_negocio": "Taller de chapa, pintura y reparación de carrocería",
        "moneda": "ARS",
        "sector": "Automotriz",
        "descripcion": "Taller especializado en chapa, pintura y reparación de carrocería.",
    },
    "columnas_clientes": ["Patente", "Modelo y Color", "Estado del trabajo"],
    "clientes": [
        {"nombre": "Marcos",    "apellido": "Alvarez",  "telefono": "1133221100", "email": "m.alvarez@gmail.com",
         "campos": {"Patente": "ABC123", "Modelo y Color": "Renault Clio 2018 Gris", "Estado del trabajo": "Entregado"}},
        {"nombre": "Claudia",   "apellido": "Vega",     "telefono": "1144332211", "email": "claudia.vega@gmail.com",
         "campos": {"Patente": "DEF456", "Modelo y Color": "Toyota Corolla 2020 Blanco", "Estado del trabajo": "En pintura"}},
        {"nombre": "Fernando",  "apellido": "Suárez",   "telefono": "1155443322", "email": "",
         "campos": {"Patente": "GHI789", "Modelo y Color": "Ford Ka 2016 Rojo", "Estado del trabajo": "Presupuestado"}},
        {"nombre": "Patricia",  "apellido": "Ríos",     "telefono": "1166554433", "email": "patricia.rios@hotmail.com",
         "campos": {"Patente": "JKL012", "Modelo y Color": "Volkswagen Gol 2019 Negro", "Estado del trabajo": "Esperando repuesto"}},
        {"nombre": "Martín",    "apellido": "Cáceres",  "telefono": "1177665544", "email": "",
         "campos": {"Patente": "MNO345", "Modelo y Color": "Chevrolet Cruze 2021 Azul", "Estado del trabajo": "En chapa"}},
        {"nombre": "Verónica",  "apellido": "Montes",   "telefono": "1188776655", "email": "v.montes@empresa.com",
         "campos": {"Patente": "PQR678", "Modelo y Color": "Honda Fit 2017 Plateado", "Estado del trabajo": "Listo para retirar"}},
        {"nombre": "Jorge",     "apellido": "Paredes",  "telefono": "1199887766", "email": "",
         "campos": {"Patente": "STU901", "Modelo y Color": "Peugeot 208 2018 Verde", "Estado del trabajo": "Entregado"}},
        {"nombre": "Lucía",     "apellido": "Campos",   "telefono": "1100998877", "email": "lucia.campos@gmail.com",
         "campos": {"Patente": "VWX234", "Modelo y Color": "Fiat Uno 2015 Rojo", "Estado del trabajo": "En diagnóstico"}},
        {"nombre": "Alberto",   "apellido": "Mora",     "telefono": "1111009988", "email": "",
         "campos": {"Patente": "YZA567", "Modelo y Color": "Toyota Hilux 2022 Blanco", "Estado del trabajo": "Presupuestado"}},
        {"nombre": "Sandra",    "apellido": "Fuentes",  "telefono": "1122110099", "email": "sfuentes@hotmail.com",
         "campos": {"Patente": "BCD890", "Modelo y Color": "Renault Sandero 2020 Gris", "Estado del trabajo": "Entregado"}},
    ],
    "stock": [
        {"codigo": "PINT-BASE-B", "descripcion": "Pintura base blanca 4L",      "unidades": 8,  "precio_venta": 12000, "costo_compra": 8000, "proveedor": "Pinturas Omega", "stock_minimo": 3},
        {"codigo": "IMPRIMANTE",  "descripcion": "Imprimante anticorrosivo 4L", "unidades": 6,  "precio_venta": 10000, "costo_compra": 6500, "proveedor": "Pinturas Omega", "stock_minimo": 2},
        {"codigo": "MASILLA",     "descripcion": "Masilla plástica 1kg",        "unidades": 12, "precio_venta": 3500,  "costo_compra": 2000, "proveedor": "AutoPartes Sur", "stock_minimo": 5},
        {"codigo": "LIJA-220",    "descripcion": "Lija al agua grano 220",      "unidades": 50, "precio_venta": 300,   "costo_compra": 150,  "proveedor": "Abrasivos SA", "stock_minimo": 20},
        {"codigo": "LIJA-400",    "descripcion": "Lija al agua grano 400",      "unidades": 40, "precio_venta": 350,   "costo_compra": 180,  "proveedor": "Abrasivos SA", "stock_minimo": 15},
        {"codigo": "LIJA-600",    "descripcion": "Lija al agua grano 600",      "unidades": 30, "precio_venta": 400,   "costo_compra": 220,  "proveedor": "Abrasivos SA", "stock_minimo": 10},
        {"codigo": "SOLVENTE",    "descripcion": "Solvente celulósico 1L",      "unidades": 15, "precio_venta": 2200,  "costo_compra": 1300, "proveedor": "Químicos SA", "stock_minimo": 5},
        {"codigo": "BARNIZ",      "descripcion": "Barniz poliuretánico 1L",     "unidades": 10, "precio_venta": 8500,  "costo_compra": 5500, "proveedor": "Pinturas Omega", "stock_minimo": 3},
        {"codigo": "CINTA-ENM",   "descripcion": "Cinta de enmascarar 48mm",   "unidades": 20, "precio_venta": 1200,  "costo_compra": 700,  "proveedor": "AutoPartes Sur", "stock_minimo": 8},
    ],
    "finanzas_iniciales": [
        {"desc": "Capital inicial",                       "ingreso": 200000, "egreso": 0,      "cat": "Capital",    "cuenta": "Banco cte."},
        {"desc": "Trabajo Marcos Alvarez — Clio",        "ingreso": 85000,  "egreso": 0,      "cat": "Ventas",     "cuenta": "Efectivo en caja"},
        {"desc": "Compra pinturas y materiales",         "ingreso": 0,      "egreso": 45000,  "cat": "Materiales", "cuenta": "Banco cte."},
        {"desc": "Trabajo Sandra Fuentes — Sandero",     "ingreso": 65000,  "egreso": 0,      "cat": "Ventas",     "cuenta": "Mercado Pago"},
        {"desc": "Trabajo Jorge Paredes — Peugeot",      "ingreso": 120000, "egreso": 0,      "cat": "Ventas",     "cuenta": "Banco cte."},
        {"desc": "Servicio eléctrico del taller",       "ingreso": 0,      "egreso": 48000,  "cat": "Gastos fijos","cuenta": "Banco cte."},
        {"desc": "Alquiler del local",                   "ingreso": 0,      "egreso": 120000, "cat": "Gastos fijos","cuenta": "Banco cte."},
    ],
    "conversaciones_stress": [
        "Ingresó el auto de Patricia Ríos, patente JKL012, VW Gol Negro 2019. Tiene chapa abollada puerta trasera derecha. Presupuesto $95000",
        "Terminé el trabajo de Claudia Vega, cobré $120000 por pintura completa del Corolla. Pagó por transferencia",
        "Compré 10 latas de pintura base blanca en Pinturas Omega, $8000 cada una, pagué con tarjeta de crédito",
        "Actualizá el estado de Martín Cáceres: campo Estado del trabajo = Listo para retirar",
        "Nuevo cliente: Daniel Herrera, tel 1133445566, patente WER112, VW Polo 2023 Negro, abolladura en puerta. Presupuesto pendiente",
        "Usé 3 latas de masilla, 20 lijas del 220 y 15 del 400 para el trabajo de Cáceres. Descontá del stock",
        "Verónica Montes vino a buscar el auto, cobré $78000. Anotá que quedó muy conforme — posible cliente recurrente",
        "Se me están acabando las lijas del 600, quedan pocas. Hacé un pedido a Abrasivos SA de 50 unidades a $220 c/u",
        "Cuántos autos tengo actualmente en el taller?",
        "Cuánto llevo facturado este mes? Y cuánto gasté en materiales?",
    ],
}

# ══════════════════════════════════════════════════════════════════════════════
# NEGOCIO 4 — Sofía Ramos, Mates personalizados
# ══════════════════════════════════════════════════════════════════════════════

MATES_PERSONALIZADOS = {
    "perfil": {
        "nombre_negocio": "Sofía Mates & Arte",
        "email_admin": "sofia.mates.test@pokeoffice.ar",
        "nombre_jefe": "Sofía",
        "tipo_negocio": "Venta de mates artesanales personalizados",
        "moneda": "ARS",
        "sector": "Artesanías y regalería",
        "descripcion": "Elaboración y venta de mates personalizados con diseños únicos pintados a mano.",
    },
    "columnas_clientes": ["Diseño favorito", "Fecha de cumpleaños", "Mate preferido"],
    "clientes": [
        {"nombre": "Julieta",   "apellido": "Herrera",  "telefono": "1150001111", "email": "julieta.h@gmail.com",
         "campos": {"Diseño favorito": "Flores silvestres", "Fecha de cumpleaños": "15/03", "Mate preferido": "Calabaza natural"}},
        {"nombre": "Ramón",     "apellido": "Espinoza", "telefono": "1161112222", "email": "",
         "campos": {"Diseño favorito": "Escudo Racing Club", "Fecha de cumpleaños": "22/07", "Mate preferido": "Palo"}},
        {"nombre": "Catalina",  "apellido": "Vargas",   "telefono": "1172223333", "email": "cata.v@hotmail.com",
         "campos": {"Diseño favorito": "Mariposas", "Fecha de cumpleaños": "08/11", "Mate preferido": "Calabaza"}},
        {"nombre": "Bruno",     "apellido": "Morales",  "telefono": "1183334444", "email": "",
         "campos": {"Diseño favorito": "Boca Juniors", "Fecha de cumpleaños": "30/01", "Mate preferido": "Acero inoxidable"}},
        {"nombre": "Valeria",   "apellido": "Reyes",    "telefono": "1194445555", "email": "valeria.r@gmail.com",
         "campos": {"Diseño favorito": "Nombre personalizado + estrellitas", "Fecha de cumpleaños": "14/06", "Mate preferido": "Calabaza natural"}},
        {"nombre": "Nicolás",   "apellido": "Arce",     "telefono": "1105556666", "email": "",
         "campos": {"Diseño favorito": "Psicodélico neon", "Fecha de cumpleaños": "09/09", "Mate preferido": "Palo"}},
        {"nombre": "Florencia", "apellido": "Navarro",  "telefono": "1116667777", "email": "flo.navarro@gmail.com",
         "campos": {"Diseño favorito": "Girasoles", "Fecha de cumpleaños": "25/12", "Mate preferido": "Calabaza"}},
        {"nombre": "Esteban",   "apellido": "Giménez",  "telefono": "1127778888", "email": "",
         "campos": {"Diseño favorito": "Boca Juniors escudo grande", "Fecha de cumpleaños": "11/04", "Mate preferido": "Acero inoxidable"}},
        {"nombre": "Daniela",   "apellido": "Castro",   "telefono": "1138889999", "email": "dani.castro@outlook.com",
         "campos": {"Diseño favorito": "Mandala zentangle", "Fecha de cumpleaños": "03/08", "Mate preferido": "Calabaza natural"}},
        {"nombre": "Ignacio",   "apellido": "Romero",   "telefono": "1149990000", "email": "",
         "campos": {"Diseño favorito": "Sin diseño — solo nombre grabado", "Fecha de cumpleaños": "17/02", "Mate preferido": "Palo"}},
        {"nombre": "Rosa",      "apellido": "Paz",      "telefono": "1122334400", "email": "rosapaz@gmail.com",
         "campos": {"Diseño favorito": "Luna y estrellas", "Fecha de cumpleaños": "20/05", "Mate preferido": "Calabaza"}},
    ],
    "stock": [
        {"codigo": "MATE-PALO",   "descripcion": "Mate de palo natural",            "unidades": 15, "precio_venta": 4500,  "costo_compra": 2000, "proveedor": "Artesanías del Norte", "stock_minimo": 5},
        {"codigo": "MATE-CAL",    "descripcion": "Mate de calabaza curado",         "unidades": 20, "precio_venta": 3800,  "costo_compra": 1500, "proveedor": "Artesanías del Norte", "stock_minimo": 8},
        {"codigo": "MATE-ACERO",  "descripcion": "Mate acero inoxidable 300ml",    "unidades": 8,  "precio_venta": 6500,  "costo_compra": 3500, "proveedor": "ImportSur", "stock_minimo": 3},
        {"codigo": "BOMB-ALPACA", "descripcion": "Bombilla alpaca punta espiral",  "unidades": 25, "precio_venta": 2200,  "costo_compra": 900,  "proveedor": "Artesanías del Norte", "stock_minimo": 10},
        {"codigo": "BOMB-ACERO",  "descripcion": "Bombilla acero inoxidable",      "unidades": 18, "precio_venta": 1800,  "costo_compra": 700,  "proveedor": "ImportSur", "stock_minimo": 8},
        {"codigo": "PINT-ACRIL",  "descripcion": "Pintura acrílica negra 100ml",  "unidades": 10, "precio_venta": 1200,  "costo_compra": 600,  "proveedor": "Casa del Artesano", "stock_minimo": 3},
        {"codigo": "PINT-COLOR",  "descripcion": "Set pinturas acrílicas 12 colores","unidades": 6, "precio_venta": 3500, "costo_compra": 1800, "proveedor": "Casa del Artesano", "stock_minimo": 2},
        {"codigo": "BARNIZ-200",  "descripcion": "Barniz para madera 200ml",       "unidades": 8,  "precio_venta": 1800,  "costo_compra": 900,  "proveedor": "Casa del Artesano", "stock_minimo": 3},
        {"codigo": "VIROLA-ALP",  "descripcion": "Virola de alpaca Ø2cm",          "unidades": 30, "precio_venta": 800,   "costo_compra": 300,  "proveedor": "Ferretería Arte", "stock_minimo": 10},
    ],
    "finanzas_iniciales": [
        {"desc": "Capital inicial — ahorro personal",        "ingreso": 80000,  "egreso": 0,     "cat": "Capital",   "cuenta": "Efectivo en caja"},
        {"desc": "Compra mates y materiales iniciales",      "ingreso": 0,      "egreso": 35000, "cat": "Insumos",   "cuenta": "Efectivo en caja"},
        {"desc": "Venta mate — Julieta Herrera",             "ingreso": 6500,   "egreso": 0,     "cat": "Ventas",    "cuenta": "Mercado Pago"},
        {"desc": "Venta mate — Ramón Espinoza",              "ingreso": 7000,   "egreso": 0,     "cat": "Ventas",    "cuenta": "Efectivo en caja"},
        {"desc": "Venta pack 3 mates — regalo corporativo",  "ingreso": 24000,  "egreso": 0,     "cat": "Ventas",    "cuenta": "Mercado Pago"},
        {"desc": "Compra barnices y pinturas",               "ingreso": 0,      "egreso": 12000, "cat": "Insumos",   "cuenta": "Efectivo en caja"},
    ],
    "conversaciones_stress": [
        "Julieta Herrera me encargó un mate de calabaza con diseño de flores silvestres, precio $6500. Pagó el 50% de anticipo, $3250 por Mercado Pago",
        "Terminé y entregué el mate de Ramón Espinoza, cobré $7000 en efectivo. Escudo Racing quedó bárbaro",
        "Compré 20 mates de calabaza en Artesanías del Norte, $1500 cada uno, pagué efectivo",
        "Me quedan pocos barnices. Comprá 5 unidades de barniz 200ml en Casa del Artesano, $900 c/u, transferencia",
        "Nueva clienta: Rosa Paz, 1122334400, quiere un mate con diseño de luna y estrellas, cumple 20/05. Presupuesto $6000",
        "Esteban Giménez quiere un mate de acero con escudo de Boca. Tiene urgencia, lo necesita para el sábado. Precio $8500",
        "Hice 5 ventas esta semana: 3 mates calabaza a $4500 c/u y 2 mate acero a $7500 c/u. Todos por Mercado Pago",
        "Se me terminaron los sets de pinturas de colores. Comprá 4 sets en Casa del Artesano a $1800 c/u",
        "Daniela Castro quiere el mandala zentangle, pagó todo por adelantado $7000 transferencia. Entrega en 2 semanas",
        "Cuántos mates de calabaza me quedan? Y cuánto vendí este mes?",
    ],
}

# ══════════════════════════════════════════════════════════════════════════════
# NEGOCIO 5 — Bruno Escobar, Repartidor
# ══════════════════════════════════════════════════════════════════════════════

REPARTIDOR = {
    "perfil": {
        "nombre_negocio": "Bruno Express Reparto",
        "email_admin": "bruno.reparto.test@pokeoffice.ar",
        "nombre_jefe": "Bruno",
        "tipo_negocio": "Servicio de reparto y distribución local",
        "moneda": "ARS",
        "sector": "Logística y distribución",
        "descripcion": "Servicio de reparto y distribución en CABA, con enfoque en comercios de barrio.",
    },
    "columnas_clientes": ["Zona de entrega", "Días habituales", "Tipo de mercadería"],
    "clientes": [
        {"nombre": "Panadería",    "apellido": "La Esperanza",   "telefono": "1140001111", "email": "esperanza@panaderia.ar",
         "campos": {"Zona de entrega": "Villa del Parque", "Días habituales": "Lunes, Miércoles, Viernes", "Tipo de mercadería": "Panes y facturas empaquetados"}},
        {"nombre": "Farmacia",     "apellido": "Central",        "telefono": "1151112222", "email": "compras@farmaciacentral.com",
         "campos": {"Zona de entrega": "Palermo", "Días habituales": "Lunes a Viernes", "Tipo de mercadería": "Medicamentos y botiquín"}},
        {"nombre": "Librería",     "apellido": "Saber",          "telefono": "1162223333", "email": "",
         "campos": {"Zona de entrega": "Belgrano", "Días habituales": "Martes y Jueves", "Tipo de mercadería": "Libros, útiles escolares"}},
        {"nombre": "Ferretería",   "apellido": "Martín",         "telefono": "1173334444", "email": "ferreteria@martin.com",
         "campos": {"Zona de entrega": "Caballito", "Días habituales": "Miércoles y Viernes", "Tipo de mercadería": "Ferretería general — peso medio"}},
        {"nombre": "Supermercado", "apellido": "Barrio",         "telefono": "1184445555", "email": "",
         "campos": {"Zona de entrega": "Almagro", "Días habituales": "Lunes a Sábados", "Tipo de mercadería": "Comestibles no perecederos"}},
        {"nombre": "Tienda Moda",  "apellido": "Joven",          "telefono": "1195556666", "email": "modajoven@tienda.ar",
         "campos": {"Zona de entrega": "Flores", "Días habituales": "Lunes y Jueves", "Tipo de mercadería": "Indumentaria — cajas livianas"}},
        {"nombre": "Verdulería",   "apellido": "El Verde",       "telefono": "1106667777", "email": "",
         "campos": {"Zona de entrega": "San Telmo", "Días habituales": "Martes y Viernes", "Tipo de mercadería": "Frutas y verduras — frágil"}},
        {"nombre": "Kiosco",       "apellido": "Don Pedro",      "telefono": "1117778888", "email": "",
         "campos": {"Zona de entrega": "Boedo", "Días habituales": "Lunes a Sábados", "Tipo de mercadería": "Golosinas y bebidas"}},
        {"nombre": "Carnicería",   "apellido": "Los Andes",      "telefono": "1128889999", "email": "losandes@carniceria.com",
         "campos": {"Zona de entrega": "Villa Urquiza", "Días habituales": "Lunes, Miércoles, Viernes", "Tipo de mercadería": "Carnes — requiere frío"}},
        {"nombre": "Electrodomésticos", "apellido": "Sur",       "telefono": "1139990000", "email": "ventas@electrosur.ar",
         "campos": {"Zona de entrega": "Parque Patricios", "Días habituales": "Martes y Jueves", "Tipo de mercadería": "Electrodomésticos — frágil y voluminoso"}},
    ],
    "stock": [
        {"codigo": "CAJA-CH",    "descripcion": "Caja de cartón chica 40x30x20",  "unidades": 50, "precio_venta": 300,  "costo_compra": 150,  "proveedor": "Empaques Sur", "stock_minimo": 20},
        {"codigo": "CAJA-GDE",   "descripcion": "Caja de cartón grande 60x40x40", "unidades": 20, "precio_venta": 600,  "costo_compra": 300,  "proveedor": "Empaques Sur", "stock_minimo": 8},
        {"codigo": "BOLSA-NYL",  "descripcion": "Bolsa de nylon reforzada",       "unidades": 100,"precio_venta": 80,   "costo_compra": 40,   "proveedor": "Plásticos SA", "stock_minimo": 30},
        {"codigo": "CINTA-ADH",  "descripcion": "Cinta adhesiva transparente 48mm","unidades": 10, "precio_venta": 800, "costo_compra": 400,  "proveedor": "Papelería Norte", "stock_minimo": 4},
        {"codigo": "FILM-STR",   "descripcion": "Film stretch 50cm x 300m",       "unidades": 5,  "precio_venta": 4500, "costo_compra": 2500, "proveedor": "Empaques Sur", "stock_minimo": 2},
    ],
    "finanzas_iniciales": [
        {"desc": "Capital inicial",                           "ingreso": 50000,  "egreso": 0,     "cat": "Capital",          "cuenta": "Efectivo en caja"},
        {"desc": "8 entregas lunes — varios clientes",       "ingreso": 16000,  "egreso": 0,     "cat": "Ventas",           "cuenta": "Efectivo en caja"},
        {"desc": "Nafta semana del 19/05",                   "ingreso": 0,      "egreso": 14000, "cat": "Combustible",      "cuenta": "Efectivo en caja"},
        {"desc": "10 entregas miércoles",                    "ingreso": 22000,  "egreso": 0,     "cat": "Ventas",           "cuenta": "Efectivo en caja"},
        {"desc": "Seguro mensual moto/auto",                 "ingreso": 0,      "egreso": 28000, "cat": "Gastos fijos",     "cuenta": "Banco cte."},
        {"desc": "Compra cajas y materiales de embalaje",    "ingreso": 0,      "egreso": 8500,  "cat": "Materiales",       "cuenta": "Efectivo en caja"},
        {"desc": "12 entregas viernes — Supermercado Barrio","ingreso": 18000,  "egreso": 0,     "cat": "Ventas",           "cuenta": "Mercado Pago"},
    ],
    "conversaciones_stress": [
        "Hice 8 entregas hoy, cobré $2000 por cada una en efectivo, total $16000",
        "Gasté $14000 en nafta esta semana. Anotalo como gasto de combustible",
        "La Panadería La Esperanza ahora quiere que también vaya los sábados. Actualizá sus días: campo Días habituales = Lunes, Miércoles, Viernes, Sábados",
        "Compré 30 cajas de cartón chica en Empaques Sur, $150 cada una, pagué en efectivo",
        "Nueva clienta: Floristería Las Rosas, Chacarita, entregas martes y sábados, flores y plantas (frágil!), tel 1166778899",
        "Cobré $22000 de todas las entregas del miércoles. Mitad efectivo mitad Mercado Pago",
        "La Carnicería Los Andes quiere empezar a agregarme el reparto los sábados también. Son cargas pesadas, cobro extra $3000 ese día",
        "Se me acabó el film stretch. Compré 5 rollos en Empaques Sur a $2500 c/u",
        "Gasté $28000 en el seguro mensual del auto. Bancario",
        "Cuánto llevo de ingresos este mes? Y cuánto en gastos de nafta?",
    ],
}

# ── Índice global ─────────────────────────────────────────────────────────────

TODOS_LOS_NEGOCIOS = [MASAJISTA, TORNERO, TALLER_CHAPA, MATES_PERSONALIZADOS, REPARTIDOR]
