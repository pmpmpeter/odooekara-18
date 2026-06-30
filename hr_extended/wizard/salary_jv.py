from odoo import models, fields, api
from datetime import datetime
import base64
from io import BytesIO
import xlsxwriter

from odoo.exceptions import UserError, ValidationError

class SalaryReportWizard(models.TransientModel):
    _name = 'salaryjv.report.wizard'
    _description = 'Salary JV Report Wizard'

    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")
    salary_structure_id = fields.Many2one('hr.payroll.structure', string="Salary Structure")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Verify'),
        ('paid', 'Paid'),
        ('done', 'Done')
    ], string="PaySheet Status", required=True, default='verify')
    report_based_on = fields.Selection([
        ('batch', 'Batch'),
        ('department', 'Department'),
        ('date', 'Only From and To Date'),
    ], string="Report Based on", required=True, default='batch')
    batch_id = fields.Many2one('hr.payslip.run',string='Batch')
    department_id = fields.Many2one('hr.department',string='Department')
    report_file = fields.Binary(string="Report File", readonly=True)
    file_name = fields.Char(string="File Name", readonly=True)
    partner_ids = fields.Many2many('res.partner', string="Email To")


    def action_generate_report(self):
        workbook = self._prepare_excel_workbook()
        self.report_file = base64.b64encode(workbook)
        self.file_name = f"Salary_Report.xlsx"
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'salaryjv.report.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def _prepare_excel_workbook(self):
        buffer = BytesIO()
        workbook = xlsxwriter.Workbook(buffer)
        sheet = workbook.add_worksheet('Salary JV Data')

        # Define styles
        title_format = workbook.add_format({'bold': True, 'align': 'left', 'font_size': 14})
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'border': 1})
        data_format = workbook.add_format({'align': 'left', 'border': 1,'num_format': '0.00'})
        data_format1 = workbook.add_format({'align': 'left', 'border': 1,'bg_color':'#D3D3D3','num_format': '0.00'})
        char_format = workbook.add_format({'align': 'left', 'border': 1})
        merge_format = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'bold': True,
                'border': 1,
            })
        merge_format1 = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'bold': True,
            'border': 1,
            'bg_color': '#D3D3D3',

        })

        # Title
        sheet.merge_range('A1:Z1','ENTITY - '+self.env.company.name, title_format)
        if self.report_based_on == 'batch':
            sheet.merge_range('A2:E2','Salary Entry for Batch'+' - '+self.batch_id.name , title_format)
        elif self.report_based_on =='date':
            sheet.merge_range('A2:E2','Salary Entry From'+' '+datetime.strftime(self.from_date,"%d-%m-%Y")+' '+'To' +' ' +datetime.strftime(self.to_date,"%d-%m-%Y"),title_format)
        elif elf.report_based_on == 'department':
            sheet.merge_range('A2:Z2', f'Salary Entry for Department {self.department_id.name}', title_format)
        sheet.set_column('A:A',7)
        sheet.set_column('B:C', 20)
        sheet.set_column('D:E',10)
        sheet.set_column('F:F',15)
        sheet.set_column('G:H',20)
        sheet.set_column('I:I',15)
        sheet.set_column('J:J',25)
        sheet.set_column('K:AN',20)
        sheet.set_row(3,28)
        # Headers
        headers = ["Sl #", "Employee","Location"]
        if self.report_based_on == 'batch':
            payslips = self.env['hr.payslip'].search([
                ('payslip_run_id', '=', self.batch_id.id),
                ('state', '=', self.state)
            ])
        elif self.report_based_on == 'department':
            payslips = self.env['hr.payslip'].search([
                ('date_from','>=', self.from_date),
                ('date_to', '<=', self.to_date),
                ('employee_id.department_id', '=', self.department_id.id),
                ('state', '=', self.state)
            ])
        elif self.report_based_on =='date':
            payslips = self.env['hr.payslip'].search([
                ('date_from','>=', self.from_date),
                ('date_to', '<=', self.to_date),
                ('state', '=', self.state)
            ])
        row = 3
        col = 0
        for header in headers:
            sheet.merge_range(2,col,3,col,header, merge_format)
            col += 1

        comp_col = col
        components = payslips.struct_id.rule_ids.filtered(
            lambda l: any(rule.category_id.name in ['Basic', 'Allowance'] for rule in l)
        )
        for comp_name in components.mapped('name'):
            sheet.write(row, comp_col, comp_name, header_format)
            comp_col += 1
        print(row,comp_col,'jjjjjjjjjj')
        sheet.write(row, comp_col, 'Total Debit', header_format)
        comp_col += 1
        ded_col = comp_col
        deduction = payslips.struct_id.rule_ids.filtered(
            lambda l: any(rule.category_id.name in ['Deduction'] for rule in l)
        )
        for comp_name in deduction.mapped('name'):
            sheet.write(row, ded_col, comp_name, header_format)
            ded_col += 1
        sheet.write(row, ded_col, 'Total Credit', header_format)
        sheet.merge_range(2,col,2,comp_col-1, 'Debit', merge_format)
        sheet.merge_range(2,comp_col,2,ded_col-1, 'Credit', merge_format)
        comp_names = components.mapped('name')
        ded_names = deduction.mapped('name')
        row += 1
        comp_fin_list = []
        ded_fin_list = []
        for slip in payslips.filtered(
                lambda l: any(rule.category_id.name in ['Basic', 'Allowance'] for rule in l.struct_id.rule_ids)):
            comp_list = []
            for line in slip.line_ids:
                comp_list.append({line.name: line.total})
            comp_fin_list.append(comp_list)
        for slip in payslips.filtered(
                lambda l: any(rule.category_id.name in ['Deduction'] for rule in l.struct_id.rule_ids)):
            ded_list = []
            total = 0
            for line in slip.line_ids:
                ded_list.append({line.name: line.total})
                total = total + line.total
            ded_fin_list.append(ded_list)
        start_row = row
        start_col = col
        comp_list = []
        total_debit_sum = 0
        total_credit_sum = 0
        for comp in comp_fin_list:
            total = 0
            for idx, component in enumerate(comp_names):
                for item in comp:
                    value = 0
                    if component in item:
                        value = item[component]
                        total = total + int(item[component])

                        break


                sheet.write(start_row, start_col + idx, value, data_format)
                sheet.write(start_row, start_col + 1 + idx, total, data_format)
            print(total,'iiiiiiiiiiiii')
            total_debit_sum += total
            comp_list.append(total)
            start_row += 1
            print('totalllllllllllllllllll', total_debit_sum)
        component_totals = {name: 0.0 for name in comp_names}
        for comp in comp_fin_list:
            for idx, component in enumerate(comp_names):
                value = 0
                for item in comp:
                    if component in item:
                        value = item[component]
                        break
                component_totals[component] += value

        print(component_totals, 'jjjjjjjjjjjj')
        for idx, component in enumerate(comp_names):
            col_index = start_col + idx  # Use same start_col from your data rows
            sheet.write(start_row, col_index, component_totals[component], data_format1)
        sheet.write(start_row, col_index+1, total_debit_sum, data_format1)
        start_row = row
        start_col = comp_col
        ded_list = []
        for comp in ded_fin_list:
            total = 0

            for idx, component in enumerate(ded_names):
                print(start_row, start_col, start_col + idx, value, idx)
                value = 0
                for item in comp:
                    if component in item:
                        value = item[component]
                        total = total + int(item[component])
                sheet.write(start_row, start_col + idx, value, data_format)
            total_col = start_col + len(ded_names)
            sheet.write(start_row, total_col, total, data_format)
            total_credit_sum += total
            ded_list.append(total)
            start_row += 1

        ded_totals = {name: 0.0 for name in ded_names}
        for comp in ded_fin_list:
            for idx, component in enumerate(ded_names):
                value = 0
                for item in comp:
                    if component in item:
                        value = item[component]
                        break
                ded_totals[component] += value
        for idx, component in enumerate(ded_names):
            col_index = start_col + idx  # Use same start_col from your data rows
            sheet.write(start_row, col_index, ded_totals[component], data_format1)
        sheet.write(start_row, col_index+1, total_credit_sum, data_format1)
        print(ded_totals, 'jjjjjjjjjjjj')

        for idx, slip in enumerate(payslips, start=1):
            col = 0
            sheet.write(row, col, idx, char_format)  # Sl #
            sheet.write(row, col +1, slip.employee_id.name, char_format)
            sheet.write(row, col +2 , slip.employee_id.work_location_id.name if slip.employee_id.work_location_id else '', char_format)
            sheet.merge_range(start_row,0, start_row,2, 'Total', merge_format1)
            row += 1
        start_row += 2
        sheet.write(start_row, 0, 'Arrears', header_format)
        workbook.close()
        buffer.seek(0)
        return buffer.read()
