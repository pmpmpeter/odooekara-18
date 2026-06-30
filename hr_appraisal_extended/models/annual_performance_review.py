import pytz
import xlsxwriter
import base64

from odoo import fields, models, api
from io import BytesIO
from datetime import datetime
from pytz import timezone


class AnnualPerformanceReview(models.AbstractModel):
    _name = 'report.hr_appraisal_extended.report_annual_performance_review'
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, rating_id):
        worksheet = workbook.add_worksheet('annual_performance_review')

        # Protect the worksheet
        worksheet.protect()

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'center',
            'text_wrap': True,
            'valign': 'vcenter',
            'fg_color': '#e7e6e6'
        })

        cell_format = workbook.add_format({'border': 1, 'align': 'center'})

        total_format = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'center',
            'fg_color': '#fbe4d5'
        })

        # Set column widths
        worksheet.set_column('A:A', 20)
        worksheet.set_column('B:B', 30)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 10)
        worksheet.set_column('E:E', 20)

        # Write headers
        worksheet.write(0, 0, "KRA", header_format)
        worksheet.write(0, 1, "Description", header_format)
        worksheet.write(0, 2, "Weightage (%)", header_format)
        worksheet.write(0, 3, "Self Rating (%)", header_format)
        worksheet.write(0, 4, "Employee Weighted Score", header_format)

        worksheet.write(0, 6, "Manager Rating (%)", header_format)
        worksheet.write(0, 7, "Manager Weighted Score", header_format)

        # Write self-rating data
        row = 1
        for kra in rating_id.kra_ids:
            worksheet.write(row, 0, kra.name, cell_format)
            worksheet.write(row, 1, kra.goal_description or "", cell_format)
            worksheet.write(row, 2, kra.weightage, cell_format)
            worksheet.write(row, 3, kra.self_rating, cell_format)
            worksheet.write(row, 4, kra.employee_weighted_score, cell_format)
            # worksheet.write(row, 4, f"{int(kra.employee_weighted_score)}%", cell_format)
            row += 1

        # Write manager ratings data
        row = 1
        for manager in rating_id.manager_rating_ids:
            worksheet.write(row, 6, manager.manager_rating, cell_format)
            worksheet.write(row, 7, manager.manager_weighted_score, cell_format)
            row += 1

        # Write totals
        merge_row = row + 1
        worksheet.merge_range(f'A{merge_row}:D{merge_row}', 'Total Employee', total_format)
        worksheet.write(merge_row - 1, 4, rating_id.total_score_employee, total_format)

        worksheet.merge_range(f'F{merge_row}:G{merge_row}', 'Total Manager', total_format)
        worksheet.write(merge_row - 1, 7, rating_id.total_score_manager, total_format)

        # Final scores
        row += 2
        worksheet.write(row, 3, "Final Employee Score", total_format)
        worksheet.write(row, 4, rating_id.employee_final_score, total_format)

        worksheet.write(row, 6, "Final Manager Score", total_format)
        worksheet.write(row, 7, rating_id.manager_final_score, total_format)
