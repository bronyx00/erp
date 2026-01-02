# accounting-service/services/template_engine.py
from decimal import Decimal
from datetime import date
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app import models, schemas

class AccountingTemplateEngine:

    @staticmethod
    async def get_available_templates(db: AsyncSession, tenant_id: int) -> list[schemas.EntryTemplate]:
        
        # --- HELPER: Buscar opciones dinámicamente ---
        async def _get_options(parent_code_prefix: str, account_type: str = None) -> list[schemas.TemplateOption]:
            """
            Busca cuentas transaccionales que empiencen con un código (hijas).
            Ej: '1.01.01' traerá Caja, Bancos, etc
            """
            
            query = select(models.Account).filter(
                models.Account.tenant_id == tenant_id,
                models.Account.is_transactional == True,
                models.Account.is_active == True,
                models.Account.code.ilike(f"{parent_code_prefix}%")
            )
            if account_type:
                query = query.filter(models.Account.account_type == account_type)
            
            result = await db.execute(query)
            accounts = result.scalars().all()
            
            options = [schemas.TemplateOption(label=acc.name, value=acc.code) for acc in accounts]
            return options
        
        # --- CARGA DE OPTIONES EN TIEMPO REAL ---
        
        # 1. Opciones de Tesorería (Cajas y Bancos) -> Grupo 1.01.01
        treasury_options = await _get_options("1.01.01")
        
        # 2. Opciones de Gastos Generales -> Grupo 6.02
        expense_options = await _get_options("6.02")
        # Gastos de personal 
        expense_options += await _get_options("6.01")
        
        return [
            # PLANTILLA 1: GASTOS 
            schemas.EntryTemplate(
                id="expense_petty_cash",
                name="Gasto de Caja Chica",
                description="Registro de gastos menores pagados en efectivo.",
                fields=[
                    schemas.TemplateField(key="amount", label="Monto Total ($)", type="number"),
                    schemas.TemplateField(
                        key="expense_type", 
                        label="¿Qué se gastó?", 
                        type="select",
                        options=expense_options
                    ),
                    schemas.TemplateField(
                        key="payment_source",
                        label="¿Cómo se pagó?",
                        type="select",
                        options=treasury_options
                    ),
                    schemas.TemplateField(key="concept", label="Detalle", type="text", required=False),
                ]
            ),

            # PLANTILLA 2: PAGO A PROVEEDORES 
            schemas.EntryTemplate(
                id="supplier_payment",
                name="Pago a Proveedores",
                description="Salida de dinero para cancelar facturas de proveedores.",
                fields=[
                    schemas.TemplateField(key="amount", label="Monto ($)", type="number"),
                    schemas.TemplateField(key="provider_name", label="Proveedor", type="text"),
                    schemas.TemplateField(
                        key="payment_source", 
                        label="Medio de Pago", 
                        type="select",
                        options=treasury_options
                    ),
                    schemas.TemplateField(key="ref", label="Referencia / Nro Recibo", type="text"),
                ]
            ),
            
            # PLANTILLA 3: COBRO A CLIENTES
            schemas.EntryTemplate(
                id="customer_collection",
                name="Cobranza a Cliente",
                description="Entrada de dinero por pago de factura de cliente.",
                fields=[
                    schemas.TemplateField(key="amount", label="Monto ($)", type="number"),
                    schemas.TemplateField(key="customer_name", label="Cliente", type="text"),
                    schemas.TemplateField(
                        key="deposit_target", 
                        label="Dónde ingresó el dinero", 
                        type="select",
                        options=treasury_options
                    )
                ]
            )
        ]

    @staticmethod
    async def process_template(
        db: AsyncSession, 
        tenant_id: int, 
        request: schemas.ApplyTemplateRequest
    ) -> schemas.LedgerEntryCreate:
        
        data = request.data
        amount = Decimal(str(data.get("amount", 0)))
        
        if amount <= 0:
            raise ValueError("El monto debe ser mayor a cero")

        lines = []
        description = ""
        reference = data.get("ref", None)

        # Helper para buscar ID
        async def get_acc_id(code: str):
            res = await db.execute(select(models.Account).filter_by(code=code, tenant_id=tenant_id))
            acc = res.scalars().first()
            if not acc:
                # Fallback: Intentar buscar sin tenant si son cuentas globales, 
                # o lanzar error descriptivo
                raise ValueError(f"La cuenta contable {code} no está configurada en su plan de cuentas.")
            return acc.id

        # --- LÓGICA DINÁMICA ---
        
        if request.template_id == "expense_petty_cash":
            # 1. Obtenemos la cuenta de Gasto seleccionada por el usuario
            expense_code = data.get("expense_type")
            expense_acc_id = await get_acc_id(expense_code)
            
            # 2. La cuenta de Caja Chica es fija (o podría ser otro select si tienes varias cajas)
            petty_cash_id = await get_acc_id("1.01.01.002") 
            
            concept = data.get("concept") or "Gastos Varios"
            description = f"Caja Chica: {concept}"
            
            # Asiento: Gasto (Debe) contra Caja (Haber)
            lines.append(schemas.LedgerLineCreate(account_id=expense_acc_id, debit=amount, credit=0))
            lines.append(schemas.LedgerLineCreate(account_id=petty_cash_id, debit=0, credit=amount))

        elif request.template_id == "supplier_payment":
            # 1. Cuenta de Pasivo (Proveedores Nacionales por defecto)
            # En un sistema V2, esto vendría de la ficha del proveedor seleccionado
            supplier_liab_id = await get_acc_id("2.01.01.001") 
            
            # 2. Cuenta de Activo (Banco/Caja) seleccionada
            payment_source_code = data.get("payment_source")
            bank_acc_id = await get_acc_id(payment_source_code)
            
            provider = data.get("provider_name", "Proveedor")
            description = f"Pago a {provider}"
            
            # Asiento: Pasivo (Debe - disminuye deuda) contra Banco (Haber - sale dinero)
            lines.append(schemas.LedgerLineCreate(account_id=supplier_liab_id, debit=amount, credit=0))
            lines.append(schemas.LedgerLineCreate(account_id=bank_acc_id, debit=0, credit=amount))

        elif request.template_id == "customer_collection":
            # 1. Cuenta de Activo (Donde entra el dinero)
            target_code = data.get("deposit_target")
            target_acc_id = await get_acc_id(target_code)
            
            # 2. Cuenta de Activo (Cuentas por Cobrar - Disminuye)
            ar_id = await get_acc_id("1.01.02.001") # Clientes Nacionales
            
            customer = data.get("customer_name", "Cliente")
            description = f"Cobro a {customer}"
            
            # Asiento: Banco (Debe - entra dinero) contra CxC (Haber - baja deuda del cliente)
            lines.append(schemas.LedgerLineCreate(account_id=target_acc_id, debit=amount, credit=0))
            lines.append(schemas.LedgerLineCreate(account_id=ar_id, debit=0, credit=amount))

        else:
            raise ValueError("Plantilla no encontrada")

        return schemas.LedgerEntryCreate(
            transaction_date=date.today(),
            description=description,
            reference=reference,
            lines=lines
        )