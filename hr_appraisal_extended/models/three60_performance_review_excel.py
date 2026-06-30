import pytz
import xlsxwriter
import base64

from odoo import fields, models, api
from io import BytesIO
from datetime import datetime
from pytz import timezone


class PerformanceReview(models.AbstractModel):
    _name = 'report.hr_appraisal_extended.report_360_performance_review'
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, reviews):
        for review in reviews:
            worksheet = workbook.add_worksheet('360_performance_review')

            worksheet.protect()
            merge_format1 = workbook.add_format({
                'bold': 1,
                'border': 1,
                'align': 'left',
                'text_wrap': True,
                'valign': 'vcenter', })

            merge_format2 = workbook.add_format({
                'bold': 1,
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'border_color': '#000000',
                'fg_color': '#d8d8d8',
                'text_wrap': True,
            })

            merge_format3 = workbook.add_format({
                'bold': 1,
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'border_color': '#000000',
                'fg_color': '#f2f2f2',
                'text_wrap': True,
            })

            merge_format4 = workbook.add_format({
                'bold': 1,
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'border_color': '#000000',
                'fg_color': '#4472c4',
                'text_wrap': True,
            })
            merge_format5 = workbook.add_format({
                'bold': 1,
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'border_color': '#000000',
                'fg_color': '#ed7d31',
                'text_wrap': True,
            })
            merge_format6 = workbook.add_format({
                'bold': 1,
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'border_color': '#000000',
                'fg_color': '#70ad47',
                'text_wrap': True,
            })
            merge_format7 = workbook.add_format({
                'bold': 1,
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'border_color': '#000000',
                'fg_color': '#f7caac',
                'text_wrap': True,
            })
            merge_format8 = workbook.add_format({
                'bold': 1,
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'border_color': '#000000',
                'fg_color': '#ffc000',
                'text_wrap': True,
            })
            merge_format9 = workbook.add_format({
                'bold': 1,
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'border_color': '#000000',
                'fg_color': '#FFFF00',
                'text_wrap': True,
            })

            worksheet.set_default_row(45)

            worksheet.set_column('A:A', 2)
            worksheet.set_column('B:B', 40)
            worksheet.set_column('C:C', 10)
            worksheet.set_column('D:D', 2)
            worksheet.set_column('E:E', 40)
            worksheet.set_column('F:F', 10)
            worksheet.set_column('G:G', 5)
            worksheet.set_column('H:H', 15)
            worksheet.set_column('I:I', 25)
            worksheet.set_column('J:J', 15)

            worksheet.write(1, 1, "Who are you leaving feedback for? (Employee Name)", merge_format2)
            worksheet.write(2, 1, "What is their job title:", merge_format2)
            worksheet.write(3, 1, "Grade (if applicable):", merge_format2)
            worksheet.merge_range('B5:F5', 'Please rate the above Employee in accordance with the criteria below:',
                                  merge_format3)

            worksheet.merge_range('C2:F2', review.employee_id.name or '', merge_format1)
            worksheet.merge_range('C3:F3', review.job_id.name or '', merge_format1)
            worksheet.merge_range('C4:F4', review.grade or '', merge_format1)

            row = 5

            written_categories_left = set()
            written_categories_right = set()

            left_row = row
            right_row = row
            add_row_left = 0
            add_row_right = 0
            left_review_type=''
            right_review_type=''
            line_count = 0
            right_line_count = 0
            total_rating_per = 0
            for line in review.review_line_ids:
                if line.review_type in ['communication', 'problem_solving', 'organisation_time',
                                        'interpersonal_skills']:
                    if line.review_type not in written_categories_left:
                        add_row_left += 1
                        if add_row_left > 1:
                            rating_marks = sum(review.review_line_ids.filtered(lambda line: line.review_type == left_review_type).mapped("rating_marks"))
                            rating_per = ((rating_marks/4)/5)*100
                            total_rating_per += rating_per
                            worksheet.write(left_row, 2,f"{str(rating_per)}%", merge_format2)
                            left_row += 1
                        left_review_type = line.review_type
                        worksheet.write(left_row, 1, dict(line._fields['review_type'].selection).get(line.review_type, '').capitalize(),
                                        merge_format4)
                        worksheet.write(left_row, 2, 'Rating', merge_format4)
                        written_categories_left.add(line.review_type)
                        left_row += 1

                    worksheet.write(left_row, 1, line.config_id.name, merge_format1)
                    worksheet.write(left_row, 2, line.rating if line.rating is not None else '', merge_format2)
                    left_row += 1
                    if len(written_categories_left) == 4:
                        line_count +=1
                    if len(written_categories_left) == 4 and line_count==4:
                        rating_marks = sum(
                            review.review_line_ids.filtered(lambda line: line.review_type == left_review_type).mapped(
                                "rating_marks"))
                        rating_per = ((rating_marks / 4) / 5) * 100
                        total_rating_per += rating_per
                        worksheet.write(left_row, 2, f"{str(rating_per)}%", merge_format2)
                        left_row += 1
                        add_row_left += 1

                elif line.review_type in ['team_working', 'continuous', 'customer_focus', 'motivation']:
                    if line.review_type not in written_categories_right:
                        add_row_right += 1
                        if add_row_right > 1:
                            rating_marks = sum(
                                review.review_line_ids.filtered(lambda line: line.review_type == right_review_type).mapped(
                                    "rating_marks"))
                            rating_per = ((rating_marks / 4) / 5) * 100
                            total_rating_per += rating_per
                            worksheet.write(right_row, 5, f"{str(rating_per)}%", merge_format2)
                            right_row += 1

                        right_review_type = line.review_type
                        worksheet.write(right_row, 4,
                                              dict(line._fields['review_type'].selection).get(line.review_type, '').capitalize(), merge_format6)
                        worksheet.write(right_row, 5, 'Rating', merge_format6)
                        written_categories_right.add(line.review_type)
                        right_row += 1

                    worksheet.write(right_row, 4, line.config_id.name, merge_format1)
                    worksheet.write(right_row, 5, line.rating if line.rating is not None else '', merge_format2)
                    right_row += 1
                    if len(written_categories_right) == 4:
                        right_line_count +=1
                    if len(written_categories_right) == 4 and right_line_count==4:
                        rating_marks = sum(
                            review.review_line_ids.filtered(lambda line: line.review_type == right_review_type).mapped(
                                "rating_marks"))
                        rating_per = ((rating_marks / 4) / 5) * 100
                        total_rating_per += rating_per
                        worksheet.write(right_row, 5, f"{str(rating_per)}%", merge_format2)
                        right_row += 1
                        add_row_right += 1
            worksheet.write(left_row, 1, f"Overall Percentage ",merge_format9)
            worksheet.write(left_row, 2, f"{total_rating_per / 8:.2f}%", merge_format1)
            left_row +=1
            worksheet.write(left_row, 1, "Review submitted by (Employee Name, Designation , Department , BU) ",merge_format9)
            worksheet.write(left_row+1 , 1, "Date and Time ", merge_format9)

            review_submitted_by = review.review_submitted_by.name or ''
            review_designation = review.review_designation.name or ''
            review_department = review.review_department.name or ''
            review_bu = ', '.join(review.review_bu_ids.mapped('name')) if review.review_bu_ids else ''
            review_date_time = review.review_date_time_prob.strftime('%Y-%m-%d %H:%M:%S') if review.review_date_time_prob else ''

            reviewer_details = f"{review_submitted_by}, {review_designation}, {review_department}, {review_bu}"

            worksheet.merge_range(left_row, 2, left_row, 5, reviewer_details, merge_format1)
            worksheet.merge_range(left_row + 1, 2, left_row + 1, 5, review_date_time, merge_format1)
