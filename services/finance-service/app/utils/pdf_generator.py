from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from decimal import Decimal
import textwrap

# Configuración de papel térmico 80mm
PAGE_WIDTH = 72 * mm 
MAX_HEIGHT = 2000 * mm

# Estilos de fuente
FONT_NORMAL = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_SIZE_S = 8
FONT_SIZE_M = 9
FONT_SIZE_L = 10

class FiscalTicketGenerator:
    def __init__(self, buffer, invoice_data, tenant_config, items):
        self.c = canvas.Canvas(buffer, pagesize=(PAGE_WIDTH, MAX_HEIGHT))
        self.invoice = invoice_data
        self.config = tenant_config 
        self.items = items
        self.cursor_y = MAX_HEIGHT - (5 * mm)
        self.left_margin = 2 * mm
        self.right_margin = PAGE_WIDTH - (2 * mm)
        # Manejo seguro de la tasa
        try:
            self.rate = Decimal(invoice_data.get('rate', 1))
        except:
            self.rate = Decimal(1)

    # --- MÉTODOS ALINEADOS A LA IZQUIERDA (AL MISMO NIVEL QUE __INIT__) ---
    def _move_down(self, amount):
        self.cursor_y -= amount
        
    def _draw_text_center(self, text, font=FONT_NORMAL, size=FONT_SIZE_M):
        self.c.setFont(font, size)
        self.c.drawCentredString(PAGE_WIDTH / 2, self.cursor_y, text)
        self._move_down(size + 2)
        
    def _draw_text_left(self, text, font=FONT_NORMAL, size=FONT_SIZE_M):
        self.c.setFont(font, size)
        self.c.drawString(self.left_margin, self.cursor_y, text)
        self._move_down(size + 1)
        
    def _draw_line(self):
        self._move_down(2)
        self.c.setDash(1, 2) 
        self.c.line(self.left_margin, self.cursor_y, self.right_margin, self.cursor_y)
        self.c.setDash([]) 
        self._move_down(5)
        
    def _draw_row(self, col1, col2, font=FONT_NORMAL, size=FONT_SIZE_M, bold_col2=False):
        self.c.setFont(font, size)
        self.c.drawString(self.left_margin, self.cursor_y, col1)
        if bold_col2: self.c.setFont(FONT_BOLD, size)
        self.c.drawRightString(self.right_margin, self.cursor_y, col2)
        self._move_down(size + 1)
        
    def _format_currency(self, amount_usd):
        amount_usd = Decimal(amount_usd)
        amount_ves = amount_usd * self.rate
        
        # Usamos .get() en config por seguridad
        mode = self.config.get('currency_display', 'VES_ONLY') if self.config else 'VES_ONLY'
        
        if mode == 'VES_ONLY':
            return f"Bs. {amount_ves:,.2f}"
        elif mode == 'DUAL':
            return f"${amount_usd:,.2f} / Bs. {amount_ves:,.2f}"
        else: 
            return f"${amount_usd:,.2f}"
    
    def generate(self):
        # Encabezado fiscal
        # Usa .get() para evitar errores si el objeto invoice no tiene atributos (si es dict)
        # Ojo: Aquí asumo que invoice es un diccionario. Si es objeto SQLAlchemy, usa getattr(self.invoice, 'attr', default)
        
        # Para simplificar, convertiremos el objeto a dict si no lo es, o usaremos getattr
        business_name = self.config.get('business_name', 'NEGOCIO DEMO') if self.config else 'NEGOCIO DEMO'
        rif = self.config.get('rif', 'J-00000000') if self.config else 'J-00000000'
        address = self.config.get('address', '') if self.config else ''
        phone = self.config.get('phone', '') if self.config else ''

        self._draw_text_center("SENIAT", FONT_BOLD, FONT_SIZE_S)
        self._draw_text_center(business_name, FONT_BOLD, FONT_SIZE_L)
        self._draw_text_center(f"RIF: {rif}", FONT_BOLD, FONT_SIZE_M)
        
        for line in textwrap.wrap(address, width=38):
            self._draw_text_center(line, FONT_SIZE_S)
        
        self._draw_line()
        self._draw_text_center(f"Telf: {phone}", FONT_SIZE_S)
        self._draw_line()
        
        # Datos Factura
        inv_num = self.invoice.get('invoice_number', '000')
        ctrl_num = self.invoice.get('control_number', f'00-{inv_num}')
        
        self._draw_text_left(f"FACTURA: {str(inv_num).zfill(8)}")
        self._draw_text_left(f"N° CONTROL: {ctrl_num}")
        
        # Fecha
        created_at = self.invoice.get('created_at')
        if created_at:
            if isinstance(created_at, str):
                 try: created_at = datetime.fromisoformat(created_at)
                 except: pass
            if isinstance(created_at, datetime):
                self._draw_text_left(f"FECHA: {created_at.strftime('%d/%m/%Y')}   HORA: {created_at.strftime('%H:%M')}")

        self._move_down(5)
        
        # Cliente
        self._draw_text_left(f"CLIENTE: {self.invoice.get('customer_name') or 'CONSUMIDOR FINAL'}")
        self._draw_text_left(f"RIF/C.I.: {self.invoice.get('customer_rif') or ''}")
        self._draw_line()

        self._draw_text_center("FACTURA", FONT_BOLD, FONT_SIZE_M)
        
        # Items
        self.c.setFont(FONT_BOLD, FONT_SIZE_S)
        self.c.drawString(self.left_margin, self.cursor_y, "DESCRIPCION")
        self.c.drawRightString(self.right_margin - (30*mm), self.cursor_y, "CANT")
        self.c.drawRightString(self.right_margin, self.cursor_y, "TOTAL")
        self._move_down(10)
        
        for item in self.items:
            self._draw_text_left(item.product_name[:30], FONT_NORMAL, FONT_SIZE_M)
            
            qty = Decimal(item.quantity)
            price = Decimal(item.unit_price)
            total = Decimal(item.total_price)
            
            math_str = f"{qty:.0f} x {self._format_currency(price)}"
            total_str = self._format_currency(total)
            
            self.c.setFont(FONT_NORMAL, FONT_SIZE_S)
            self.c.drawRightString(self.right_margin - (25*mm), self.cursor_y, math_str)
            self.c.setFont(FONT_BOLD, FONT_SIZE_M)
            self.c.drawRightString(self.right_margin, self.cursor_y, total_str)
            self._move_down(FONT_SIZE_M + 4)
        
        self._draw_line()
        
        # Totales
        total_usd = Decimal(self.invoice.get('total_amount', 0))
        
        self.c.setFont(FONT_BOLD, FONT_SIZE_L + 2)
        self.c.drawString(self.left_margin, self.cursor_y, "TOTAL A PAGAR:")
        self._move_down(FONT_SIZE_L + 4)
        
        # Mostrar Total según config
        display_total = self._format_currency(total_usd)
        self.c.setFont(FONT_BOLD, 14)
        self.c.drawRightString(self.right_margin, self.cursor_y, display_total)
        
        self._move_down(15)
        self._draw_text_center("GRACIAS POR SU COMPRA", FONT_BOLD)
        
        # Finalizar
        self.c.showPage()
        self.c.save()

# Función pública con el nombre correcto que busca main.py
def generate_invoice_pdf(invoice_data: dict, items: list, tenant_config: dict = None):
    buffer = BytesIO()
    # Pasamos config vacía si es None
    generator = FiscalTicketGenerator(buffer, invoice_data, tenant_config or {}, items)
    generator.generate()
    buffer.seek(0)
    return buffer