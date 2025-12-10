from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
from datetime import date

class FinancialReportGenerator:
    def __init__(self, company_name: str, rif: str):
        self.company_name = company_name or "EMPRESA DEMO C.A."
        self.rif = rif or "J-00000000-0"
        self.styles = getSampleStyleSheet()
        self.elements = []
        
        # Estilos Corporativos
        self.style_title = ParagraphStyle('Title', parent=self.styles['Heading1'], alignment=1, fontSize=14, spaceAfter=6)
        self.style_subtitle = ParagraphStyle('Subtitle', parent=self.styles['Normal'], alignment=1, fontSize=10)
        self.style_cell_normal = ParagraphStyle('Cell', parent=self.styles['Normal'], fontSize=9)
        self.style_cell_total = ParagraphStyle('CellTotal', parent=self.styles['Normal'], fontSize=9, fontName='Helvetica-Bold')
        self.style_cell_bold = ParagraphStyle('CellBold', parent=self.styles['Normal'], fontSize=9, fontName='Helvetica-Bold')

    def _add_header(self, title: str, period_desc: str):
        """Encabezado Oficial según Normas"""
        self.elements.append(Paragraph(self.company_name.upper(), self.style_title))
        self.elements.append(Paragraph(f"RIF: {self.rif}", self.style_subtitle))
        self.elements.append(Spacer(1, 0.1 * inch))
        self.elements.append(Paragraph(title.upper(), self.style_title))
        self.elements.append(Paragraph(period_desc, self.style_subtitle))
        self.elements.append(Paragraph("(Expresado en Dólares de los Estados Unidos de América)", self.style_subtitle))
        self.elements.append(Spacer(1, 0.3 * inch))

    def _add_signatures(self):
        """Firmas Legales (Contador y Representante Legal)"""
        self.elements.append(Spacer(1, 0.8 * inch))
        data = [
            ["_______________________", "_______________________"],
            ["ELABORADO POR:", "APROBADO POR:"],
            ["CONTADOR PÚBLICO", "GERENTE GENERAL"],
            ["C.P.C. ____________", ""]
        ]
        t = Table(data, colWidths=[3.5 * inch, 3.5 * inch])
        t.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 10),
        ]))
        self.elements.append(t)

    def _create_standard_table(self, data, cols_width):
        t = Table(data, colWidths=cols_width)
        t.setStyle(TableStyle([
            ('ALIGN', (-1,0), (-1,-1), 'RIGHT'), # Montos a la derecha
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), # Header negrita
            ('LINEBELOW', (0,0), (-1,0), 1, colors.black), # Línea header
        ]))
        return t

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
    
    def generate_equity_changes(self, data: list, start_date: date, end_date: date):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=LETTER)
        
        self._add_header("Estado de Cambios en el Patrimonio", f"Del {start_date} al {end_date}")
        
        # Filtramos solo cuentas de Patrimonio (Grupo 3) de Nivel 3 o 4 (Movimiento)
        equity_accs = [x for x in data if x['code'].startswith('3') and x['level'] >= 3]
        
        table_data = [["CUENTA PATRIMONIAL", "SALDO FINAL"]]
        total_equity = 0
        
        for acc in equity_accs:
            table_data.append([
                Paragraph(acc['name'], self.style_cell_normal),
                "{:,.2f}".format(acc['balance'])
            ])
            total_equity += acc['balance']
            
        # Total
        table_data.append([
            Paragraph("<b>TOTAL PATRIMONIO AL CIERRE</b>", self.style_cell_total),
            Paragraph(f"<b>{'{:,.2f}'.format(total_equity)}</b>", self.style_cell_total)
        ])
        
        t = self._create_standard_table(table_data, [5.0*inch, 1.5*inch])
        self.elements.append(t)
        self._add_signatures()
        
        doc.build(self.elements)
        buffer.seek(0)
        return buffer

    def generate_cash_flow(self, balance_data: list, income_data: list, start_date: date, end_date: date):
        """
        Genera Flujo de Efectivo basado en variaciones.
        Requiere datos de: Resultado del periodo + Variaciones de Activos/Pasivos.
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=LETTER)
        self._add_header("Estado de Flujos de Efectivo", f"Del {start_date} al {end_date}")
        
        # 1. Obtener Resultado del Ejercicio (Utilidad/Pérdida)
        revenue = sum(x['balance'] for x in income_data if x['code'].startswith('4'))
        expenses = sum(x['balance'] for x in income_data if x['code'].startswith(('5', '6')))
        net_income = revenue - expenses
        
        table_data = [["CONCEPTO", "PARCIAL", "TOTAL"]]
        
        # --- ACTIVIDADES DE OPERACIÓN ---
        table_data.append([Paragraph("<b>ACTIVIDADES DE OPERACIÓN</b>", self.style_cell_bold), "", ""])
        table_data.append([Paragraph("Utilidad (Pérdida) del Ejercicio", self.style_cell_normal), "", "{:,.2f}".format(net_income)])
        
        # Ajustes por partidas que no afectan efectivo (Depreciación)
        # Buscamos cuentas de gasto '6.04' (Depreciaciones)
        depreciation = sum(x['balance'] for x in income_data if x['code'].startswith('6.04'))
        if depreciation > 0:
            table_data.append([Paragraph("Más: Cargos por Depreciación", self.style_cell_normal), "{:,.2f}".format(depreciation), ""])
        
        # Cambios en Capital de Trabajo (Simplificado: Usamos saldos finales como variación por ser primer año)
        # En un sistema maduro, esto sería (Saldo Final - Saldo Inicial)
        # Nota: Aumento de Activo RESTA, Aumento de Pasivo SUMA.
        
        # Cuentas por Cobrar (1.01.02 y 1.01.03) -> Aumento RESTA efectivo
        receivables = sum(x['balance'] for x in balance_data if x['code'].startswith(('1.01.02', '1.01.03')))
        if receivables > 0:
            table_data.append([Paragraph("(Aumento) en Cuentas por Cobrar", self.style_cell_normal), f"({'{:,.2f}'.format(receivables)})", ""])
            
        # Inventarios (1.01.05) -> Aumento RESTA
        inventory = sum(x['balance'] for x in balance_data if x['code'].startswith('1.01.05'))
        if inventory > 0:
            table_data.append([Paragraph("(Aumento) en Inventarios", self.style_cell_normal), f"({'{:,.2f}'.format(inventory)})", ""])

        # Cuentas por Pagar (2.01) -> Aumento SUMA
        payables = sum(x['balance'] for x in balance_data if x['code'].startswith('2.01'))
        if payables > 0:
            table_data.append([Paragraph("Aumento en Cuentas por Pagar", self.style_cell_normal), "{:,.2f}".format(payables), ""])

        # Flujo Neto Operación
        # Fórmula: Utilidad + Depreciación - CxC - Inv + CxP
        net_cash_op = net_income + depreciation - receivables - inventory + payables
        table_data.append([Paragraph("<b>Efectivo Neto de Actividades de Operación</b>", self.style_cell_total), "", "{:,.2f}".format(net_cash_op)])
        
        # --- ACTIVIDADES DE INVERSIÓN ---
        # Compra de Activo Fijo (1.02) -> Salida de dinero
        fixed_assets = sum(x['balance'] for x in balance_data if x['code'].startswith('1.02') and not x['code'].startswith('1.02.01.004')) # Excluir Deprec. Acumulada
        table_data.append([Paragraph("<b>ACTIVIDADES DE INVERSIÓN</b>", self.style_cell_bold), "", ""])
        if fixed_assets > 0:
            table_data.append([Paragraph("Adquisición de Propiedad, Planta y Equipo", self.style_cell_normal), "", f"({'{:,.2f}'.format(fixed_assets)})"])
        
        # --- RESUMEN ---
        net_increase = net_cash_op - fixed_assets
        table_data.append([Spacer(1, 0.2*inch), "", ""])
        table_data.append([Paragraph("<b>AUMENTO (DISMINUCIÓN) NETO DE EFECTIVO</b>", self.style_cell_total), "", "{:,.2f}".format(net_increase)])
        
        # Saldo Caja y Bancos (1.01.01)
        cash_balance = sum(x['balance'] for x in balance_data if x['code'].startswith('1.01.01'))
        table_data.append([Paragraph("<b>EFECTIVO AL FINAL DEL PERIODO</b>", self.style_cell_total), "", "{:,.2f}".format(cash_balance)])

        t = self._create_standard_table(table_data, [3.5*inch, 1.5*inch, 1.5*inch])
        self.elements.append(t)
        self._add_signatures()
        
        doc.build(self.elements)
        buffer.seek(0)
        return buffer