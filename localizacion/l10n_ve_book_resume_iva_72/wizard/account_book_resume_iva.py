# -*- coding: utf-8 -*-

from odoo import fields, models
from datetime import datetime, timedelta
from io import BytesIO
import logging
import xlwt
import base64
_logger = logging.getLogger(__name__)


class AccountBookResumeIva(models.TransientModel):
    _name = 'account.book.resume.iva'
    _description = 'Book 72'
    _rec_name = 'id'

    f_inicio = fields.Date("Fecha de inicio", required=True, copy=False,
                           default=lambda *a: datetime.now().strftime('%Y-%m-%d'))
    f_fin = fields.Date("Fecha final", required=True, copy=False,
                        default=lambda *a: (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'))
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id.id)

    def amount_total_retention_iva(self):
        start_time = datetime.now()
        total_ret_iva = 0.0
        desde = fields.Date.from_string(self.f_inicio)
        hasta = fields.Date.from_string(self.f_fin)
        query = """
            SELECT total_ret_iva FROM alicuota
            WHERE date_voucher BETWEEN '%s' AND '%s'
            AND move_type in ('out_invoice','out_refund','out_receipt')
            AND retention_iva_state = 'done'
        """ % (desde, hasta)
        self._cr.execute(query)
        obj_query = self._cr.dictfetchall()
        for book in obj_query:
            total_ret_iva += book['total_ret_iva']
        end_time = datetime.now()
        _logger.info(">> ({}) {}: {}  | {}: {}".format(
            'amount_total_retention_iva',
            'Hora de Inicio', start_time,
            'Tiempo de ejecucion', end_time - start_time))
        return total_ret_iva

    def fiscal_debit(self):
        start_time = datetime.now()
        desde = fields.Date.from_string(self.f_inicio)
        hasta = fields.Date.from_string(self.f_fin)
        query = """
            SELECT
            move_id,
            currency_id,
            base_general,
            ali_general,
            base_additional,
            ali_additional,
            base_reduced,
            ali_reduced,
            total_exempt
            FROM alicuota
            WHERE date_invoice BETWEEN '%s' AND '%s'
            AND move_type in ('out_invoice','out_refund','out_receipt')
            AND state = 'posted'
        """ % (desde, hasta)
        self._cr.execute(query)
        obj_query = self._cr.dictfetchall()
        total_exento = 0.0
        total_base_general = 0.0
        alicuota_general = 0.0
        base_adicional = 0.0
        alicuota_adicional = 0.0
        base_reducida = 0.0
        alicuota_reducida = 0.0
        for book in obj_query:
            total_exento += self.amount_rate(book['total_exempt'], book['currency_id'], book['move_id'])
            total_base_general += self.amount_rate(book['base_general'], book['currency_id'], book['move_id'])
            alicuota_general += self.amount_rate(book['ali_general'], book['currency_id'], book['move_id'])
            base_adicional += self.amount_rate(book['base_additional'], book['currency_id'], book['move_id'])
            alicuota_adicional += self.amount_rate(book['ali_additional'], book['currency_id'], book['move_id'])
            base_reducida += self.amount_rate(book['base_reduced'], book['currency_id'], book['move_id'])
            alicuota_reducida += self.amount_rate(book['ali_reduced'], book['currency_id'], book['move_id'])
        end_time = datetime.now()
        _logger.info(">> ({}) {}: {}  | {}: {}".format(
            'fiscal_debit',
            'Hora de Inicio', start_time,
            'Tiempo de ejecucion', end_time - start_time))
        return {
            'total_exento': total_exento,
            'total_base_general': total_base_general,
            'alicuota_general': alicuota_general,
            'base_adicional': base_adicional,
            'alicuota_adicional': alicuota_adicional,
            'base_reducida': base_reducida,
            'alicuota_reducida': alicuota_reducida

        }

    def fiscal_credit(self):
        start_time = datetime.now()
        desde = fields.Date.from_string(self.f_inicio)
        hasta = fields.Date.from_string(self.f_fin)
        query = """
            SELECT
            move_id,
            currency_id,
            base_general,
            ali_general,
            base_additional,
            ali_additional,
            base_reduced,
            ali_reduced,
            total_exempt
            FROM alicuota
            WHERE date_invoice BETWEEN '%s' AND '%s'
            AND move_type in ('in_invoice','in_refund','in_receipt')
            AND state = 'posted'
        """ % (desde, hasta)
        self._cr.execute(query)
        obj_query = self._cr.dictfetchall()
        total_exento = 0.0
        total_base_general = 0.0
        alicuota_general = 0.0
        base_adicional = 0.0
        alicuota_adicional = 0.0
        base_reducida = 0.0
        alicuota_reducida = 0.0
        for book in obj_query:
            total_exento += self.amount_rate(book['total_exempt'], book['currency_id'], book['move_id'])
            total_base_general += self.amount_rate(book['base_general'], book['currency_id'], book['move_id'])
            alicuota_general += self.amount_rate(book['ali_general'], book['currency_id'], book['move_id'])
            base_adicional += self.amount_rate(book['base_additional'], book['currency_id'], book['move_id'])
            alicuota_adicional += self.amount_rate(book['ali_additional'], book['currency_id'], book['move_id'])
            base_reducida += self.amount_rate(book['base_reduced'], book['currency_id'], book['move_id'])
            alicuota_reducida += self.amount_rate(book['ali_reduced'], book['currency_id'], book['move_id'])
        end_time = datetime.now()
        _logger.info(">> ({}) {}: {}  | {}: {}".format(
            'fiscal_credit',
            'Hora de Inicio', start_time,
            'Tiempo de ejecucion', end_time - start_time))
        return {
            'total_exento': total_exento,
            'total_base_general': total_base_general,
            'alicuota_general': alicuota_general,
            'base_adicional': base_adicional,
            'alicuota_adicional': alicuota_adicional,
            'base_reducida': base_reducida,
            'alicuota_reducida': alicuota_reducida

        }

    def amount_rate(self, amount, currency_id, move_id):
        total = 0.0
        result = 0.0
        if currency_id != self.company_id.currency_id.id:
            obj_move = self.env['account.move'].search([('id', '=', move_id)], order="id asc")
            for move in obj_move:
                total += abs(move.amount_untaxed / move.amount_untaxed_signed)
            rate = round(total, 3)
            result += amount * rate
        else:
            result += amount
        return result

    def generate_xls_report(self):
        start_time = datetime.now()
        wb1 = xlwt.Workbook(encoding='utf-8')
        ws1 = wb1.add_sheet('Resumen')
        fp = BytesIO()
        diccionario = self.fiscal_debit()
        diccionario2 = self.fiscal_credit()
        total_ret = self.amount_total_retention_iva()
        header_content_style = xlwt.easyxf("font: name Helvetica size 20 px, bold 1, height 170;")
        header_content_style_c = xlwt.easyxf("font: name Helvetica size 20 px, bold 1, height 170; align: horiz center")
        sub_header_style = xlwt.easyxf(
            "font: name Helvetica size 10 px, bold 1, height 170; borders: left thin, right thin,"
            "top thin, bottom thin;")

        sub_header_style_c = xlwt.easyxf(
            "font: name Helvetica size 10 px, bold 1, height 170; borders: left thin, right thin,"
            "top thin, bottom thin; align: horiz center")

        sub_header_style_r = xlwt.easyxf(
            "font: name Helvetica size 10 px, bold 1, height 170; borders: left thin, right thin, top thin,"
            "bottom thin; align: horiz right")

        header_style = xlwt.easyxf(
            "font: name Helvetica size 10 px, height 170; borders: left thin, right thin, top thin, bottom thin;")

        header_style_c = xlwt.easyxf(
            "font: name Helvetica size 10 px, height 170; borders: left thin, right thin, top thin,"
            "bottom thin; align: horiz center")

        header_style_r = xlwt.easyxf(
            "font: name Helvetica size 10 px, height 170; borders: left thin, right thin,"
            "top thin, bottom thin; align: horiz right")

        # sub_header_content_style = xlwt.easyxf("font: name Helvetica size 10 px, height 170;")
        # line_content_style = xlwt.easyxf("font: name Helvetica, height 170;")
        row = 0
        # col = 0
        ws1.row(row).height = 500
        ws1.write_merge(row, row, 4, 9, "Raz??n Social:" + " " + str(self.company_id.name), sub_header_style)
        row += 1
        ws1.write_merge(row, row, 4, 9, "Rif:" + " " + str(self.company_id.partner_id.doc_type.upper()) + str(
            self.company_id.partner_id.vat), sub_header_style)
        row += 1
        ws1.write_merge(row, row, 4, 9, "Resumen de IVA", sub_header_style_c)
        row += 1
        ws1.write_merge(row, row, 4, 4, "Periodo", header_content_style)
        ws1.write_merge(row, row, 5, 5, self.f_fin.strftime("%m-%Y"), header_content_style)
        ws1.write_merge(row, row, 6, 6, "Desde:", header_content_style_c)
        ws1.write_merge(row, row, 7, 7, self.f_inicio, header_content_style)
        ws1.write_merge(row, row, 8, 8, "Hasta:", header_content_style_c)
        ws1.write_merge(row, row, 9, 9, self.f_fin, header_content_style)
        # Debitos Fiscales
        row += 2
        ws1.write_merge(row, row, 4, 7, "D??BITOS FISCALES", sub_header_style)
        ws1.write_merge(row, row, 8, 8, "BASE IMPONIBLE", sub_header_style)
        ws1.write_merge(row, row, 9, 9, "D??BITO FISCAL", sub_header_style)
        row += 1
        ws1.write_merge(row, row, 4, 4, (row - 5), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Ventas Internas no Gravadas", header_style)
        ws1.write_merge(row, row, 8, 8, diccionario['total_exento'], header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row += 1
        ws1.write_merge(row, row, 4, 4, (row - 5), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Ventas de Exportaci??n", header_style)
        ws1.write_merge(row, row, 8, 8, "0,00", header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row += 1
        ws1.write_merge(row, row, 4, 4, (row - 5), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Ventas Internas Gravadas por Alicuota General", header_style)
        ws1.write_merge(row, row, 8, 8, diccionario['total_base_general'], header_style_r)
        ws1.write_merge(row, row, 9, 9, diccionario['alicuota_general'], header_style_r)
        row += 1
        ws1.write_merge(row, row, 4, 4, (row - 5), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Ventas Internas Gravadas por Alicuota General m??s Adicional", header_style)
        ws1.write_merge(row, row, 8, 8, diccionario['base_adicional'], header_style_r)
        ws1.write_merge(row, row, 9, 9, diccionario['alicuota_adicional'], header_style_r)
        row += 1
        ws1.write_merge(row, row, 4, 4, (row - 5), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Ventas Internas Gravadas por Alicuota Reducida", header_style)
        ws1.write_merge(row, row, 8, 8, diccionario['base_reducida'], header_style_r)
        ws1.write_merge(row, row, 9, 9, diccionario['alicuota_reducida'], header_style_r)
        sub_total1 = diccionario['total_exento'] + diccionario['total_base_general'] + diccionario['base_adicional'] + \
            diccionario['base_reducida']
        sub_total11 = diccionario['alicuota_general'] + diccionario['alicuota_adicional'] +\
            diccionario['alicuota_reducida']
        row += 1
        ws1.write_merge(row, row, 4, 4, (row - 5), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Total Ventas y Debitos Fiscales para Efectos de Determinaci??n", header_style)
        ws1.write_merge(row, row, 8, 8, sub_total1, header_style_r)
        ws1.write_merge(row, row, 9, 9, sub_total11, header_style_r)
        row += 1
        ws1.write_merge(row, row, 4, 4, (row-5), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Ajustes a los D??bitos Fiscales de Periodos Anteriores.", header_style)
        ws1.write_merge(row, row, 8, 8, "---", header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row += 1
        ws1.write_merge(row, row, 4, 4, (row-5), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Certificados de D??bitos Fiscales Exonerados", header_style)
        ws1.write_merge(row, row, 8, 8, "---", header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row += 1
        ws1.write_merge(row, row, 4, 4, (row - 5), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Total D??bitos Fiscales:", sub_header_style)
        ws1.write_merge(row, row, 8, 8, "---", sub_header_style_r)
        ws1.write_merge(row, row, 9, 9, sub_total11, sub_header_style_r)

        # Creditos Fiscales
        row += 1
        ws1.write_merge(row, row, 4, 7, "CR??DITO FISCALES", sub_header_style)
        ws1.write_merge(row, row, 8, 8, "BASE IMPONIBLE", sub_header_style)
        ws1.write_merge(row, row, 9, 9, "CR??DITO FISCAL", sub_header_style)
        row += 1
        ws1.write_merge(row, row, 4, 4, (row - 6), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Compras no Gravadas y/o sin Derecho a Credito Fiscal", header_style)
        ws1.write_merge(row, row, 8, 8, diccionario2['total_exento'], header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row += 1
        ws1.write_merge(row, row, 4, 4, (row - 6), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Importaciones No Gravadas", header_style)
        ws1.write_merge(row, row, 8, 8, "0,00", header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row += 1
        ws1.write_merge(row, row, 4, 4, (row - 6), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Importaciones Gravadas por Alicuota General", header_style)
        ws1.write_merge(row, row, 8, 8, "0,00", header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row += 1
        ws1.write_merge(row, row, 4, 4, (row - 6), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Importaciones Gravadas por Alicuota General m??s Alicuota Adicional",
                        header_style)
        ws1.write_merge(row, row, 8, 8, "0,00", header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row += 1
        ws1.write_merge(row, row, 4, 4, (row - 6), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Importaciones Gravadas por Alicuota Reducida", header_style)
        ws1.write_merge(row, row, 8, 8, "0,00", header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row += 1
        ws1.write_merge(row, row, 4, 4, (row - 6), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Compras Gravadas por Alicuota General", header_style)
        ws1.write_merge(row, row, 8, 8, diccionario2['total_base_general'], header_style_r)
        ws1.write_merge(row, row, 9, 9, diccionario2['alicuota_general'], header_style_r)
        row += 1
        ws1.write_merge(row, row, 4, 4, (row - 6), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Compras Gravadas por Alicuota General m??s Alicuota Adicional", header_style)
        ws1.write_merge(row, row, 8, 8, diccionario2['base_adicional'], header_style_r)
        ws1.write_merge(row, row, 9, 9, diccionario2['alicuota_adicional'], header_style_r)
        row += 1
        ws1.write_merge(row, row, 4, 4, (row - 6), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Compras Gravadas por Alicuota Reducida", header_style)
        ws1.write_merge(row, row, 8, 8, diccionario2['base_reducida'], header_style_r)
        ws1.write_merge(row, row, 9, 9, diccionario2['alicuota_reducida'], header_style_r)
        row += 1
        sub_total2 = diccionario2['total_exento'] + diccionario2['total_base_general'] + diccionario2[
            'base_adicional'] + diccionario2['base_reducida']
        sub_total22 = diccionario2['alicuota_general'] + diccionario2['alicuota_adicional'] + diccionario2[
            'alicuota_reducida']
        ws1.write_merge(row, row, 4, 4, (row - 6), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Total Compras y Cr??ditos Fiscales del Per??odo", header_style)
        ws1.write_merge(row, row, 8, 8, sub_total2, header_style_r)
        ws1.write_merge(row, row, 9, 9, sub_total22, header_style_r)

        row += 1
        ws1.write_merge(row, row, 4, 9, "CALCULO DEL CREDITO DEDUCIBLE", sub_header_style)
        # ws1.write_merge(row,row, 8, 8, "BASE IMPONIBLE",sub_header_style)
        # ws1.write_merge(row,row, 9, 9, "CR??DITO FISCAL",sub_header_style)
        row += 1
        ws1.write_merge(row, row, 4, 4, (row - 6), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Creditos Fiscales Totalmente Deducibles ", header_style)
        ws1.write_merge(row, row, 8, 8, "0,00", header_style_r)
        ws1.write_merge(row, row, 9, 9, sub_total22, header_style_r)
        row += 1
        ws1.write_merge(row, row, 4, 4, (row - 6), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Cr??ditos Fiscales Producto de la Aplicaci??n del Porcentaje de la Prorrata",
                        header_style)
        ws1.write_merge(row, row, 8, 8, "0,00", header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row += 1
        ws1.write_merge(row, row, 4, 4, (row - 6), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Total Cr??ditos Fiscales Deducibles", header_style)
        ws1.write_merge(row, row, 8, 8, "0,00", header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row += 1
        ws1.write_merge(row, row, 4, 4, (row - 6), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Exedente Cr??ditos Fiscales del Semana Anterior ", header_style)
        ws1.write_merge(row, row, 8, 8, "0,00", header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row += 1
        ws1.write_merge(row, row, 4, 4, (row - 6), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Reintegro Solicitado (s??lo exportadores)", header_style)
        ws1.write_merge(row, row, 8, 8, "0,00", header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row += 1
        ws1.write_merge(row, row, 4, 4, (row - 6), header_style_c)
        ws1.write_merge(row, row, 5, 7,
                        "Reintegro (s??lo quien suministre bienes o presten servicios a entes exonerados)", header_style)
        ws1.write_merge(row, row, 8, 8, "0,00", header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row += 1
        ws1.write_merge(row, row, 4, 4, (row - 6), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Ajustes a los Cr??ditos Fiscales de Periodos Anteriores.", header_style)
        ws1.write_merge(row, row, 8, 8, "0,00", header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row += 1
        ws1.write_merge(row, row, 4, 4, (row - 6), header_style_c)
        ws1.write_merge(row, row, 5, 7,
                        "Certificados de D??bitos Fiscales Exonerados (emitidos de entes exonerados)"
                        "Registrados en el periodo",
                        header_style)
        ws1.col(5).width = int(
            len('Certificados de D??bitos Fiscales Exonerados (emitidos de entes exonerados)'
                'Registrados en el periodo') * 128)
        ws1.write_merge(row, row, 8, 8, "0,00", header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row += 1
        ws1.write_merge(row, row, 4, 4, (row - 6), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Total Creditos Fiscales:", sub_header_style)
        ws1.write_merge(row, row, 8, 8, "0,00", sub_header_style_r)
        ws1.write_merge(row, row, 9, 9, sub_total22, sub_header_style_r)

        row += 1
        ws1.write_merge(row, row, 4, 9, "AUTOLIQUIDACI??N", sub_header_style)
        # ws1.write_merge(row,row, 8, 8, "BASE IMPONIBLE",sub_header_style)
        # ws1.write_merge(row,row, 9, 9, "CR??DITO FISCAL",sub_header_style)
        row += 1
        resultado27 = 0
        resultado28 = 0
        if sub_total11 > sub_total22:
            resultado27 += sub_total11 - sub_total22
        if sub_total22 > sub_total11:
            resultado28 += sub_total22 - sub_total11
        ws1.write_merge(row, row, 4, 4, (row - 7), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Total Cuota Tributaria del Per??odo.", header_style)
        ws1.write_merge(row, row, 8, 8, "---", header_style_r)
        ws1.write_merge(row, row, 9, 9, resultado27, header_style_r)
        row = row + 1
        ws1.write_merge(row, row, 4, 4, (row - 7), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Exedente de Cr??dito Fiscal para el mes Siguiente.", header_style)
        ws1.write_merge(row, row, 8, 8, "---", header_style_r)
        ws1.write_merge(row, row, 9, 9, resultado28, header_style_r)
        row = row + 1
        ws1.write_merge(row, row, 4, 4, (row - 7), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Impuesto Pagado en Declaraci??n(es) Sustituida(s)", header_style)
        ws1.write_merge(row, row, 8, 8, "0,00", header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row = row + 1
        ws1.write_merge(row, row, 4, 4, (row - 7), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Retenciones Descontadas en Declaraci??n(es) Sustitutiva(s)", header_style)
        ws1.write_merge(row, row, 8, 8, "0,00", header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row = row + 1
        ws1.write_merge(row, row, 4, 4, (row - 7), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Percepciones Descontadas en Declaraci??n(es) Sustitutiva(s)", header_style)
        ws1.write_merge(row, row, 8, 8, "0,00", header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row = row + 1
        total32 = resultado28 + resultado27
        ws1.write_merge(row, row, 4, 4, (row - 7), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Sub- Total Impuesto a Pagar:", sub_header_style)
        # ws1.write_merge(row,row, 8, 8, "0,00",sub_header_style_r)
        ws1.write_merge(row, row, 9, 9, total32, sub_header_style_r)

        row = row + 1
        ws1.write_merge(row, row, 4, 9, "RETENCIONES IVA", sub_header_style)
        # ws1.write_merge(row,row, 8, 8, "BASE IMPONIBLE",sub_header_style)
        # ws1.write_merge(row,row, 9, 9, "CR??DITO FISCAL",sub_header_style)
        row = row + 1

        # Monto total retencion iva
        total_ret_anterior = 0
        ws1.write_merge(row, row, 4, 4, (row - 8), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Retenciones IVA Acumuladas por Descontar", header_style)
        ws1.write_merge(row, row, 8, 8, total_ret_anterior, header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row = row + 1
        ws1.write_merge(row, row, 4, 4, (row - 8), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Retenciones del IVA del Periodo", header_style)
        ws1.write_merge(row, row, 8, 8, total_ret, header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row = row + 1
        ws1.write_merge(row, row, 4, 4, (row - 8), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Cr??ditos del IVA Adquiridos por Cesiones de Retenciones", header_style)
        ws1.write_merge(row, row, 8, 8, "0,00", header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row = row + 1
        ws1.write_merge(row, row, 4, 4, (row - 8), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Recuperaciones del IVA Retenciones Solicitadas", header_style)
        ws1.write_merge(row, row, 8, 8, "0,00", header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row = row + 1
        total_ret_iva2 = total_ret + total_ret_anterior
        ws1.write_merge(row, row, 4, 4, (row - 8), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Total Retenciones del IVA", header_style)
        ws1.write_merge(row, row, 8, 8, total_ret_iva2, header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row = row + 1
        total_ret_desc = 0
        if total32 < total_ret_iva2:
            ret_iva_soportada = total32
        else:
            ret_iva_soportada = total_ret_iva2
        ws1.write_merge(row, row, 4, 4, (row - 8), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Retenciones del IVA Soportadas y Descontadas", header_style)
        ws1.write_merge(row, row, 8, 8, total_ret_desc, header_style_r)
        ws1.write_merge(row, row, 9, 9, ret_iva_soportada, header_style_r)
        row = row + 1
        solo_ret_iva = total_ret_iva2 - total_ret_desc
        ws1.write_merge(row, row, 4, 4, (row - 8), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Saldo Retenciones del IVA no Aplicado ", header_style)
        ws1.write_merge(row, row, 8, 8, solo_ret_iva, header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row = row + 1
        ws1.write_merge(row, row, 4, 4, (row - 8), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Sub- Total Impuesto a Pagar item 40:", sub_header_style)
        # ws1.write_merge(row,row, 8, 8, "0,00",sub_header_style_r)
        ws1.write_merge(row, row, 9, 9, total32 - ret_iva_soportada, sub_header_style_r)

        row = row + 1
        ws1.write_merge(row, row, 4, 9, "PERCEPCI??N", sub_header_style)
        # ws1.write_merge(row,row, 8, 8, "BASE IMPONIBLE",sub_header_style)
        # ws1.write_merge(row,row, 9, 9, "CR??DITO FISCAL",sub_header_style)
        row = row + 1
        ws1.write_merge(row, row, 4, 4, (row - 9), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Percepciones Acumuladas en Importaciones por Descontar", header_style)
        ws1.write_merge(row, row, 8, 8, "0,00", header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row = row + 1
        ws1.write_merge(row, row, 4, 4, (row - 9), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Percepciones del Periodo", header_style)
        ws1.write_merge(row, row, 8, 8, "0,00", header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row = row + 1
        ws1.write_merge(row, row, 4, 4, (row - 9), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Cr??ditos Adquiridos por Cesiones de Percepciones", header_style)
        ws1.write_merge(row, row, 8, 8, "0,00", header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row = row + 1
        ws1.write_merge(row, row, 4, 4, (row - 9), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Recuperaciones Percepciones Solicitado", header_style)
        ws1.write_merge(row, row, 8, 8, "0,00", header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row = row + 1
        ws1.write_merge(row, row, 4, 4, (row - 9), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Total Percepciones", header_style)
        ws1.write_merge(row, row, 8, 8, "0,00", header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row = row + 1
        ws1.write_merge(row, row, 4, 4, (row - 9), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Percepciones en Aduanas Descontadas", header_style)
        ws1.write_merge(row, row, 8, 8, "0,00", header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row = row + 1
        ws1.write_merge(row, row, 4, 4, (row - 9), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Saldo de Percepciones en Aduanas no Aplicado", header_style)
        ws1.write_merge(row, row, 8, 8, "0,00", header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", header_style_r)
        row = row + 1
        ws1.write_merge(row, row, 4, 4, (row - 9), header_style_c)
        ws1.write_merge(row, row, 5, 7, "Total a Pagar:", sub_header_style)
        # ws1.write_merge(row,row, 8, 8, "0,00",sub_header_style_r)
        ws1.write_merge(row, row, 9, 9, "0,00", sub_header_style_r)
        # ************ fin cuerpo excel
        wb1.save(fp)
        out = base64.b64encode(fp.getvalue())
        action = self.env.ref('l10n_ve_book_resume_iva_72.action_resumen_download_wizard').read()[0]
        ids = self.env['resume.download.wizard'].create({
             'report': out,
             'name': 'Resume_ventas_compras.xls'
        })
        action['res_id'] = ids.id
        end_time = datetime.now()
        _logger.info(">> ({}) {}: {}  | {}: {}".format(
            'generate_xls_report',
            'Hora de Inicio', start_time,
            'Tiempo de ejecucion', end_time - start_time))
        return action


class WizardResumeDownload(models.TransientModel):
    _name = "resume.download.wizard"

    name = fields.Char(string='Link', readonly="True")
    report = fields.Binary('Prepared file', readonly=True)
