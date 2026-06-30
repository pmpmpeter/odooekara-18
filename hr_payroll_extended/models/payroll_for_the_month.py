import pytz
import xlsxwriter
import base64

from odoo import fields, models, api
from io import BytesIO
from datetime import datetime
from pytz import timezone


class PayrollForTheMonth(models.AbstractModel):
    _name = 'report.hr_payroll_extended.report_payroll_for_the_month'
    _inherit = "report.report_xlsx.abstract"


    def generate_xlsx_report(self, workbook,data,employee):

        # main_product = data
        # company_name = main_product['company_name']
        # company_id = main_product['company_id']
        # date_from = main_product['date_from']
        # date_to = main_product['date_to']

        worksheet = workbook.add_worksheet('payroll_for_the_month')

        worksheet.protect()
        merge_format1 = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'border_color': '#000000',
            'text_wrap': True,
        })

        merge_format2 = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'border_color': '#000000',
            'fg_color': '#d9e2f3',
            'text_wrap': True,
        })
        merge_format3 = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'border_color': '#000000',
            'fg_color': '#ffcccb',
            'text_wrap': True,
        })

        merge_format4 = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'border_color': '#000000',
            'fg_color': '#FFFF99',
            'text_wrap': True,
        })

        merge_format5 = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'border_color': '#000000',
            'fg_color': '#FFFF66',
            'text_wrap': True,
        })








        worksheet.set_column('A:A', 5)
        worksheet.set_column('B:B', 15)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 15)
        worksheet.set_column('E:E', 15)
        worksheet.set_column('F:F', 15)
        worksheet.set_column('G:G', 15)
        worksheet.set_column('H:H', 15)
        worksheet.set_column('I:I', 25)
        worksheet.set_column('J:J', 15)
        worksheet.set_column('L:L', 15)
        worksheet.set_column('M:M', 15)
        worksheet.set_column('N:N', 15)
        worksheet.set_column('O:O', 15)
        worksheet.set_column('P:P', 15)
        worksheet.set_column('Q:Q', 15)
        worksheet.set_column('R:R', 15)
        worksheet.set_column('S:S', 15)
        worksheet.set_column('T:T', 15)
        worksheet.set_column('U:U', 15)
        worksheet.set_column('V:V', 15)
        worksheet.set_column('W:W', 15)
        worksheet.set_column('X:X', 15)
        worksheet.set_column('Y:Y', 15)
        worksheet.set_column('Z:Z', 15)
        worksheet.set_column('AA:AA', 15)
        # worksheet.set_row('M4', 2)
        # worksheet.set_row(4, 15)
        # Create a format
        # cell_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
        # # Apply the format to specific cells
        # worksheet.write('M4', "", cell_format)
        # worksheet.write('N4', "", cell_format)
        # # worksheet.write('N4', "", cell_format)


        # worksheet.merge_range('B2:L2', 'GMC Details', merge_format1)

        # worksheet.merge_range('A2:I2', datetime.datetime.strptime(str(date_from), '%Y-%m-%d').strftime('%d-%m-%Y') +' ' 'To' ' ' + datetime.datetime.strptime(str(date_to), '%Y-%m-%d').strftime('%d-%m-%Y'), format_date)
        worksheet.merge_range('B2:D2', 'Ekara Partnership', merge_format2)

        worksheet.merge_range('B3:D3', 'Payroll Data for September 2024', merge_format2)
        worksheet.merge_range('B4:B5', 'Sl #', merge_format1)
        worksheet.set_row(3, 70, merge_format1)
        worksheet.merge_range('C4:C5', 'Employee', merge_format1)
        worksheet.merge_range('D4:D5', 'Employement Status', merge_format1)
        worksheet.merge_range('E4:E5', 'Empl.No.', merge_format1)

        worksheet.merge_range('F4:F5', 'UAN', merge_format1)
        worksheet.merge_range('G4:G5', 'Date of joining', merge_format1)
        worksheet.merge_range('H4:H5', 'Date of Resignation Acceptance', merge_format1)
        worksheet.merge_range('I4:I5', 'Last working day', merge_format1)

        worksheet.merge_range('J4:J5', 'Location', merge_format1)
        worksheet.merge_range('K4:K5', 'Annual Compensation', merge_format3)
        worksheet.merge_range('L4:L5', 'Days paid this month (September 2024)', merge_format1)

        worksheet.merge_range('O4:O5', 'LoP this month', merge_format1)
        worksheet.merge_range('P4:Z4', 'Components', merge_format1)
        worksheet.write(4, 12, "CL this month", merge_format1)
        worksheet.write(4, 13, "EL this month", merge_format1)
        worksheet.write(4, 15, "Basic", merge_format3)
        worksheet.write(4, 16, "HRA", merge_format3)
        worksheet.write(4, 17, "Statutory Bonus", merge_format3)
        worksheet.write(4, 18, "Co. contr. to PF", merge_format3)
        worksheet.write(4, 19, "Food Coupons", merge_format4)
        worksheet.write(4, 20, "Personal pay", merge_format3)
        worksheet.write(4, 21, "Deductions - Parental Insurance  Premium installment for this month", merge_format4)
        worksheet.write(4, 22, "Other earnings (thro 'payroll)", merge_format4)
        worksheet.write(4, 23, "Oth. earnings (arrears)", merge_format4)
        worksheet.write(4, 24, "Recovery of advances", merge_format4)
        worksheet.write(4, 25, "Other recoveries ", merge_format4)
        worksheet.write(4, 26, "Remarks", merge_format5)




