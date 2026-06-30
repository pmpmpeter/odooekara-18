# -*- coding: utf-8 -*-

import io
import xlsxwriter
from odoo import api, fields, models, _
from odoo.tools import date_utils
from odoo.tools.safe_eval import json
from odoo.exceptions import ValidationError
import base64


class SurveyXlsReport(models.TransientModel):
    _name = 'survey.xlsx.report'
    _description = 'Survey Report '

    partner_id = fields.Many2one('res.partner', string="Partner",
                                 help="Select for getting the report of the "
                                      "user", default=lambda self: self.env.user.partner_id)
    survey_ids = fields.Many2many('survey.survey', string="Survey",
                                  help="This field stores survey ids",
                                  readonly=False)
    report_file = fields.Binary(string="Report File", readonly=True)
    file_name = fields.Char(string="File Name", readonly=True)
    group_by = fields.Selection([('questions', 'Questions'),
                                 ], string='Group By')

    def action_print_survey_results_percentage_xlsx_report(self):
        if not self.survey_ids:
            surveys = self.env['survey.survey'].sudo().search([])
        else:
            surveys = self.survey_ids

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Survey Report")

        title_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'align': 'center', 'border': 1})
        answer_format = workbook.add_format({'align': 'center', 'border': 1})
        question_format = workbook.add_format({'align': 'left', 'text_wrap': True, 'border': 1})
        total_format = workbook.add_format(
            {'bold': True, 'bg_color': '#D3D3D3', 'align': 'center', 'border': 1})  # Gold background for total

        worksheet.set_column('A:A', 15)  # Qn. No.
        worksheet.set_column('B:B', 25)  # Survey Name
        worksheet.set_column('C:C', 20)  # Category
        worksheet.set_column('D:D', 50)  # Question
        worksheet.set_column('E:N', 20)  # Answer Columns

        headers = ["Qn. No.", "Survey Name", "Category", "Question", "Strongly Agree", "Strongly Agree%", "Agree",
                   "Agree%",
                   "Neutral", "Neutral%", "Disagree", "Disagree%", "Strongly Disagree", "Strongly Disagree%"]

        for col, header in enumerate(headers):
            worksheet.write(2, col, header, title_format)

        score_mapping = {
            "Strongly Agree": 5,
            "Agree": 4,
            "Neither Agree nor Disagree": 3,
            "Disagree": 2,
            "Strongly Disagree": 1
        }

        total_counts = {key: 0 for key in score_mapping.keys()}

        row = 3
        for survey in surveys:
            user_inputs = self.env['survey.user_input'].sudo().search([
                ('survey_id', '=', survey.id),
                ('state', '=', 'done')
            ])

            question_data = {}
            question_order = {}
            question_counter = 1

            for user_input in user_inputs:
                answers = self.env['survey.user_input.line'].sudo().search([
                    ('user_input_id', '=', user_input.id)
                ])

                for answer in answers:
                    question = answer.question_id
                    question_id = question.id

                    if question_id not in question_data:
                        question_data[question_id] = {
                            'survey_name': survey.title,
                            'question': question.title,
                            'category': question.survey_category_id.name or "-",
                            'Strongly Agree': 0,
                            'Agree': 0,
                            'Neither Agree nor Disagree': 0,
                            'Disagree': 0,
                            'Strongly Disagree': 0,
                            'Total Score': 0
                        }
                        question_order[question_id] = question_counter
                        question_counter += 1

                    response_text = answer.display_name
                    score = score_mapping.get(response_text, 0)

                    if response_text in question_data[question_id]:
                        question_data[question_id][response_text] += 1
                        total_counts[response_text] += 1

                    question_data[question_id]['Total Score'] += score

            for question_id, data in question_data.items():
                # Score-Based Calculation
                # total_score = data['Total Score'] or 1

                # Count-Based Calculation: Get total responses for the question
                total_responses = sum(data[resp] for resp in score_mapping.keys()) or 1

                worksheet.set_row(row, 30)
                worksheet.write(row, 0, question_order[question_id], answer_format)
                worksheet.write(row, 1, data['survey_name'], answer_format)
                worksheet.write(row, 2, data['category'], answer_format)
                worksheet.write(row, 3, data['question'], question_format)

                for col_index, response_type in enumerate(score_mapping.keys()):
                    count = data[response_type]

                    # Score-Based Calculation
                    # percentage = (count * score_mapping[response_type] / total_score) * 100

                    # Count-Based Calculation
                    percentage = (count / total_responses) * 100

                    worksheet.write(row, 4 + (col_index * 2), count, answer_format)
                    worksheet.write(row, 5 + (col_index * 2), f"{percentage:.2f}%", answer_format)

                row += 1

        worksheet.write(row, 3, "Total", total_format)
        total_responses = sum(total_counts.values()) or 1

        for col_index, response_type in enumerate(score_mapping.keys()):
            total_count = total_counts[response_type]
            total_percentage = (total_count / total_responses) * 100

            worksheet.write(row, 4 + (col_index * 2), total_count, total_format)
            worksheet.write(row, 5 + (col_index * 2), f"{total_percentage:.2f}%", total_format)

        workbook.close()
        output.seek(0)
        self.report_file = base64.b64encode(output.read())
        self.file_name = "Survey_Report.xlsx"

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'survey.xlsx.report',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_print_survey_groupby_xlsx_report(self):
        if self.group_by:
            survey_data_map = {}
            if not self.survey_ids:
                print('ccc')
                surveys = self.env['survey.survey'].sudo().search([])
                for survey in surveys:
                    user_inputs = self.env['survey.user_input'].sudo().search([
                        ('survey_id', '=', survey.id),
                        ('state', '=', 'done')
                    ])
                    survey_data_map[survey.title] = []
                    for user_input in user_inputs:
                        answers = self.env['survey.user_input.line'].sudo().search([
                            ('user_input_id', '=', user_input.id)
                        ])
                        participant_data = {
                            'participant': user_input.partner_id.name or "Anonymous",
                            'responses': [
                                {
                                    'question': answer.question_id.title,
                                    'answer': answer.display_name,
                                    'score': answer.answer_score
                                }
                                for answer in answers
                            ]
                        }

                        survey_data_map[survey.title].append(participant_data)
            elif self.survey_ids:
                surveys = self.env['survey.survey'].sudo().search([('id', 'in', self.survey_ids.ids)])
                for survey in surveys:
                    user_inputs = self.env['survey.user_input'].sudo().search([
                        ('survey_id', '=', survey.id),
                        ('state', '=', 'done')
                    ])
                    survey_data_map[survey.title] = []
                    for user_input in user_inputs:
                        answers = self.env['survey.user_input.line'].sudo().search([
                            ('user_input_id', '=', user_input.id)
                        ])
                        participant_data = {
                            'participant': user_input.partner_id.name or "Anonymous",
                            'responses': [
                                {
                                    'question': answer.question_id.title,
                                    'answer': answer.display_name,
                                    'score': answer.answer_score
                                }
                                for answer in answers
                            ]
                        }
                        survey_data_map[survey.title].append(participant_data)

            output = io.BytesIO()

            # Create a workbook and add a worksheet
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet()
            start_row = 1  # Starting row index (0-based)
            end_row = 500  # Ending row index
            start_col = 0  # Column A (0-based)
            end_col = 3  # Column D (0-based)
            # table_format = workbook.add_format({
            #     'border': 1,  # Sets a thin border
            #     'align': 'center',  # Horizontal alignment
            #     'valign': 'vcenter',  # Vertical alignment
            # })
            # for row in range(start_row, end_row + 1):
            #     for col in range(start_col, end_col + 1):
            #         worksheet.write_blank(row, col, None, table_format)

            # Define header and formatting
            title_format1 = workbook.add_format(
                {'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D3D3D3'})
            title_format = workbook.add_format(
                {'bold': True, 'font_size': 14, 'align': 'left', 'valign': 'vcenter', 'bg_color': '#D3D3D3'})
            question_format1 = workbook.add_format(
                {'bold': True, 'font_size': 12, 'align': 'left'})
            question_format = workbook.add_format(
                {'bold': True, 'font_size': 12, 'align': 'left', 'bg_color': '#D3D3D3'})
            participant_format = workbook.add_format({'bold': True, 'font_size': 10, 'align': 'left'})
            answer_format = workbook.add_format({'font_size': 10, 'align': 'left'})
            heading_row_height = 30

            worksheet.set_column('A:A', 40)
            worksheet.set_column('B:B', 60)
            worksheet.set_column('C:C', 10)

            # Starting row
            row = 0
            worksheet.merge_range(row, 0, row, 3, 'Survey Analysis Report', title_format1)

            row = 3

            for survey_title, participants in survey_data_map.items():
                worksheet.set_row(row, heading_row_height)
                worksheet.merge_range(row, 0, row, 3, survey_title, title_format)
                row += 1
                col = 0
                if participants:
                    # Extract all questions for this survey
                    questions = []
                    for participant in participants:
                        questions.extend([response['question'] for response in participant['responses']])
                    questions = list(set(questions))  # Remove duplicates
                    for question in questions:
                        worksheet.write(row, col + 0, 'Question:', question_format1)
                        worksheet.write(row, col + 1, question, question_format1)
                        row += 2
                        worksheet.write(row, col + 0, "Participants", question_format)
                        worksheet.write(row, col + 1, "Answer", question_format)
                        worksheet.write(row, col + 2, "Score", question_format)
                        col = 0
                        row += 1

                        for participant in participants:
                            worksheet.write(row, col, participant['participant'], answer_format)

                            answer = next(
                                (response['answer'] for response in participant['responses'] if
                                 response['question'] == question),
                                "Skipped"
                            )
                            score = next(
                                (response['score'] for response in participant['responses'] if
                                 response['question'] == question),
                                "Skipped"
                            )
                            worksheet.write(row, col + 1, answer, answer_format)
                            worksheet.write(row, col + 2, score, answer_format)
                            row += 1
                        row += 1
                else:
                    worksheet.write(row, 0, "No participants", answer_format)
                    row += 1
                row += 1

            workbook.close()
            output.seek(0)
            report = output.read()
            self.report_file = base64.b64encode(report)
            self.file_name = f"Survey_Report.xlsx"
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'survey.xlsx.report',
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'new',
            }
            return report

    def action_print_survey_xlsx_report(self):
        data_dict = {}
        part_data = []
        if self.survey_ids:
            for doc in self.survey_ids:
                domain = [('survey_id', '=', doc.id), ('state', '=', 'done')]
                if self.partner_id:
                    domain.append(('partner_id', '=', self.partner_id.id))
                for record in self.env['survey.user_input'].search(domain):
                    part_data.append({'survey_name': doc.title, 'user_name': record.partner_id.name})
                    for rec in self.env['survey.user_input.line'].search(
                            [('user_input_id', '=', record.id)]):
                        data = {
                            'survey_name': rec.survey_id.title,
                            'create_date': rec.create_date,
                            'user_name': rec.user_input_id.partner_id.name,
                            'question': rec.question_id.title,
                            'answer': rec.display_name,
                            'score': rec.answer_score
                        }
                        survey_name = data['survey_name']
                        if survey_name not in data_dict:
                            data_dict[survey_name] = []
                        data_dict[survey_name].append(data)
        else:
            sur = self.env['survey.survey'].sudo().search([])
            if self.partner_id:
                for doc in sur:
                    survey_inp = self.env['survey.user_input'].search(
                        [('survey_id', '=', doc.id), ('partner_id', '=', self.partner_id.id), ('state', '=', 'done')])
                    for record in survey_inp:
                        part_data.append({'survey_name': record.survey_id.title, 'user_name': record.partner_id.name})
                        for rec in self.env['survey.user_input.line'].search(
                                [('user_input_id', '=', record.id)]):

                            data = {
                                'survey_name': rec.survey_id.title,
                                'create_date': rec.create_date,
                                'user_name': rec.user_input_id.partner_id.name,
                                'question': rec.question_id.title,
                                'answer': rec.display_name,
                                'score': rec.answer_score
                            }
                            survey_name = data['survey_name']
                            if survey_name not in data_dict:
                                data_dict[survey_name] = []
                            data_dict[survey_name].append(data)
            else:
                sur = self.env['survey.survey'].sudo().search([])
                for doc in sur:
                    survey_inp = self.env['survey.user_input'].search(
                        [('survey_id', '=', doc.id), ('state', '=', 'done')])
                    for record in survey_inp:
                        part_data.append({'survey_name': record.survey_id.title, 'user_name': record.partner_id.name})
                        for rec in self.env['survey.user_input.line'].search(
                                [('user_input_id', '=', record.id)]):

                            data = {
                                'survey_name': rec.survey_id.title,
                                'create_date': rec.create_date,
                                'user_name': rec.user_input_id.partner_id.name,
                                'question': rec.question_id.title,
                                'answer': rec.display_name,
                                'score': rec.answer_score
                            }
                            survey_name = data['survey_name']
                            if survey_name not in data_dict:
                                data_dict[survey_name] = []
                            data_dict[survey_name].append(data)
        grouped_data_list = [
            {'survey_name': survey_name,
             'data': survey_data} for survey_name, survey_data in
            data_dict.items()]
        dict_data = {
            'record': grouped_data_list,
            'part_data': part_data
        }
        report = self.get_xlsx_report(dict_data)
        self.report_file = base64.b64encode(report)
        self.file_name = f"Survey_Report.xlsx"
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'survey.xlsx.report',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
        return report

    def get_xlsx_report(self, dict_data):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        format21 = workbook.add_format({'font_size': 12, 'bold': True})
        format22 = workbook.add_format(
            {'font_size': 14, 'bold': True, 'align': 'left', 'bg_color': '#D3D3D3', 'border': 1})
        font_size_8 = workbook.add_format({'font_size': 10})
        head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '20px'})
        heading_row_height = 30
        if dict_data.get('record'):
            if dict_data['record']:
                row = 0
                for records in dict_data.get('record'):
                    sheet.write(row, 0, records['survey_name'], head)
                    sheet.set_row(sheet.dim_rowmax, heading_row_height)
                    sheet.merge_range(sheet.dim_rowmax, 0, sheet.dim_rowmax, 4,
                                      records['survey_name'],
                                      head)
                    row += 1
                    for part in dict_data.get('part_data'):
                        if part['survey_name'] == records['survey_name']:
                            sheet.merge_range(row, 0, row, 1, 'Participant:', format22)
                            sheet.merge_range(row, 2, row, 4, part['user_name'], format22)
                            row += 1
                            sheet.set_column('A:A', 5)
                            sheet.set_column('B:B', 15)
                            sheet.set_column('C:C', 66)
                            sheet.set_column('D:D', 46)
                            sheet.write(row, 0, 'Sl no', format21)
                            sheet.write(row, 1, 'Date', format21)
                            sheet.write(row, 2, 'Question', format21)
                            sheet.write(row, 3, 'Answer', format21)
                            sheet.write(row, 4, 'Score', format21)
                            row += 1
                            a = 1
                            for datas in records.get('data'):
                                if part['user_name'] == datas['user_name']:
                                    sheet.write(row, 0, a, font_size_8)
                                    a = a + 1
                                    sheet.write(row, 1, str(datas.get('create_date').strftime('%d-%m-%Y')),
                                                font_size_8)
                                    sheet.write(row, 2, datas.get('question'),
                                                font_size_8)
                                    sheet.write(row, 3, datas.get('answer'),
                                                font_size_8)
                                    sheet.write(row, 4, datas.get('score'),
                                                font_size_8)
                                    row += 1
                workbook.close()
                output.seek(0)
                return output.read()
                # response.stream.write(output.read())
                # output.close()
