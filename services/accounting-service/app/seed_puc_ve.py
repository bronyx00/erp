import asyncio
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Account
from app.database import AsyncSessionLocal

# PUC VENEZUELA 2025 (Estructura Base Completa)
# Nivel 1: Grupo, Nivel 2: Rubro, Nivel 3: Cuenta Mayor
PUC_FULL_DATA = [
    # --- 1. ACTIVOS ---
    {"code": "1", "name": "ACTIVO", "account_type": "ASSET", "level": 1, "is_transactional": False, "parent_code": None},
    {"code": "1.01", "name": "ACTIVO CORRIENTE", "account_type": "ASSET", "level": 2, "is_transactional": False, "parent_code": "1"},
    
    # 1.01.01 Efectivo
    {"code": "1.01.01", "name": "Efectivo y Equivalentes de Efectivo", "account_type": "ASSET", "level": 3, "is_transactional": False, "parent_code": "1.01"},
    {"code": "1.01.01.001", "name": "Caja Principal", "account_type": "ASSET", "level": 4, "is_transactional": True, "parent_code": "1.01.01"},
    {"code": "1.01.01.002", "name": "Caja Chica", "account_type": "ASSET", "level": 4, "is_transactional": True, "parent_code": "1.01.01"},
    {"code": "1.01.01.003", "name": "Bancos Nacionales", "account_type": "ASSET", "level": 4, "is_transactional": True, "parent_code": "1.01.01"},
    {"code": "1.01.01.004", "name": "Bancos Moneda Extranjera", "account_type": "ASSET", "level": 4, "is_transactional": True, "parent_code": "1.01.01"},

    # 1.01.02 Inversiones
    {"code": "1.01.02", "name": "Inversiones Financieras a Corto Plazo", "account_type": "ASSET", "level": 3, "is_transactional": True, "parent_code": "1.01"},

    # 1.01.03 Cuentas por Cobrar (Exigible)
    {"code": "1.01.03", "name": "Cuentas y Efectos por Cobrar Comerciales", "account_type": "ASSET", "level": 3, "is_transactional": False, "parent_code": "1.01"},
    {"code": "1.01.03.001", "name": "Cuentas por Cobrar Clientes Nacionales", "account_type": "ASSET", "level": 4, "is_transactional": True, "parent_code": "1.01.03"},
    {"code": "1.01.03.002", "name": "Cuentas por Cobrar Clientes Extranjeros", "account_type": "ASSET", "level": 4, "is_transactional": True, "parent_code": "1.01.03"},
    {"code": "1.01.03.003", "name": "Efectos por Cobrar", "account_type": "ASSET", "level": 4, "is_transactional": True, "parent_code": "1.01.03"},
    {"code": "1.01.03.099", "name": "Provisión Cuentas Incobrables", "account_type": "ASSET", "level": 4, "is_transactional": True, "parent_code": "1.01.03"},

    # 1.01.04 Otras Cuentas por Cobrar
    {"code": "1.01.04", "name": "Otras Cuentas por Cobrar", "account_type": "ASSET", "level": 3, "is_transactional": False, "parent_code": "1.01"},
    {"code": "1.01.04.001", "name": "Anticipo a Proveedores", "account_type": "ASSET", "level": 4, "is_transactional": True, "parent_code": "1.01.04"},
    {"code": "1.01.04.002", "name": "Préstamos a Empleados", "account_type": "ASSET", "level": 4, "is_transactional": True, "parent_code": "1.01.04"},
    {"code": "1.01.04.003", "name": "Crédito Fiscal IVA (A favor)", "account_type": "ASSET", "level": 4, "is_transactional": True, "parent_code": "1.01.04"},
    {"code": "1.01.04.004", "name": "ISLR Retenido por Clientes (Anticipo)", "account_type": "ASSET", "level": 4, "is_transactional": True, "parent_code": "1.01.04"},

    # 1.01.05 Inventarios (Realizable)
    {"code": "1.01.05", "name": "Inventarios", "account_type": "ASSET", "level": 3, "is_transactional": False, "parent_code": "1.01"},
    {"code": "1.01.05.001", "name": "Inventario de Mercancía", "account_type": "ASSET", "level": 4, "is_transactional": True, "parent_code": "1.01.05"},
    {"code": "1.01.05.002", "name": "Inventario de Materia Prima", "account_type": "ASSET", "level": 4, "is_transactional": True, "parent_code": "1.01.05"},
    {"code": "1.01.05.003", "name": "Inventario de Productos en Proceso", "account_type": "ASSET", "level": 4, "is_transactional": True, "parent_code": "1.01.05"},
    {"code": "1.01.05.004", "name": "Inventario de Suministros", "account_type": "ASSET", "level": 4, "is_transactional": True, "parent_code": "1.01.05"},

    # 1.02 ACTIVO NO CORRIENTE
    {"code": "1.02", "name": "ACTIVO NO CORRIENTE", "account_type": "ASSET", "level": 2, "is_transactional": False, "parent_code": "1"},
    
    # 1.02.01 Propiedad Planta y Equipo
    {"code": "1.02.01", "name": "Propiedad, Planta y Equipo", "account_type": "ASSET", "level": 3, "is_transactional": False, "parent_code": "1.02"},
    {"code": "1.02.01.001", "name": "Terrenos", "account_type": "ASSET", "level": 4, "is_transactional": True, "parent_code": "1.02.01"},
    {"code": "1.02.01.002", "name": "Edificios", "account_type": "ASSET", "level": 4, "is_transactional": True, "parent_code": "1.02.01"},
    {"code": "1.02.01.003", "name": "Depreciación Acum. Edificios", "account_type": "ASSET", "level": 4, "is_transactional": True, "parent_code": "1.02.01"},
    {"code": "1.02.01.004", "name": "Maquinaria y Equipos", "account_type": "ASSET", "level": 4, "is_transactional": True, "parent_code": "1.02.01"},
    {"code": "1.02.01.005", "name": "Depreciación Acum. Maquinaria", "account_type": "ASSET", "level": 4, "is_transactional": True, "parent_code": "1.02.01"},
    {"code": "1.02.01.006", "name": "Mobiliario y Enseres", "account_type": "ASSET", "level": 4, "is_transactional": True, "parent_code": "1.02.01"},
    {"code": "1.02.01.007", "name": "Equipos de Computación", "account_type": "ASSET", "level": 4, "is_transactional": True, "parent_code": "1.02.01"},

    # --- 2. PASIVOS ---
    {"code": "2", "name": "PASIVO", "account_type": "LIABILITY", "level": 1, "is_transactional": False, "parent_code": None},
    {"code": "2.01", "name": "PASIVO CORRIENTE", "account_type": "LIABILITY", "level": 2, "is_transactional": False, "parent_code": "2"},
    
    # 2.01.01 Ctas por Pagar
    {"code": "2.01.01", "name": "Cuentas y Efectos por Pagar Comerciales", "account_type": "LIABILITY", "level": 3, "is_transactional": False, "parent_code": "2.01"},
    {"code": "2.01.01.001", "name": "Proveedores Nacionales", "account_type": "LIABILITY", "level": 4, "is_transactional": True, "parent_code": "2.01.01"},
    {"code": "2.01.01.002", "name": "Proveedores Extranjeros", "account_type": "LIABILITY", "level": 4, "is_transactional": True, "parent_code": "2.01.01"},

    # 2.01.02 Obligaciones Fiscales (Crucial en Venezuela)
    {"code": "2.01.02", "name": "Obligaciones Fiscales y Parafiscales", "account_type": "LIABILITY", "level": 3, "is_transactional": False, "parent_code": "2.01"},
    {"code": "2.01.02.001", "name": "Débito Fiscal IVA", "account_type": "LIABILITY", "level": 4, "is_transactional": True, "parent_code": "2.01.02"},
    {"code": "2.01.02.002", "name": "IVA por Pagar (Cuota)", "account_type": "LIABILITY", "level": 4, "is_transactional": True, "parent_code": "2.01.02"},
    {"code": "2.01.02.003", "name": "Retenciones IVA por Pagar", "account_type": "LIABILITY", "level": 4, "is_transactional": True, "parent_code": "2.01.02"},
    {"code": "2.01.02.004", "name": "Retenciones ISLR por Pagar", "account_type": "LIABILITY", "level": 4, "is_transactional": True, "parent_code": "2.01.02"},
    {"code": "2.01.02.005", "name": "ISLR por Pagar (Empresa)", "account_type": "LIABILITY", "level": 4, "is_transactional": True, "parent_code": "2.01.02"},
    {"code": "2.01.02.006", "name": "Aportes Parafiscales (SSO, FAOV, INCES)", "account_type": "LIABILITY", "level": 4, "is_transactional": True, "parent_code": "2.01.02"},
    {"code": "2.01.02.007", "name": "IGTF por Pagar (3%)", "account_type": "LIABILITY", "level": 4, "is_transactional": True, "parent_code": "2.01.02"},

    # 2.01.03 Obligaciones Laborales
    {"code": "2.01.03", "name": "Obligaciones Laborales", "account_type": "LIABILITY", "level": 3, "is_transactional": False, "parent_code": "2.01"},
    {"code": "2.01.03.001", "name": "Sueldos y Salarios por Pagar", "account_type": "LIABILITY", "level": 4, "is_transactional": True, "parent_code": "2.01.03"},
    {"code": "2.01.03.002", "name": "Prestaciones Sociales por Pagar", "account_type": "LIABILITY", "level": 4, "is_transactional": True, "parent_code": "2.01.03"},
    {"code": "2.01.03.003", "name": "Utilidades por Pagar", "account_type": "LIABILITY", "level": 4, "is_transactional": True, "parent_code": "2.01.03"},

    # --- 3. PATRIMONIO ---
    {"code": "3", "name": "PATRIMONIO", "account_type": "EQUITY", "level": 1, "is_transactional": False, "parent_code": None},
    {"code": "3.01", "name": "CAPITAL SOCIAL", "account_type": "EQUITY", "level": 2, "is_transactional": False, "parent_code": "3"},
    {"code": "3.01.01", "name": "Capital Suscrito y Pagado", "account_type": "EQUITY", "level": 3, "is_transactional": True, "parent_code": "3.01"},
    {"code": "3.02", "name": "RESULTADOS", "account_type": "EQUITY", "level": 2, "is_transactional": False, "parent_code": "3"},
    {"code": "3.02.01", "name": "Utilidades No Distribuidas", "account_type": "EQUITY", "level": 3, "is_transactional": True, "parent_code": "3.02"},
    {"code": "3.02.02", "name": "Resultado del Ejercicio", "account_type": "EQUITY", "level": 3, "is_transactional": True, "parent_code": "3.02"},

    # --- 4. INGRESOS ---
    {"code": "4", "name": "INGRESOS", "account_type": "REVENUE", "level": 1, "is_transactional": False, "parent_code": None},
    {"code": "4.01", "name": "INGRESOS OPERACIONALES", "account_type": "REVENUE", "level": 2, "is_transactional": False, "parent_code": "4"},
    {"code": "4.01.01", "name": "Ventas Brutas", "account_type": "REVENUE", "level": 3, "is_transactional": True, "parent_code": "4.01"},
    {"code": "4.01.02", "name": "Devoluciones en Ventas", "account_type": "REVENUE", "level": 3, "is_transactional": True, "parent_code": "4.01"},
    {"code": "4.01.03", "name": "Descuentos en Ventas", "account_type": "REVENUE", "level": 3, "is_transactional": True, "parent_code": "4.01"},
    
    # --- 5. COSTOS ---
    {"code": "5", "name": "COSTOS", "account_type": "EXPENSE", "level": 1, "is_transactional": False, "parent_code": None},
    {"code": "5.01", "name": "COSTO DE VENTAS", "account_type": "EXPENSE", "level": 2, "is_transactional": False, "parent_code": "5"},
    {"code": "5.01.01", "name": "Costo de Mercancía Vendida", "account_type": "EXPENSE", "level": 3, "is_transactional": True, "parent_code": "5.01"},
    {"code": "5.01.02", "name": "Compras de Mercancía", "account_type": "EXPENSE", "level": 3, "is_transactional": True, "parent_code": "5.01"},

    # --- 6. GASTOS ---
    {"code": "6", "name": "GASTOS OPERACIONALES", "account_type": "EXPENSE", "level": 1, "is_transactional": False, "parent_code": None},
    
    # 6.01 Gastos de Personal
    {"code": "6.01", "name": "Gastos de Personal", "account_type": "EXPENSE", "level": 2, "is_transactional": False, "parent_code": "6"},
    {"code": "6.01.01", "name": "Sueldos y Salarios", "account_type": "EXPENSE", "level": 3, "is_transactional": True, "parent_code": "6.01"},
    {"code": "6.01.02", "name": "Bonos y Comisiones", "account_type": "EXPENSE", "level": 3, "is_transactional": True, "parent_code": "6.01"},
    {"code": "6.01.03", "name": "Prestaciones Sociales", "account_type": "EXPENSE", "level": 3, "is_transactional": True, "parent_code": "6.01"},
    {"code": "6.01.04", "name": "Cestaticket (Alimentación)", "account_type": "EXPENSE", "level": 3, "is_transactional": True, "parent_code": "6.01"},

    # 6.02 Servicios
    {"code": "6.02", "name": "Servicios Públicos y Privados", "account_type": "EXPENSE", "level": 2, "is_transactional": False, "parent_code": "6"},
    {"code": "6.02.01", "name": "Alquileres", "account_type": "EXPENSE", "level": 3, "is_transactional": True, "parent_code": "6.02"},
    {"code": "6.02.02", "name": "Electricidad", "account_type": "EXPENSE", "level": 3, "is_transactional": True, "parent_code": "6.02"},
    {"code": "6.02.03", "name": "Internet y Telefonía", "account_type": "EXPENSE", "level": 3, "is_transactional": True, "parent_code": "6.02"},
    {"code": "6.02.04", "name": "Mantenimiento y Reparaciones", "account_type": "EXPENSE", "level": 3, "is_transactional": True, "parent_code": "6.02"},
    
    # 6.03 Tributarios
    {"code": "6.03", "name": "Gastos Tributarios", "account_type": "EXPENSE", "level": 2, "is_transactional": False, "parent_code": "6"},
    {"code": "6.03.01", "name": "Impuestos Municipales", "account_type": "EXPENSE", "level": 3, "is_transactional": True, "parent_code": "6.03"},
    {"code": "6.03.02", "name": "IGTF (Gasto Deducible)", "account_type": "EXPENSE", "level": 3, "is_transactional": True, "parent_code": "6.03"},

    # 6.04 Depreciaciones
    {"code": "6.04", "name": "Depreciaciones y Amortizaciones", "account_type": "EXPENSE", "level": 2, "is_transactional": False, "parent_code": "6"},
    {"code": "6.04.01", "name": "Gasto Depreciación", "account_type": "EXPENSE", "level": 3, "is_transactional": True, "parent_code": "6.04"},
]

async def seed_puc(tenant_id: int):
    """
    Inserta el PUC usando Core SQLAlchemy Bulk Insert para máxima velocidad.
    Resuelve las relaciones parent_id dinámicamente.
    """
    db = AsyncSessionLocal()
    try:
        print("Iniciando carga masiva del PUC Venezuela (Bulk Mode)...")
        
        # 1. Mapeo de Código -> ID para resolver padres
        # Como necesitamos los IDs para los padres, insertaremos por niveles
        # Nivel 1 (Sin padres) -> Nivel 2 (Padres ya existen) -> etc.
        
        code_to_id_map = {}
        
        # Determinamos cuantos niveles hay
        max_level = max(item['level'] for item in PUC_FULL_DATA)
        
        for level in range(1, max_level + 1):
            current_level_accounts = [x for x in PUC_FULL_DATA if x['level'] == level]
            
            if not current_level_accounts:
                continue
                
            insert_data = []
            for item in current_level_accounts:
                parent_id = None
                if item['parent_code']:
                    parent_id = code_to_id_map.get(item['parent_code'])
                    if not parent_id:
                        print(f"Advertencia: Padre {item['parent_code']} no encontrado para {item['code']}")
                
                insert_data.append({
                    "tenant_id": tenant_id,
                    "code": item['code'],
                    "name": item['name'],
                    "account_type": item['account_type'],
                    "level": item['level'],
                    "is_transactional": item['is_transactional'],
                    "parent_id": parent_id,
                    "is_active": True,
                    "balance": 0
                })
            
            if insert_data:
                stmt = insert(Account).values(insert_data).returning(Account.id, Account.code)
                result = await db.execute(stmt)
                
                # Guardamos los IDs generados para usarlos como parent_id en el siguiente nivel
                for row in result:
                    code_to_id_map[row.code] = row.id
            
        await db.commit()
        print(f"Carga completa. Total cuentas procesadas: {len(code_to_id_map)}")
        
    except Exception as e:
        print(f"Error crítico cargando PUC: {e}")
        await db.rollback()
    finally:
        await db.close()

if __name__ == "__main__":
    import sys
    tid = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    asyncio.run(seed_puc(tid))