import pytz
import xlsxwriter
import base64

from odoo import fields, models, api
from io import BytesIO
from datetime import datetime
from pytz import timezone

class DirectorFinalRatings(models.AbstractModel):
    _name = 'report.hr_appraisal_extended.report_director_final_ratings'
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook,data,rating_id):

        worksheet = workbook.add_worksheet('Sales Collection Wise Report.xlsx')
        worksheet.protect()
        cell_format = workbook.add_format({'border': 1})
        merge_format1 = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'border_color': '#000000',
            'valign': 'vcenter',
            'text_wrap': True,
        })

        merge_format2 = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'border_color': '#000000',
            'fg_color': '#e7e6e6',
            'text_wrap': True,
        })

        worksheet.set_row(1, 30)

        worksheet.set_column('A:A', 15)
        worksheet.set_column('B:B', 25)
        worksheet.set_column('C:C', 25)
        worksheet.set_column('D:D', 25)
        worksheet.set_column('E:E', 30)
        worksheet.set_column('F:F', 30)
        worksheet.set_column('G:G', 30)
        worksheet.set_column('H:H', 30)
        worksheet.set_column('I:I', 30)
        worksheet.set_column('J:J', 30)
        worksheet.set_row(1, 30)
        worksheet.write(1, 0, "Name", merge_format2)
        worksheet.write(1, 1, "Designation", merge_format2)
        worksheet.write(1, 2, "Overall Final Rating", merge_format2)
        worksheet.write(1, 3, "Recommended Increment %", merge_format2)
        worksheet.write(1, 4, "Recommended PBVP Payout \n %(to be released on a pro-rata basis)", merge_format2)
        worksheet.write(1, 5, "Eligible for Promotion? (Y/N)", merge_format2)
        worksheet.write(1, 6, "New Designation (if applicable)", merge_format2)

        worksheet.write(2, 0, rating_id.employee_id.name, merge_format1)
        worksheet.write(2, 1, rating_id.designation_id.name, merge_format1)
        worksheet.write(2, 2, rating_id.manager_final_score, merge_format1)
        worksheet.write(2, 3, rating_id.recommended_increment, merge_format1)
        worksheet.write(2, 4, rating_id.recommended_pbvp_payout, merge_format1)
        worksheet.write(2, 5, rating_id.eligible_for_promotion if rating_id.eligible_for_promotion == 'no' else rating_id.new_job_level, merge_format1)
        worksheet.write(2, 6, rating_id.new_designation, merge_format1)

