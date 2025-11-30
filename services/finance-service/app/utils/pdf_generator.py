from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from decimal import Decimal
from datetime import datetime
import textwrap

# --- CONFIGURACIÓN ---
# Ancho estándar de papel térmico (80mm - márgenes)
PAGE_WIDTH = 72 * mm 
MAX_HEIGHT = 2000 * mm # Altura inicial "infinita" (luego se recorta)

# Fuentes
FONT_NORMAL = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_SIZE_S = 8
FONT_SIZE_M = 9
FONT_SIZE_L = 11

class FiscalTicketGenerator:
    def __init__(self, buffer, invoice):
        self.c = canvas.Canvas(buffer, pagesize=(PAGE_WIDTH, MAX_HEIGHT))
        self.invoice = invoice
        self.y = MAX_HEIGHT - 10 # Posición vertical inicial (cursor)
        self.left_margin = 2 * mm
        self.right_margin = PAGE_WIDTH - (2 * mm)

    # --- MÉTODOS AUXILIARES DE DIBUJO ---
    
    def _move_down(self, amount):
        """Mueve el cursor hacia abajo"""
        self.y -= amount

    def _draw_text_center(self, text, size=FONT_SIZE_M, bold=False):
        """Dibuja texto centrado. Orden: Texto, Tamaño, Negrita"""
        font = FONT_BOLD if bold else FONT_NORMAL
        self.c.setFont(font, size)
        self.c.drawCentredString(PAGE_WIDTH / 2, self.y, str(text))
        self._move_down(size + 3)

    def _draw_text_left(self, text, size=FONT_SIZE_S, bold=False):
        """Dibuja texto alineado a la izquierda"""
        font = FONT_BOLD if bold else FONT_NORMAL
        self.c.setFont(font, size)
        self.c.drawString(self.left_margin, self.y, str(text))
        self._move_down(size + 3)
        
    def _draw_text_right(self, text, size=FONT_SIZE_S, bold=False):
        """Dibuja texto alineado a la derecha"""
        font = FONT_BOLD if bold else FONT_NORMAL
        self.c.setFont(font, size)
        self.c.drawRightString(self.right_margin, self.y, str(text))

    def _draw_line(self):
        """Dibuja una línea separadora punteada"""
        self._move_down(2)
        self.c.setDash(1, 2) 
        self.c.line(self.left_margin, self.y, self.right_margin, self.y)
        self.c.setDash([]) 
        self._move_down(8)

    def _safe_get(self, attr_name, default=""):
        """Obtiene un atributo del objeto invoice de forma segura"""
        val = getattr(self.invoice, attr_name, default)
        return val if val is not None else default

    # --- LÓGICA PRINCIPAL DE GENERACIÓN ---
    
    def generate(self):
        # 1. ENCABEZADO (SENIAT)
        self._draw_text_center("SENIAT", 8, True)
        self._move_down(2)
        
        # Datos Empresa
        company = self._safe_get('company_name_snapshot', 'EMPRESA DEMO')
        rif = self._safe_get('company_rif_snapshot', 'J-00000000-0')
        # Nota: Manejamos el posible typo del modelo anterior 'compant' vs 'company'
        address = getattr(self.invoice, 'company_address_snapshot', 
                          getattr(self.invoice, 'compant_address_snapshot', 'Sin dirección fiscal'))

        self._draw_text_center(company, FONT_SIZE_L, True)
        self._draw_text_center(f"RIF: {rif}", FONT_SIZE_M, True)
        
        # Dirección Multilínea
        if address:
            for line in textwrap.wrap(address, width=38):
                self._draw_text_center(line, FONT_SIZE_S)
        
        self._draw_line()
        
        # 2. DATOS FACTURA
        self._draw_text_center("FACTURA", FONT_SIZE_M, True)
        
        inv_num = str(self._safe_get('invoice_number', 0)).zfill(8)
        ctrl_num = self._safe_get('control_number', f"00-{inv_num}")
        
        self._draw_text_left(f"N° FACTURA: {inv_num}", FONT_SIZE_M, True)
        self._draw_text_left(f"N° CONTROL: {ctrl_num}", FONT_SIZE_S)
        
        # Fecha y Hora
        dt = self.invoice.created_at
        if dt:
            date_str = dt.strftime('%d-%m-%Y')
            time_str = dt.strftime('%H:%M')
            self._draw_text_left(f"FECHA: {date_str}   HORA: {time_str}")
        
        self._draw_line()
        
        # 3. DATOS CLIENTE
        cust_name = self._safe_get('customer_name', 'CONSUMIDOR FINAL')
        cust_rif = self._safe_get('customer_rif', '')
        cust_address = self._safe_get('customer_address', '')

        self._draw_text_left(f"RAZÓN SOCIAL: {cust_name}")
        self._draw_text_left(f"RIF/C.I.: {cust_rif}")
        
        if cust_address:
            self._draw_text_left("DIRECCIÓN:", FONT_SIZE_S)
            for line in textwrap.wrap(cust_address, width=38):
                self._draw_text_left(f"  {line}", FONT_SIZE_S)
                
        self._draw_line()
        
        # 4. ÍTEMS
        # Encabezado de tabla
        self.c.setFont(FONT_BOLD, 7)
        self.c.drawString(self.left_margin, self.y, "DESCRIPCION / CANT")
        self.c.drawRightString(self.right_margin, self.y, "TOTAL")
        self._move_down(10)
        
        total_base = Decimal(0)
        
        # Iterar productos
        for item in self.invoice.items:
            # Nombre producto (wrapppeado)
            name_lines = textwrap.wrap(item.product_name, width=28)
            
            # Primera línea: Nombre
            self._draw_text_left(name_lines[0], FONT_SIZE_S)
            
            # Líneas extra del nombre
            for line in name_lines[1:]:
                self._draw_text_left(line, FONT_SIZE_S)
                
            # Detalles: Cantidad x Precio
            qty = Decimal(item.quantity)
            price = Decimal(item.unit_price)
            total_line = Decimal(item.total_price)
            
            # Usamos cursor manual para poner precio a la derecha en la misma línea
            # Subimos un poco porque _draw_text_left bajó el cursor
            self.y += (FONT_SIZE_S + 1) 
            
            detail_text = f"   {qty:.2f} x ${price:,.2f}"
            
            self.c.setFont(FONT_NORMAL, 8)
            self.c.drawString(self.left_margin, self.y, detail_text)
            
            self.c.setFont(FONT_BOLD, 9)
            self.c.drawRightString(self.right_margin, self.y, f"${total_line:,.2f}")
            
            self._move_down(12) # Espacio para el siguiente ítem

        self._draw_line()
        
        # 5. TOTALES
        # Subtotal
        total_usd = Decimal(self._safe_get('total_usd', 0))
        # Asumimos que tax_amount ya viene calculado o es 0
        tax = Decimal(self._safe_get('tax_amount_usd', 0))
        subtotal = total_usd - tax

        self.c.setFont(FONT_NORMAL, 9)
        self.c.drawString(self.right_margin - 40*mm, self.y, "SUBTOTAL:")
        self.c.drawRightString(self.right_margin, self.y, f"${subtotal:,.2f}")
        self._move_down(12)
        
        if tax > 0:
            self.c.drawString(self.right_margin - 40*mm, self.y, "I.V.A (16%):")
            self.c.drawRightString(self.right_margin, self.y, f"${tax:,.2f}")
            self._move_down(12)

        # GRAN TOTAL USD
        self.c.setFont(FONT_BOLD, 12)
        self.c.drawString(self.left_margin, self.y, "TOTAL A PAGAR:")
        self.c.drawRightString(self.right_margin, self.y, f"${total_usd:,.2f}")
        self._move_down(18)
        
        # TOTAL EN BOLIVARES (DUAL)
        amount_ves = self._safe_get('amount_ves')
        if amount_ves:
            ves_val = Decimal(amount_ves)
            self.c.setFont(FONT_BOLD, 11)
            self.c.drawString(self.left_margin, self.y, "TOTAL BS:")
            self.c.drawRightString(self.right_margin, self.y, f"Bs {ves_val:,.2f}")
            self._move_down(12)
            
            # Tasa
            rate = self._safe_get('exchange_rate', 0)
            self._draw_text_center(f"(Tasa de Cambio: {rate:,.2f})", 8)

        self._draw_line()
        self._draw_text_center("SIN DERECHO A CRÉDITO FISCAL", 8, True)
        self._draw_text_center("(Representación Gráfica)", 7)
        
        # --- CIERRE Y RECORTE ---
        self.c.showPage()
        
        # Truco: Calcular altura usada para recortar la página
        # MAX_HEIGHT (2000) - self.y (donde quedó el cursor) + margen
        final_height = MAX_HEIGHT - self.y + (10*mm)
        
        self.c.setPageSize((PAGE_WIDTH, final_height))
        # Mover contenido al nuevo origen
        self.c.translate(0, final_height - MAX_HEIGHT)
        
        self.c.save()

# --- FUNCIÓN DE ENTRADA ---
def generate_invoice_pdf(invoice_data, items):
    """
    Genera un PDF en memoria.
    invoice_data: Objeto Invoice de SQLAlchemy (con atributos).
    items: Lista de InvoiceItems.
    """
    buffer = BytesIO()
    # Aseguramos que el objeto invoice tenga la lista de items accesible
    invoice_data.items = items 
    
    generator = FiscalTicketGenerator(buffer, invoice_data)
    generator.generate()
    
    buffer.seek(0)
    return buffer