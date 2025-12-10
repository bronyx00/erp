import asyncio
import sys
from sqlalchemy import insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.models import Account
from app.database import AsyncSessionLocal

# ==============================================================================
#  PUC VENEZUELA - BASE COMÚN (NIVEL 4/5 DETALLADO)
# ==============================================================================
CORE_ACCOUNTS = [
    # --- 1. ACTIVO ---
    {"code": "1", "name": "ACTIVO", "account_type": "ASSET", "level": 1, "parent": None},
    {"code": "1.01", "name": "ACTIVO CORRIENTE", "account_type": "ASSET", "level": 2, "parent": "1"},
    
    # Disponibles
    {"code": "1.01.01", "name": "Efectivo y Equivalentes", "account_type": "ASSET", "level": 3, "parent": "1.01"},
    {"code": "1.01.01.001", "name": "Caja Principal", "account_type": "ASSET", "level": 4, "parent": "1.01.01", "tx": True},
    {"code": "1.01.01.002", "name": "Caja Chica Administrativa", "account_type": "ASSET", "level": 4, "parent": "1.01.01", "tx": True},
    {"code": "1.01.01.003", "name": "Bancos Nacionales", "account_type": "ASSET", "level": 4, "parent": "1.01.01", "tx": True},
    {"code": "1.01.01.004", "name": "Bancos Moneda Extranjera (Custodia)", "account_type": "ASSET", "level": 4, "parent": "1.01.01", "tx": True},
    {"code": "1.01.01.005", "name": "Billeteras Digitales (Binance/Zelle)", "account_type": "ASSET", "level": 4, "parent": "1.01.01", "tx": True},

    # Exigibles
    {"code": "1.01.02", "name": "Cuentas por Cobrar", "account_type": "ASSET", "level": 3, "parent": "1.01"},
    {"code": "1.01.02.001", "name": "Clientes Nacionales", "account_type": "ASSET", "level": 4, "parent": "1.01.02", "tx": True},
    {"code": "1.01.02.002", "name": "Clientes Extranjeros", "account_type": "ASSET", "level": 4, "parent": "1.01.02", "tx": True},
    {"code": "1.01.02.003", "name": "Préstamos a Empleados", "account_type": "ASSET", "level": 4, "parent": "1.01.02", "tx": True},
    {"code": "1.01.02.004", "name": "Anticipos a Proveedores", "account_type": "ASSET", "level": 4, "parent": "1.01.02", "tx": True},
    {"code": "1.01.02.005", "name": "Reclamos a Seguros", "account_type": "ASSET", "level": 4, "parent": "1.01.02", "tx": True},

    # Activos Fiscales (Venezuela)
    {"code": "1.01.05", "name": "Activos Fiscales", "account_type": "ASSET", "level": 3, "parent": "1.01"},
    {"code": "1.01.05.001", "name": "Crédito Fiscal IVA", "account_type": "ASSET", "level": 4, "parent": "1.01.05", "tx": True},
    {"code": "1.01.05.002", "name": "Retenciones de ISLR (Soportadas)", "account_type": "ASSET", "level": 4, "parent": "1.01.05", "tx": True},
    {"code": "1.01.05.003", "name": "Retenciones de IVA (Soportadas)", "account_type": "ASSET", "level": 4, "parent": "1.01.05", "tx": True},
    {"code": "1.01.05.004", "name": "Anticipos de ISLR", "account_type": "ASSET", "level": 4, "parent": "1.01.05", "tx": True},

    # Propiedad Planta y Equipo 
    {"code": "1.02", "name": "ACTIVO NO CORRIENTE", "account_type": "ASSET", "level": 2, "parent": "1"},
    {"code": "1.02.01", "name": "Propiedad Planta y Equipo", "account_type": "ASSET", "level": 3, "parent": "1.02"},
    {"code": "1.02.01.001", "name": "Mobiliario y Enseres", "account_type": "ASSET", "level": 4, "parent": "1.02.01", "tx": True},
    {"code": "1.02.01.002", "name": "Equipos de Computación", "account_type": "ASSET", "level": 4, "parent": "1.02.01", "tx": True},
    {"code": "1.02.01.003", "name": "Vehículos", "account_type": "ASSET", "level": 4, "parent": "1.02.01", "tx": True},
    {"code": "1.02.01.004", "name": "Depreciación Acumulada", "account_type": "ASSET", "level": 4, "parent": "1.02.01", "tx": True},

    # --- 2. PASIVO ---
    {"code": "2", "name": "PASIVO", "account_type": "LIABILITY", "level": 1, "parent": None},
    {"code": "2.01", "name": "PASIVO CORRIENTE", "account_type": "LIABILITY", "level": 2, "parent": "2"},
    
    # Obligaciones Comerciales
    {"code": "2.01.01", "name": "Cuentas por Pagar", "account_type": "LIABILITY", "level": 3, "parent": "2.01"},
    {"code": "2.01.01.001", "name": "Proveedores Nacionales", "account_type": "LIABILITY", "level": 4, "parent": "2.01.01", "tx": True},
    {"code": "2.01.01.002", "name": "Proveedores del Exterior", "account_type": "LIABILITY", "level": 4, "parent": "2.01.01", "tx": True},
    
    # Obligaciones Fiscales 
    {"code": "2.01.02", "name": "Obligaciones Fiscales", "account_type": "LIABILITY", "level": 3, "parent": "2.01"},
    {"code": "2.01.02.001", "name": "Débito Fiscal IVA", "account_type": "LIABILITY", "level": 4, "parent": "2.01.02", "tx": True},
    {"code": "2.01.02.002", "name": "Retenciones IVA por Enterar", "account_type": "LIABILITY", "level": 4, "parent": "2.01.02", "tx": True},
    {"code": "2.01.02.003", "name": "Retenciones ISLR por Enterar", "account_type": "LIABILITY", "level": 4, "parent": "2.01.02", "tx": True},
    {"code": "2.01.02.004", "name": "IGTF por Pagar (3%)", "account_type": "LIABILITY", "level": 4, "parent": "2.01.02", "tx": True},
    {"code": "2.01.02.005", "name": "Impuestos Municipales por Pagar", "account_type": "LIABILITY", "level": 4, "parent": "2.01.02", "tx": True},

    # Obligaciones Laborales 
    {"code": "2.01.03", "name": "Obligaciones Laborales", "account_type": "LIABILITY", "level": 3, "parent": "2.01"},
    {"code": "2.01.03.001", "name": "Sueldos y Salarios por Pagar", "account_type": "LIABILITY", "level": 4, "parent": "2.01.03", "tx": True},
    {"code": "2.01.03.002", "name": "Cestaticket por Pagar", "account_type": "LIABILITY", "level": 4, "parent": "2.01.03", "tx": True},
    {"code": "2.01.03.003", "name": "SSO / IVSS por Pagar", "account_type": "LIABILITY", "level": 4, "parent": "2.01.03", "tx": True},
    {"code": "2.01.03.004", "name": "FAOV (Banavih) por Pagar", "account_type": "LIABILITY", "level": 4, "parent": "2.01.03", "tx": True},
    {"code": "2.01.03.005", "name": "INCES por Pagar", "account_type": "LIABILITY", "level": 4, "parent": "2.01.03", "tx": True},
    {"code": "2.01.03.006", "name": "Prestaciones Sociales Acumuladas", "account_type": "LIABILITY", "level": 4, "parent": "2.01.03", "tx": True},

    # --- 3. PATRIMONIO ---
    {"code": "3", "name": "PATRIMONIO", "account_type": "EQUITY", "level": 1, "parent": None},
    {"code": "3.01", "name": "Capital", "account_type": "EQUITY", "level": 2, "parent": "3"},
    {"code": "3.01.01", "name": "Capital Social Suscrito y Pagado", "account_type": "EQUITY", "level": 3, "parent": "3.01", "tx": True},
    {"code": "3.02", "name": "Resultados", "account_type": "EQUITY", "level": 2, "parent": "3"},
    {"code": "3.02.01", "name": "Utilidades no Distribuidas", "account_type": "EQUITY", "level": 3, "parent": "3.02", "tx": True},
    {"code": "3.02.02", "name": "Resultado del Ejercicio", "account_type": "EQUITY", "level": 3, "parent": "3.02", "tx": True},

    # --- 4. INGRESOS ---
    {"code": "4", "name": "INGRESOS", "account_type": "REVENUE", "level": 1, "parent": None},
    {"code": "4.01", "name": "Ingresos Operacionales", "account_type": "REVENUE", "level": 2, "parent": "4"},
    {"code": "4.01.01", "name": "Ventas", "account_type": "REVENUE", "level": 3, "parent": "4.01"},
    {"code": "4.01.01.001", "name": "Ventas de Contado", "account_type": "REVENUE", "level": 4, "parent": "4.01.01", "tx": True},
    {"code": "4.01.01.002", "name": "Ventas a Crédito", "account_type": "REVENUE", "level": 4, "parent": "4.01.01", "tx": True},
    {"code": "4.01.02", "name": "Otros Ingresos", "account_type": "REVENUE", "level": 3, "parent": "4.01"},
    {"code": "4.01.02.001", "name": "Ganancia en Cambio", "account_type": "REVENUE", "level": 4, "parent": "4.01.02", "tx": True},

    # --- 5. COSTOS (Estructura) ---
    {"code": "5", "name": "COSTOS", "account_type": "EXPENSE", "level": 1, "parent": None},
    
    # --- 6. GASTOS ---
    {"code": "6", "name": "GASTOS OPERATIVOS", "account_type": "EXPENSE", "level": 1, "parent": None},
    
    # 6.01 Personal
    {"code": "6.01", "name": "Gastos de Personal", "account_type": "EXPENSE", "level": 2, "parent": "6"},
    {"code": "6.01.01", "name": "Sueldos y Salarios", "account_type": "EXPENSE", "level": 3, "parent": "6.01", "tx": True},
    {"code": "6.01.02", "name": "Cestaticket Socialista", "account_type": "EXPENSE", "level": 3, "parent": "6.01", "tx": True},
    {"code": "6.01.03", "name": "Vacaciones y Bono Vacacional", "account_type": "EXPENSE", "level": 3, "parent": "6.01", "tx": True},
    {"code": "6.01.04", "name": "Utilidades (Bonificación Fin de Año)", "account_type": "EXPENSE", "level": 3, "parent": "6.01", "tx": True},
    {"code": "6.01.05", "name": "Aportes Patronales (IVSS, FAOV, INCES)", "account_type": "EXPENSE", "level": 3, "parent": "6.01", "tx": True},
    {"code": "6.01.06", "name": "Prestaciones Sociales", "account_type": "EXPENSE", "level": 3, "parent": "6.01", "tx": True},
    {"code": "6.01.07", "name": "Viáticos y Movilización", "account_type": "EXPENSE", "level": 3, "parent": "6.01", "tx": True},

    # 6.02 Servicios y Funcionamiento
    {"code": "6.02", "name": "Gastos Generales y Servicios", "account_type": "EXPENSE", "level": 2, "parent": "6"},
    {"code": "6.02.01", "name": "Alquileres de Local/Oficina", "account_type": "EXPENSE", "level": 3, "parent": "6.02", "tx": True},
    {"code": "6.02.02", "name": "Condominio", "account_type": "EXPENSE", "level": 3, "parent": "6.02", "tx": True},
    {"code": "6.02.03", "name": "Electricidad y Agua", "account_type": "EXPENSE", "level": 3, "parent": "6.02", "tx": True},
    {"code": "6.02.04", "name": "Internet y Telefonía", "account_type": "EXPENSE", "level": 3, "parent": "6.02", "tx": True},
    {"code": "6.02.05", "name": "Honorarios Profesionales (Contador/Abogado)", "account_type": "EXPENSE", "level": 3, "parent": "6.02", "tx": True},
    {"code": "6.02.06", "name": "Mantenimiento y Reparaciones", "account_type": "EXPENSE", "level": 3, "parent": "6.02", "tx": True},
    {"code": "6.02.07", "name": "Materiales de Oficina y Limpieza", "account_type": "EXPENSE", "level": 3, "parent": "6.02", "tx": True},
    {"code": "6.02.08", "name": "Publicidad y Redes Sociales", "account_type": "EXPENSE", "level": 3, "parent": "6.02", "tx": True},

    # 6.03 Financieros y Tributarios
    {"code": "6.03", "name": "Gastos Financieros y Tributarios", "account_type": "EXPENSE", "level": 2, "parent": "6"},
    {"code": "6.03.01", "name": "Comisiones Bancarias y POS", "account_type": "EXPENSE", "level": 3, "parent": "6.03", "tx": True},
    {"code": "6.03.02", "name": "IGTF (Gasto Deducible)", "account_type": "EXPENSE", "level": 3, "parent": "6.03", "tx": True},
    {"code": "6.03.03", "name": "Impuestos Municipales (Patente)", "account_type": "EXPENSE", "level": 3, "parent": "6.03", "tx": True},
    {"code": "6.03.04", "name": "Pérdida en Cambio", "account_type": "EXPENSE", "level": 3, "parent": "6.03", "tx": True},

    # 6.04 Depreciaciones
    {"code": "6.04", "name": "Depreciación y Amortización", "account_type": "EXPENSE", "level": 2, "parent": "6"},
    {"code": "6.04.01", "name": "Depreciación Propiedad Planta y Equipo", "account_type": "EXPENSE", "level": 3, "parent": "6.04", "tx": True},
]

# ==============================================================================
#  SECTOR: COMERCIO / RETAIL / SUPERMERCADOS
# ==============================================================================
COMMERCE_ACCOUNTS = [
    # Activos
    {"code": "1.01.05", "name": "Inventarios", "account_type": "ASSET", "level": 3, "parent": "1.01"},
    {"code": "1.01.05.001", "name": "Inventario de Mercancía para la Venta", "account_type": "ASSET", "level": 4, "parent": "1.01.05", "tx": True},
    {"code": "1.01.05.002", "name": "Mercancía en Tránsito", "account_type": "ASSET", "level": 4, "parent": "1.01.05", "tx": True},
    
    # Costos
    {"code": "5.01", "name": "COSTO DE VENTAS", "account_type": "EXPENSE", "level": 2, "parent": "5"},
    {"code": "5.01.01", "name": "Costo de Mercancía Vendida", "account_type": "EXPENSE", "level": 3, "parent": "5.01", "tx": True},
    {"code": "5.01.02", "name": "Mermas y Desperdicios de Inventario", "account_type": "EXPENSE", "level": 3, "parent": "5.01", "tx": True},
    {"code": "5.01.03", "name": "Fletes en Compras", "account_type": "EXPENSE", "level": 3, "parent": "5.01", "tx": True},

    # Gastos Específicos
    {"code": "6.02.09", "name": "Gastos de Embalaje y Bolsas", "account_type": "EXPENSE", "level": 3, "parent": "6.02", "tx": True},
    {"code": "6.02.10", "name": "Faltantes de Caja", "account_type": "EXPENSE", "level": 3, "parent": "6.02", "tx": True},
]

# ==============================================================================
#  SECTOR: MANUFACTURA / INDUSTRIA
# ==============================================================================
INDUSTRY_ACCOUNTS = [
    # Inventarios Complejos
    {"code": "1.01.05", "name": "Inventarios", "account_type": "ASSET", "level": 3, "parent": "1.01"},
    {"code": "1.01.05.001", "name": "Inventario de Materia Prima", "account_type": "ASSET", "level": 4, "parent": "1.01.05", "tx": True},
    {"code": "1.01.05.002", "name": "Inventario de Productos en Proceso", "account_type": "ASSET", "level": 4, "parent": "1.01.05", "tx": True},
    {"code": "1.01.05.003", "name": "Inventario de Productos Terminados", "account_type": "ASSET", "level": 4, "parent": "1.01.05", "tx": True},
    {"code": "1.01.05.004", "name": "Inventario de Suministros de Fábrica", "account_type": "ASSET", "level": 4, "parent": "1.01.05", "tx": True},

    # Costos de Producción Detallados
    {"code": "5.01", "name": "COSTOS DE PRODUCCIÓN", "account_type": "EXPENSE", "level": 2, "parent": "5"},
    {"code": "5.01.01", "name": "Materia Prima Directa Consumida", "account_type": "EXPENSE", "level": 3, "parent": "5.01", "tx": True},
    {"code": "5.01.02", "name": "Mano de Obra Directa", "account_type": "EXPENSE", "level": 3, "parent": "5.01", "tx": True},
    {"code": "5.01.03", "name": "Costos Indirectos de Fabricación (CIF)", "account_type": "EXPENSE", "level": 3, "parent": "5.01", "tx": True},
    {"code": "5.01.04", "name": "Depreciación Maquinaria Industrial", "account_type": "EXPENSE", "level": 3, "parent": "5.01", "tx": True},
    {"code": "5.01.05", "name": "Electricidad Planta", "account_type": "EXPENSE", "level": 3, "parent": "5.01", "tx": True},
]

# ==============================================================================
#  SECTOR: SERVICIOS / HONORARIOS / FREELANCE
# ==============================================================================
SERVICE_ACCOUNTS = [
    # Activos Intangibles
    {"code": "1.02.02", "name": "Activos Intangibles", "account_type": "ASSET", "level": 3, "parent": "1.02"},
    {"code": "1.02.02.001", "name": "Software y Licencias", "account_type": "ASSET", "level": 4, "parent": "1.02.02", "tx": True},
    {"code": "1.02.02.002", "name": "Marcas y Patentes", "account_type": "ASSET", "level": 4, "parent": "1.02.02", "tx": True},

    # Ingresos Específicos
    {"code": "4.01.03", "name": "Ingresos por Servicios", "account_type": "REVENUE", "level": 3, "parent": "4.01"},
    {"code": "4.01.03.001", "name": "Honorarios Profesionales", "account_type": "REVENUE", "level": 4, "parent": "4.01.03", "tx": True},
    {"code": "4.01.03.002", "name": "Contratos de Mantenimiento", "account_type": "REVENUE", "level": 4, "parent": "4.01.03", "tx": True},
    {"code": "4.01.03.003", "name": "Asesorías y Consultorías", "account_type": "REVENUE", "level": 4, "parent": "4.01.03", "tx": True},

    # Costos del Servicio (No hay inventario, hay horas/hombre)
    {"code": "5.01", "name": "COSTOS DEL SERVICIO", "account_type": "EXPENSE", "level": 2, "parent": "5"},
    {"code": "5.01.01", "name": "Sueldos Personal Operativo (Proyectos)", "account_type": "EXPENSE", "level": 3, "parent": "5.01", "tx": True},
    {"code": "5.01.02", "name": "Viáticos de Proyectos", "account_type": "EXPENSE", "level": 3, "parent": "5.01", "tx": True},
    {"code": "5.01.03", "name": "Licencias y Software de Clientes", "account_type": "EXPENSE", "level": 3, "parent": "5.01", "tx": True},
]

# ==============================================================================
#  SECTOR: AGROPECUARIO / GANADERÍA
# ==============================================================================
AGRICULTURE_ACCOUNTS = [
    # Activos Biológicos
    {"code": "1.01.06", "name": "Activos Biológicos Corrientes", "account_type": "ASSET", "level": 3, "parent": "1.01"},
    {"code": "1.01.06.001", "name": "Cultivos en Proceso (Siembra)", "account_type": "ASSET", "level": 4, "parent": "1.01.06", "tx": True},
    {"code": "1.01.06.002", "name": "Ganado de Engorde", "account_type": "ASSET", "level": 4, "parent": "1.01.06", "tx": True},
    
    {"code": "1.02.03", "name": "Activos Biológicos No Corrientes", "account_type": "ASSET", "level": 3, "parent": "1.02"},
    {"code": "1.02.03.001", "name": "Ganado Reproductor (Plantel)", "account_type": "ASSET", "level": 4, "parent": "1.02.03", "tx": True},
    {"code": "1.02.03.002", "name": "Plantaciones Permanentes (Frutales)", "account_type": "ASSET", "level": 4, "parent": "1.02.03", "tx": True},

    # Costos de Explotación
    {"code": "5.01", "name": "COSTOS DE EXPLOTACIÓN", "account_type": "EXPENSE", "level": 2, "parent": "5"},
    {"code": "5.01.01", "name": "Insumos Agrícolas (Semillas/Fertilizantes)", "account_type": "EXPENSE", "level": 3, "parent": "5.01", "tx": True},
    {"code": "5.01.02", "name": "Alimento y Medicina Veterinaria", "account_type": "EXPENSE", "level": 3, "parent": "5.01", "tx": True},
    {"code": "5.01.03", "name": "Mano de Obra Campo", "account_type": "EXPENSE", "level": 3, "parent": "5.01", "tx": True},
    {"code": "5.01.04", "name": "Combustible Maquinaria Agrícola", "account_type": "EXPENSE", "level": 3, "parent": "5.01", "tx": True},
]

# Mapa de Plantillas
TEMPLATES = {
    "general": CORE_ACCOUNTS, # Por defecto
    "commerce": CORE_ACCOUNTS + COMMERCE_ACCOUNTS,
    "retail": CORE_ACCOUNTS + COMMERCE_ACCOUNTS, # Alias
    "services": CORE_ACCOUNTS + SERVICE_ACCOUNTS,
    "industry": CORE_ACCOUNTS + INDUSTRY_ACCOUNTS,
    "manufacturing": CORE_ACCOUNTS + INDUSTRY_ACCOUNTS, # Alias
    "agriculture": CORE_ACCOUNTS + AGRICULTURE_ACCOUNTS,
    "livestock": CORE_ACCOUNTS + AGRICULTURE_ACCOUNTS # Alias
}

async def seed_puc(tenant_id: int, sector: str = "commerce"):
    """
    Carga inteligente de Plan de Cuentas.
    sector: 'commerce', 'services', 'industry', 'agriculture'.
    """
    db = AsyncSessionLocal()
    try:
        # Normalizar sector
        sector_key = sector.lower()
        selected_accounts = TEMPLATES.get(sector_key, TEMPLATES["commerce"])
        
        print(f"🚀 [SEED] Iniciando carga de Plantilla '{sector_key.upper()}' para Tenant {tenant_id}")
        
        # Eliminar duplicados por código (en caso de que listas se solapen)
        unique_accounts = {a['code']: a for a in selected_accounts}.values()
        
        # Ordenar rigurosamente por nivel (1->2->3->4) para garantizar padres
        sorted_accounts = sorted(unique_accounts, key=lambda x: x['level'])
        
        # Mapa en memoria: { "1.01": 15, "1.01.01": 22 }
        code_to_id_map = {}
        
        # Insertar nivel por nivel
        max_level = max(item['level'] for item in sorted_accounts)
        
        for level in range(1, max_level + 1):
            level_batch = [x for x in sorted_accounts if x['level'] == level]
            if not level_batch: 
                continue
                
            insert_rows = []
            for item in level_batch:
                # Buscar ID del padre
                parent_id = None
                if item['parent']:
                    parent_id = code_to_id_map.get(item['parent'])
                    if not parent_id:
                        # Si es nivel > 1 y no tiene padre, es un error de lógica de la plantilla, pero no rompemos
                        print(f"⚠️ [SEED] Padre '{item['parent']}' no encontrado para '{item['code']}'. Se insertará sin padre.")
                
                insert_rows.append({
                    "tenant_id": tenant_id,
                    "code": item['code'],
                    "name": item['name'],
                    "account_type": item['account_type'],
                    "level": item['level'],
                    "is_transactional": item.get('tx', False),
                    "parent_id": parent_id,
                    "is_active": True,
                    "balance": 0
                })

            if insert_rows:
                # UPSERT: Insertar, si existe el código para ese tenant, ignorar (Do Nothing)
                stmt = pg_insert(Account).values(insert_rows)
                stmt = stmt.on_conflict_do_nothing(
                    constraint='uq_account_code_tenant'
                ).returning(Account.id, Account.code)
                
                result = await db.execute(stmt)
                new_rows = result.all()
                
                # Actualizar mapa con los nuevos IDs
                for row in new_rows:
                    code_to_id_map[row.code] = row.id
                
                # CRÍTICO: Si "Do Nothing" se activó, no nos devuelve ID.
                # Debemos buscar los IDs de las cuentas que YA existían para poder usarlas de padres.
                # Solo buscamos si el número de insertados < número de intentados
                if len(new_rows) < len(insert_rows):
                     codes_to_fetch = [x['code'] for x in insert_rows]
                     from sqlalchemy import select
                     existing_query = select(Account.id, Account.code).filter(
                         Account.tenant_id == tenant_id,
                         Account.code.in_(codes_to_fetch)
                     )
                     existing_res = await db.execute(existing_query)
                     for row in existing_res:
                         code_to_id_map[row.code] = row.id

        await db.commit()
        print(f"✅ [SEED] Carga completada exitosamente. Total cuentas disponibles: {len(code_to_id_map)}")
        
    except Exception as e:
        print(f"❌ [SEED] Error crítico: {e}")
        await db.rollback()
    finally:
        await db.close()

if __name__ == "__main__":
    # Soporte para ejecutar: python seed_puc_ve.py <tenant_id> <sector>
    tid = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    sec = sys.argv[2] if len(sys.argv) > 2 else "commerce"
    asyncio.run(seed_puc(tid, sec))