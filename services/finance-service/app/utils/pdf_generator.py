from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from datetime import datetime
from decimal import Decimal
import textwrap

# --- CONFIGURACIÓN DE TICKET ---
# Ancho estándar de impresora térmica de 80mm (el área imprimible es aprox 72mm)
TICKET_WIDTH = 72 * mm
# Altura inicial "infinita", luego la recortaremos al tamaño real del contenido
MAX_HEIGHT = 1000 * mm

# Estilos de fuente simulados
FONT_NORMAL = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_SIZE_S = 8
FONT_SIZE_M = 9
FONT_SIZE_L = 10

class FiscalTicketGenerator:
    def __init__(self, buffer, invoice_data, tenant_config, items):
        self.c = canvas.Canvas(buffer, pagesize=(TICKET_WIDTH, MAX_HEIGHT))
        self.invoice = invoice_data
        self.config = tenant_config # Aqui viene RIF, Dirección, Preferencias
        self.items = items
        self.cursor_y = MAX_HEIGHT - (5 * mm) # Margen superior
        self.left_margin = 2 * mm
        self.right_margin = TICKET_WIDTH - (2 * mm)
        self.rate = Decimal(invoice_data.get('rate', 1))
        
        def _move_down(self, amount):
            self.cursor_y -= amount
            
        def _draw_text_center(self, text, font=FONT_NORMAL, size=FONT_SIZE_M):
            self.c.setFont(font, size)
            self.c.drawCentredString(TICKET_WIDTH / 2, self.cursor_y, text)
            self._move_down(size + 2)
            
        def _draw_text_left(self, text, font=FONT_NORMAL, size=FONT_SIZE_M):
            self.c.setFont(font, size)
            self.c.drawString(self.left_margin, self.cursor_y, text)
            self._move_down(size + 1)
            
        def _draw_line(self):
            self._move_down(2)
            self.c.setDash(1, 2) # Línea punteada 
            self.c.line(self.left_margin, self.cursor_y, self.right_margin, self.cursor_y)
            self.c.setDash([]) # Reset
            self._move_down(5)
            
        def _draw_row(self, col1, col2, font=FONT_NORMAL, size=FONT_SIZE_M, bold_col2=False):
            self.c.setFont(font, size)
            self.c.drawString(self.left_margin, self.cursor_y, col1)
            if bold_col2: self.c.setFont(FONT_BOLD, size)
            self.c.drawRightString(self.right_margin, self.cursor_y, col2)
            self._move_down(size + 1)
            
        def _format_currency(self, amount_usd):
            # Lógica de visualización según preferencias del dueño
            amount_usd = Decimal(amount_usd)
            amount_ves = amount_usd * self.rate
            
            mode = self.config.get('currency_display', 'VES_ONLY')
            
            if mode == 'VES_ONLY':
                return f"Bs. {amount_ves:,.2f}"
            elif mode == 'DUAL':
                return f"${amount_usd:,.2f} / Bs. {amount_ves:,.2f}"
            else: # MIXED (por defecto muesta USD)
                return f"${amount_usd:,.2f}"
        
        def generate(self):
            # Encabezado fiscal
            self._draw_text_center(self.config.get('business_name', 'NEGOCIO DEMO C.A'), FONT_BOLD, FONT_SIZE_L)
            self._draw_text_center(f"RIF: {self.config.get('rif', 'J-00000000-0')}", FONT_BOLD)
            
            # Dirección multilínea
            address = self.config.get('address', 'Dirección Fiscal no configurada')
            # Funcion
            self._draw_text_center(address[:40], size=FONT_SIZE_S)
            if len(address) > 40: self._draw_text_center(address[40:80], size=FONT_SIZE_S)
            
            self._draw_text_center(f"Telf: {self.config.get('phone', '')}", size=FONT_SIZE_S)
            self._draw_line()
            
            # Datos del Documento y Cliente
            invoice_number = str(self.invoice.get('id')).zfill(8)
            self._draw_text_left(f"FACTURA: 000-001-00{invoice_number}")
            # Serial de la Impresora Fiscal (Simulado)
            self._draw_text_left(f"SERIAL: Z3A0923412")
            
            created_at = self.invoice.get('created_at')
            if isinstance(created_at, str): created_at = datetime.fromisoformat(created_at)
            self._draw_text_left(f"FECHA: {created_at.strftime('%d/%m/%Y')}   HORA: {created_at.strftime('%H:%M')}")
            self._draw_text_left(f"CAJA: 01     CAJERO: ADMINISTRADOR") # Cambiar luego
            
            self._move_down(5)
            customer_info = self.invoice.get('customer_email') or "CLIENTE CONTADO"
            self._draw_text_left(f"CLIENTE: {customer_info}")
            self._draw_text_left(f"RIF/C.I.: V-00000000") # Placeholder
            self._draw_line()

            # Items de Venta
            self.c.setFont(FONT_BOLD, FONT_SIZE_S)
            
            self.c.drawString(self.left_margin, self.cursor_y, "DESCRIPCION")
            self.c.drawRightString(self.right_margin - (30*mm), self.cursor_y, "CANTxP.UNIT")
            self.c.drawRightString(self.right_margin, self.cursor_y, "TOTAL")
            self._move_down(10)
            
            for item in self.items:
                # Línea 1: Nombre del producto
                self._draw_text_left(item.product_name[:30], size=FONT_SIZE_M)
                
                # Línea 2: Cantidad x Precio = Subtotal
                qty = Decimal(item.quantity)
                price = Decimal(item.unit_price)
                total = Decimal(item.total_price)
                
                math_str = f"{qty:.2f} x {self._format_currency(price)}"
                total_str = self._format_currency(total)
                
                self.c.setFont(FONT_NORMAL, FONT_SIZE_S)
                self.c.drawRightString(self.right_margin - (25*mm), self.cursor_y, math_str)
                self.c.setFont(FONT_BOLD, FONT_SIZE_M)
                self.c.drawRightString(self.right_margin, self.cursor_y, total_str)
                self._move_down(FONT_SIZE_M + 4)
            
            self._draw_line()
            
            # Totales Fiscales
            
            # Usamos una función auxiliar para decidir qué moneda mostrar en los totales
            def _fmt_total(key_usd):
                val_usd = Decimal(self.invoice.get(key_usd, 0))
                if self.config.get('currency_display') == 'VES_ONLY':
                    return f"Bs {(val_usd * self.rate):,.2f}"
                # Para DUAL y MIXED, los subtotales suelen mostrarse en la moneda principal (USD)
                # y solo el gran total final se muestra en ambas.
                return f"${val_usd:,.2f}"

            if Decimal(self.invoice.get('subtotal_exento', 0)) > 0:
                self._draw_row("MONTO EXENTO:", _fmt_total('subtotal_exento'))

            # Base Imponible y Alicuota (Asumiendo 16% General)
            base_g = Decimal(self.invoice.get('subtotal_base_g', 0))
            tax_g = Decimal(self.invoice.get('tax_g', 0))
            
            if base_g > 0:
                self._draw_row("BASE IMPONIBLE (G) 16%:", _fmt_total('subtotal_base_g'))
                self._draw_row("IVA (G) 16%:", _fmt_total('tax_g'))

            self._draw_line()
            
            # GRAN TOTAL
            total_usd = Decimal(self.invoice.get('total_amount', 0))
            total_ves = total_usd * self.rate

            self.c.setFont(FONT_BOLD, FONT_SIZE_L + 2)
            self.c.drawString(self.left_margin, self.cursor_y, "TOTAL A PAGAR:")
            self._move_down(FONT_SIZE_L + 4)

            # Visualización del Gran Total según preferencia
            display_mode = self.config.get('currency_display', 'DUAL')
            
            if display_mode in ['DUAL', 'MIXED_TOTAL']:
                # Primero Dólares grande
                self.c.setFont(FONT_BOLD, 14)
                self.c.drawRightString(self.right_margin, self.cursor_y, f"$ {total_usd:,.2f}")
                self._move_down(16)
                # Luego Bolívares
                self.c.setFont(FONT_BOLD, 12)
                self.c.drawRightString(self.right_margin, self.cursor_y, f"Bs {total_ves:,.2f}")
                self._move_down(14)
            elif display_mode == 'VES_ONLY':
                self.c.setFont(FONT_BOLD, 14)
                self.c.drawRightString(self.right_margin, self.cursor_y, f"Bs {total_ves:,.2f}")
                self._move_down(16)

            self._move_down(5)
            self._draw_text_center(f"TASA DE CAMBIO BCV: Bs {self.rate:,.2f}", size=FONT_SIZE_S)
            self._draw_line()
            self._draw_text_center("¡GRACIAS POR SU COMPRA!", FONT_BOLD)

            # --- FINALIZACIÓN Y RECORTE ---
            # Calculamos la altura real usada y recortamos el PDF
            real_height = MAX_HEIGHT - self.cursor_y + (10*mm)
            self.c.setPageSize((TICKET_WIDTH, real_height))
            self.c.translate(0, real_height - MAX_HEIGHT)
            
            self.c.save()

def get_ticket_pdf_buffer(invoice_data: dict, items: list, tenant_config: dict):
    buffer = BytesIO()
    generator = FiscalTicketGenerator(buffer, invoice_data, tenant_config, items)
    generator.generate()
    buffer.seek(0)
    return buffer