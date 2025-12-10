from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
from datetime import date

class FinancialReportGenerator:
    def __init__(self, company_name: str, rif: str):
        self.company_name = company_name
        self.rif = rif
        self.styles = getSampleStyleSheet()
        self.elements = []
        
        # Estilos personalizados
        self.style_title = ParagraphStyle('Title', parent=self.styles['Heading1'], alignment=1, fontSize=14)
        self.style_subtitle = ParagraphStyle('Subtitle', parent=self.styles['Normal'], alignment=1, fontSize=10)
        self.style_header_table = ParagraphStyle('HeaderTable', parent=self.styles['Normal'], fontSize=9, fontName='Helvetica-Bold')
        self.style_cell_normal = ParagraphStyle('Cell', parent=self.styles['Normal'], fontSize=9)
        self.style_cell_total = ParagraphStyle('CellTotal', parent=self.styles['Normal'], fontSize=9, fontName='Helvetica-Bold')

    def _add_header(self, title: str, period_desc: str):
        self.elements.append(Paragraph(self.company_name.upper(), self.style_title))
        self.elements.append(Paragraph(f"RIF: {self.rif}", self.style_subtitle))
        self.elements.append(Spacer(1, 0.1 * inch))
        self.elements.append(Paragraph(title.upper(), self.style_title))
        self.elements.append(Paragraph(period_desc, self.style_subtitle))
        self.elements.append(Paragraph("(Expresado en Dólares Americanos)", self.style_subtitle))
        self.elements.append(Spacer(1, 0.3 * inch))

    def _add_signatures(self):
        self.elements.append(Spacer(1, 0.8 * inch))
        data = [["_______________________", "_______________________"],
                ["Elaborado por (Contador)", "Aprobado por (Gerencia)"]]
        t = Table(data, colWidths=[3.5 * inch, 3.5 * inch])
        t.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
        self.elements.append(t)

    def generate_balance_sheet(self, data: list, end_date: date):
        """Estado de Situación Financiera"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=LETTER)
        
        self._add_header("Estado de Situación Financiera", f"Al {end_date.strftime('%d-%m-%Y')}")
        
        # Filtrar Activos, Pasivos y Patrimonio
        table_data = [["CÓDIGO", "CUENTA", "NOTAS", "SALDO"]]
        
        # Grupos grandes
        assets = [x for x in data if x['type'] == 'ASSET']
        liabilities = [x for x in data if x['type'] == 'LIABILITY']
        equity = [x for x in data if x['type'] == 'EQUITY']
        
        def add_section(accounts, section_name):
            if not accounts: return
            # Título de sección
            table_data.append([section_name, "", "", ""]) 
            for acc in accounts:
                # Indentación visual según nivel
                indent = "&nbsp;" * ((acc['level'] - 1) * 4)
                name = Paragraph(f"{indent}{acc['name']}", self.style_cell_normal)
                
                # Formato de moneda
                bal = "{:,.2f}".format(acc['balance'])
                
                # Negrita para totales (Nivel 1 y 2)
                style = self.style_cell_normal
                if acc['level'] <= 2:
                    name = Paragraph(f"{indent}{acc['name']}", self.style_cell_total)
                
                table_data.append([acc['code'], name, "", bal])

        add_section(assets, "ACTIVOS")
        add_section(liabilities, "PASIVOS")
        add_section(equity, "PATRIMONIO")

        # Totalizar (Ecuación Patrimonial)
        total_assets = sum(a['balance'] for a in assets if a['level'] == 1)
        total_liab_eq = sum(l['balance'] for l in liabilities if l['level'] == 1) + \
                        sum(e['balance'] for e in equity if e['level'] == 1)
        
        table_data.append(["", "TOTAL ACTIVO", "", "{:,.2f}".format(total_assets)])
        table_data.append(["", "TOTAL PASIVO Y PATRIMONIO", "", "{:,.2f}".format(total_liab_eq)])

        # Estilo de Tabla
        t = Table(table_data, colWidths=[1.2*inch, 3.5*inch, 0.6*inch, 1.5*inch])
        t.setStyle(TableStyle([
            ('LINEBELOW', (0,0), (-1,0), 1, colors.black),
            ('ALIGN', (-1,0), (-1,-1), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTNAME', (0,-2), (-1,-1), 'Helvetica-Bold'), # Totales en negrita
            ('LINEABOVE', (0,-2), (-1,-1), 1, colors.black),
        ]))
        
        self.elements.append(t)
        self._add_signatures()
        
        doc.build(self.elements)
        buffer.seek(0)
        return buffer

    def generate_income_statement(self, data: list, start_date: date, end_date: date):
        """Estado de Resultados (Ganancias y Pérdidas)"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=LETTER)
        
        self._add_header("Estado de Resultados", f"Del {start_date.strftime('%d-%m-%Y')} al {end_date.strftime('%d-%m-%Y')}")
        
        table_data = [["CUENTA", "SALDO"]]
        
        revenue = [x for x in data if x['type'] == 'REVENUE']
        costs = [x for x in data if x['type'] == 'EXPENSE' and x['code'].startswith('5')]
        expenses = [x for x in data if x['type'] == 'EXPENSE' and x['code'].startswith('6')]

        total_rev = sum(x['balance'] for x in revenue if x['level'] == 1)
        total_cost = sum(x['balance'] for x in costs if x['level'] == 1)
        total_exp = sum(x['balance'] for x in expenses if x['level'] == 1)
        
        gross_profit = total_rev - total_cost
        net_profit = gross_profit - total_exp

        # Llenar tabla
        for group, name in [(revenue, "INGRESOS"), (costs, "COSTOS"), (expenses, "GASTOS")]:
            table_data.append([Paragraph(f"<b>{name}</b>", self.style_cell_normal), ""])
            for acc in group:
                indent = "&nbsp;" * ((acc['level'] - 1) * 4)
                acc_name = Paragraph(f"{indent}{acc['name']}", self.style_cell_normal)
                table_data.append([acc_name, "{:,.2f}".format(acc['balance'])])
        
        # Resultados Finales
        table_data.append([Paragraph("<b>UTILIDAD BRUTA</b>", self.style_cell_total), "{:,.2f}".format(gross_profit)])
        table_data.append([Paragraph("<b>UTILIDAD NETA DEL EJERCICIO</b>", self.style_cell_total), "{:,.2f}".format(net_profit)])

        t = Table(table_data, colWidths=[4.5*inch, 2.0*inch])
        t.setStyle(TableStyle([
            ('LINEBELOW', (0,0), (-1,0), 1, colors.black),
            ('ALIGN', (-1,0), (-1,-1), 'RIGHT'),
        ]))
        
        self.elements.append(t)
        self._add_signatures()
        
        doc.build(self.elements)
        buffer.seek(0)
        return buffer