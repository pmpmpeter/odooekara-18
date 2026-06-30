from odoo import api, fields, models, _
import time, re, xlwt, base64, math, itertools
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError, Warning
from datetime import date, datetime
import logging
from PIL import Image


class AccountLedgerBalanceReport(models.AbstractModel):
    _name = 'report.account_ledger_balance.account_ledger_balance_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, lines):
        # =========================Creating Excel Sheet Forms and styles=============
        worksheet1 = workbook.add_worksheet("Summary")
        worksheet2 = workbook.add_worksheet("Transactions")
        cell_header1 = workbook.add_format({'align': 'left',
                                            'font_size': 10,
                                            'valign': 'vcenter',
                                            'border': 1,
                                            'bold': 1})
        cell_header2 = workbook.add_format({'align': 'center',
                                            'font_size': 10,
                                            'valign': 'vcenter',
                                            'border': 1,
                                            'bold': 1})
        cell_data1 = workbook.add_format({'font_size': 10, 'align': 'left', 'valign': 'vcenter', 'border': 1})
        cell_data2 = workbook.add_format({'font_size': 10, 'align': 'left', 'valign': 'vcenter', 'border': 1})
        cell_data3 = workbook.add_format({'font_size': 10, 'align': 'center', 'valign': 'vcenter', 'border': 1})
        floating_point_bordered = workbook.add_format(
            {'font_size': 10, 'num_format': '#,##0.00', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        floating_point = workbook.add_format(
            {'font_size': 10, 'num_format': '#,##0.00', 'align': 'right', 'valign': 'vcenter', 'border': 1})
        date_format = workbook.add_format(
            {'font_size': 10, 'align': 'left', 'valign': 'vcenter', 'border': 1, 'num_format': 'dd/mm/yyyy'})
        # ---------------------------- Set Cloums in excel format----------------------
        # worksheet.set_column('A:A', 30)
        worksheet1.set_column('B:B', 15)
        worksheet1.set_column('C:C', 15)
        worksheet1.set_column('D:D', 15)
        worksheet1.set_column('E:E', 15)
        worksheet1.set_column('F:F', 15)
        worksheet1.set_column('G:G', 13)
        worksheet1.set_column('H:H', 13)
        worksheet1.set_column('I:I', 13)
        worksheet1.set_column('J:J', 13)
        worksheet1.set_column('K:K', 13)
        worksheet1.set_column('L:L', 13)
        worksheet1.set_column('M:M', 13)
        worksheet2.set_column('B:B', 10)
        worksheet2.set_column('C:C', 12)
        worksheet2.set_column('D:D', 35)
        worksheet2.set_column('E:E', 13)
        worksheet2.set_column('F:F', 13)
        worksheet2.set_column('G:G', 13)
        worksheet2.set_column('H:H', 13)
        worksheet2.set_column('I:I', 13)
        worksheet2.set_column('J:J', 13)
        worksheet2.set_column('K:K', 13)
        worksheet2.set_column('L:L', 13)
        worksheet2.set_column('M:M', 13)

        # worksheet.freeze_panes(1, 0)

        field_heading1 = ["FROM DATE",
                          "TO DATE", "DEBIT", "CREDIT", "CLOSING BALANCE"]
        field_heading2 = ["S.NO",
                          "DATE", "MOVE", "DESCRIPTION", "DEBIT", "CREDIT", "BALANCE"]

        try:
            for i in range(0, 300):
                worksheet1.set_row(i, 25)
                worksheet2.set_row(i, 25)
        except:
            pass

        report_id = self.env['accounting.balance.report'].search([('id', '=', data['ids'])])
        row = 1
        col = 0
        worksheet1.merge_range(row, row, col + 1, col + 5,
                               'LEDGER' + ' ' + str(report_id.account_id.code.upper()) + ' ' + str(
                                   report_id.account_id.name.upper()) + ' ' + 'REPORT',
                               cell_header2)
        row += 2
        for rec in report_id:
            worksheet1.write(row, col + 1, 'Ledger Name :', cell_header1)
            worksheet1.write(row, col + 2, rec.account_id.code + ' ' + rec.account_id.name, cell_data1)
            worksheet1.write(row + 1, col + 1, 'Start Date :', cell_header1)
            worksheet1.write(row + 1, col + 2, rec.date_from.strftime('%d/%m/%Y'), cell_data1)
            row = row + 1
            worksheet1.write(row + 1, col + 1, 'End Date :', cell_header1)
            worksheet1.write(row + 1, col + 2, rec.date_to.strftime('%d/%m/%Y'), cell_data1)
            row = row + 1
            partner_name = ''
            for partner in rec.partner_ids:
                if partner_name:
                    partner_name = partner_name + ',' + partner.name
                else:
                    partner_name = partner.name
            if partner_name:
                worksheet1.write(row + 1, col + 1, 'Partner :', cell_header1)
                worksheet1.write(row + 1, col + 2, partner_name, cell_data1)
                row = row + 1
            analytic_name = ''
            for analytic in rec.analytic_account_ids:
                if analytic_name:
                    analytic_name = analytic_name + ',' + analytic.name + '-' + analytic.partner_id.name
                else:
                    analytic_name = analytic.name + '-' + analytic.partner_id.name
            if analytic_name:
                worksheet1.write(row + 1, col + 1, 'Analytic Account :', cell_header1)
                worksheet1.write(row + 1, col + 2, analytic_name, cell_data1)
                row = row + 1
            row += 1
            worksheet1.write(row + 1, col + 1, 'Opening Balance :', cell_header1)
            worksheet1.write(row + 1, col + 2, 'Debit :', cell_header1)
            worksheet1.write(row + 1, col + 3, rec.get_open_bal_debit(rec), floating_point)
            worksheet1.write(row + 1, col + 4, 'Credit :', cell_header1)
            worksheet1.write(row + 1, col + 5, rec.get_open_bal_credit(rec), floating_point)
            row += 1
            worksheet1.write(row + 1, col + 1, 'Period Total :', cell_header1)
            worksheet1.write(row + 1, col + 2, 'Debit :', cell_header1)
            worksheet1.write(row + 1, col + 3, rec.get_period_bal_debit(rec), floating_point)
            worksheet1.write(row + 1, col + 4, 'Credit :', cell_header1)
            worksheet1.write(row + 1, col + 5, rec.get_period_bal_credit(rec), floating_point)
            row += 1
            worksheet1.write(row + 1, col + 1, 'Closing Balance :', cell_header1)
            worksheet1.write(row + 1, col + 2, rec.get_closing_balance(rec), floating_point)
            row += 2

            for index, col_data in enumerate(field_heading1):
                worksheet1.write(row + 1, index + 1, col_data, cell_header2)
            row += 1
            for reps in rec.monthly_report_lines:
                worksheet1.write(row + 1, col + 1, reps.date_from, date_format)
                worksheet1.write(row + 1, col + 2, reps.date_to, date_format)
                worksheet1.write(row + 1, col + 3, reps.debit, floating_point)
                worksheet1.write(row + 1, col + 4, reps.credit, floating_point)
                worksheet1.write(row + 1, col + 5, reps.cl_balance, floating_point)
                row += 1
            row += 1

            row1 = 0
            col1 = 0
            worksheet2.freeze_panes(1, 0)
            for index, col_data in enumerate(field_heading2):
                worksheet2.write(row1, index, col_data, cell_header2)

            s_no = 1
            total_debit = 0.00
            total_credit = 0.00
            closing_balance = rec.get_open_bal_debit(rec) - rec.get_open_bal_credit(rec)
            for h in rec.get_account_data(rec):
                worksheet2.write(row1 + 1, col1, s_no, cell_data3)
                worksheet2.write(row1 + 1, col1 + 1, datetime.strptime(h['date'], '%d/%m/%Y'), date_format)
                worksheet2.write(row1 + 1, col1 + 2, h['move'], cell_data2)
                worksheet2.write(row1 + 1, col1 + 3, h['name'], cell_data2)
                worksheet2.write(row1 + 1, col1 + 4, h['debit'], floating_point)
                total_debit += h['debit']
                worksheet2.write(row1 + 1, col1 + 5, h['credit'], floating_point)
                total_credit += h['credit']
                worksheet2.write(row1 + 1, col1 + 6, h['balance'] + closing_balance, floating_point)
                closing_balance += h['balance']
                row1 += 1
                s_no += 1
            row1 += 1
            # worksheet2.write(row1 + 1, col1 + 1, 'Period Total :', cell_header1)
            # worksheet2.write(row1 + 1, col1 + 2, 'Debit :', cell_header1)
            # worksheet2.write(row1 + 1, col1 + 3, total_debit, floating_point)
            # worksheet2.write(row1 + 1, col1 + 4, 'Credit :', cell_header1)
            # worksheet2.write(row1 + 1, col1 + 5, total_credit, floating_point)
            # row1 += 1
            # worksheet2.write(row1 + 1, col1 + 1, 'Closing Balance :', cell_header1)
            # worksheet2.write(row1 + 1, col1 + 2, closing_balance, floating_point)
