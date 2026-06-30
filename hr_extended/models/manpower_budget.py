from odoo import models, fields, api
import pytz
import xlsxwriter
import base64
import io
from datetime import datetime
from pytz import timezone
from odoo.exceptions import UserError, ValidationError


class ManpowerBudget(models.Model):
    _name = 'manpower.budget'
    _description = 'Manpower Budget'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # Enable chatter functionality
    _rec_name = 'name'

    @api.depends('employee_monthly_ids')
    def _compute_ctc_annual(self):
        for rec in self:
            for line in rec.employee_monthly_ids:
                rec.ctc_annual += (line.ctc_month * line.employee_count)

    @api.depends('employee_monthly_ids')
    def _compute_ctc_month(self):
        for rec in self:
            for line in rec.employee_monthly_ids:
                rec.ctc_monthly += (line.ctc_month)

    name = fields.Char(string='Reference', required=True, readonly=True, default='New')
    create_date = fields.Datetime(string="Creation Date", readonly=True, default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', string="User", default=lambda self: self.env.user, readonly=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, readonly=True)
    tax_entity_id = fields.Many2one('res.company', string="Tax Entity")
    category_id = fields.Many2one('hr.contract.type', string="Category")
    manpower_request_type = fields.Selection([
        ('existing', 'Existing'),
        ('additional', 'Additional')
    ], string="Type of Manpower Request")
    business_unit_id = fields.Many2one('business.units',domain="[('company_id', '=', company_id)]", string="Business Unit")
    department_id = fields.Many2one('hr.department',domain="[('company_id', '=', company_id)]", string="Department")
    job_id = fields.Many2one('hr.job',domain="[('company_id', '=', company_id)]", string="Role/Designation")
    position_id = fields.Many2one('hr.position.names',domain="[('company_id', '=', company_id)]", string="Role/Designation")
    job_level_id = fields.Many2one('hr.job.levels',domain="[('company_id', '=', company_id)]", string="Job Level/Grade")
    justification = fields.Char(string="Justification")
    ctc_annual = fields.Float(string="CTC-Annual",compute='_compute_ctc_annual')
    ctc_monthly = fields.Float(string="CTC-Month", compute='_compute_ctc_month')
    employee_monthly_ids = fields.One2many(
        'manpower.budget.employee.monthly',
        'budget_id',
        string="Employee Count by Month",
        default=lambda self: self._default_employee_monthly_ids(),
        tracking=True
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('assigned', 'Assigned'),
            ('submitted', 'Submitted'),
            ('hr_approved', 'HR Head Approved'),
            ('done', 'Done')
        ],
        string='Status',
        default='draft',
        required=True
    )
    assigned_user_id = fields.Many2one('res.users',string='Assigned To')
    hr_id = fields.Many2one('res.users',string='Assigned By')
    director_id = fields.Many2one('res.users',string='Director')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('manpower.budget') or 'New'
        return super(ManpowerBudget, self).create(vals)

    def action_assign_user(self):
        self.write({'state': 'assigned'})

        # Notify the assigned user via email
        if self.assigned_user_id:
            # Construct the URL to the record
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            record_url = f"{base_url}/web#id={self.id}&model=manpower.budget&view_type=form"

            # Prepare email content
            subject = 'You have been assigned to a Manpower Budget'
            body_html = f"""
                <p>Hello {self.assigned_user_id.name},</p>
                <p>You have been assigned to a Manpower Budget.</p>
                <p>Click <a href="{record_url}">here</a> to view the record.</p>
            """

            # Create and send the email
            mail_values = {
                'subject': subject,
                'body_html': body_html,
                'email_to': self.assigned_user_id.email,  # Send email to the assigned user's email address
                'email_from': self.env.user.email or 'no-reply@example.com',  # Sender's email
            }
            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.sudo().send()


    def action_submit_record(self):
        self.write({'state': 'submitted'})
        if self.ctc_annual == 0 :
            raise UserError('Kindly enter Employee Count and CTC/Month')

        if self.hr_id:
            # Construct the URL to the record
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            record_url = f"{base_url}/web#id={self.id}&model=manpower.budget&view_type=form"

            # Prepare email content
            subject = 'Manpower Budget has been submitted'
            body_html = f"""
                <p>Hello {self.hr_id.name},</p>
                <p>The Budget {self.name },as been submitted by {self.assigned_user_id.name}</p>
                <p>Click <a href="{record_url}">here</a> to view the record.</p>
            """

            # Create and send the email
            mail_values = {
                'subject': subject,
                'body_html': body_html,
                'email_to': self.hr_id.email,  # Send email to the assigned user's email address
                'email_from': self.env.user.email or 'no-reply@example.com',  # Sender's email
            }
            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.sudo().send()

    def action_hr_approve(self):
        self.write({'state': 'hr_approved'})

    def action_set_done(self):
        self.write({'state': 'done'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})




    @api.model
    def _default_employee_monthly_ids(self):
        """Generate default employee_monthly_ids for financial year months."""
        financial_year_months = [
            ('04', 'April'), ('05', 'May'), ('06', 'June'),
            ('07', 'July'), ('08', 'August'), ('09', 'September'),
            ('10', 'October'), ('11', 'November'), ('12', 'December'),
            ('01', 'January'), ('02', 'February'), ('03', 'March'),
        ]
        current_year = fields.Date.today().year
        next_year = current_year + 1
        employee_lines = []
        for month_code, month_name in financial_year_months:
            year = current_year if int(month_code) >= 4 else next_year
            employee_lines.append({
                'month': month_code,
                'employee_count': 0,  # Default employee count
            })
        return [(0, 0, line) for line in employee_lines]


    def action_export_excel(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('manpower_budget_sheet')
        year= self.get_financial_year(fields.Date.today())
        y_1 = year['year_one']
        y_2 = year['year_two']

        # sheet.protect()
        merge_format1 = workbook.add_format({'bold': 1,'border': 1,'align': 'center','text_wrap': True,'valign': 'vcenter',})
        merge_format2 = workbook.add_format({'bold': 1,'border': 1,'align': 'center','valign': 'vcenter','border_color': '#000000','fg_color': '#c5e0b3','text_wrap': True,})
        merge_format3 = workbook.add_format({'bold': 1,'border': 1,'align': 'center','valign': 'vcenter','border_color': '#000000','fg_color': '#b4c6e7','text_wrap': True,})
        merge_format4 = workbook.add_format({'bold': 1,'border': 1,'align': 'center','valign': 'vcenter','border_color': '#000000','fg_color': '#FFFF00','text_wrap': True,})
        merge_format5 = workbook.add_format({'bold': 1,'border': 1,'align': 'center','valign': 'vcenter','border_color': '#000000','fg_color': '#fbe4d5','text_wrap': True,})

        sheet.set_column('A:A', 30)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 40)
        sheet.set_column('D:D', 15)
        sheet.set_column('E:E', 20)
        sheet.set_column('F:F', 20)
        sheet.set_column('G:G', 15)
        sheet.set_column('H:H', 15)
        sheet.set_column('I:I', 15)
        sheet.set_column('J:J', 15)
        sheet.set_column('K:K', 15)
        sheet.set_column('L:L', 15)
        sheet.set_column('M:M', 15)
        sheet.set_column('N:N', 15)
        sheet.set_column('O:O', 15)
        sheet.set_column('P:J', 15)
        sheet.set_column('Q:Q', 15)
        sheet.set_column('R:R', 15)
        sheet.set_column('S:S', 15)
        sheet.set_column('T:T', 15)
        sheet.set_column('U:U', 15)
        sheet.set_column('V:V', 15)
        sheet.set_column('W:W', 15)
        sheet.set_column('X:X', 15)
        sheet.set_column('Y:Y', 15)
        sheet.set_column('Z:Z', 15)
        sheet.set_column('AA:AA', 15)
        sheet.set_column('AB:AB', 15)
        sheet.set_column('AC:AC', 15)
        sheet.set_column('AD:AD', 15)
        sheet.set_column('AE:AE', 15)
        sheet.set_column('AG:AG', 15)
        sheet.set_column('AH:AH', 15)
        sheet.set_column('AI:AI', 15)
        sheet.write(5, 0, "Tax Entity", merge_format3)
        sheet.write(0, 0, "Guideline", merge_format2)
        sheet.write(3, 0, " Manpower for FY "+str(y_1)+'-'+str(y_2), merge_format1)
        sheet.write(5, 1, "Category", merge_format3)
        sheet.write(5, 2, "Type of \n Manpower Request", merge_format3)
        sheet.write(5, 3, "Business Unit", merge_format3)
        sheet.write(5, 4, "Department", merge_format3)
        sheet.write(5, 5, "Role/Designation", merge_format3)
        sheet.write(5, 6, "Job Level/Grade", merge_format3)
        sheet.write(5, 7, "Justification", merge_format3)
        sheet.write(5, 8, "CTC/Annual", merge_format3)
        sheet.merge_range('J5:U5', 'No. of Employees', merge_format1)
        sheet.merge_range('X5:AI5', 'Total Salary Per Month', merge_format1)
        sheet.merge_range('D2:H2', 'If an employee is added in month 1, pls consider that employee for all the 12 months', merge_format1)
        sheet.merge_range('D1:I1', 'Kindly fill the details of existing Manpower/additional Manpower to be recruited for Budget Year FY '+str(y_1)+'-'+str(y_2), merge_format1)
        sheet.write(5, 9, "Apr/"+str(y_1), merge_format4)
        sheet.write(5, 10, "May/"+str(y_1), merge_format4)
        sheet.write(5, 11, "Jun/"+str(y_1), merge_format4)
        sheet.write(5, 12, "Jul/"+str(y_1), merge_format4)
        sheet.write(5, 13, "Aug/"+str(y_1), merge_format4)
        sheet.write(5, 14, "Sep/"+str(y_1), merge_format4)
        sheet.write(5, 15, "Oct/"+str(y_1), merge_format4)
        sheet.write(5, 16, "Nov/"+str(y_1), merge_format4)
        sheet.write(5, 17, "Dec/"+str(y_1), merge_format4)
        sheet.write(5, 18, "Jan/"+str(y_2), merge_format4)
        sheet.write(5, 19, "Feb/"+str(y_2), merge_format4)
        sheet.write(5, 20, "Mar/"+str(y_2), merge_format4)
        sheet.write(5, 21, "FY "+str(y_1)+'-'+str(y_2), merge_format4)
        sheet.write(5, 22, "", merge_format5)
        sheet.write(5, 23, "Apr/"+str(y_1), merge_format4)
        sheet.write(5, 24, "May/"+str(y_1), merge_format4)
        sheet.write(5, 25, "Jun/"+str(y_1), merge_format4)
        sheet.write(5, 26, "Jul/"+str(y_1), merge_format4)
        sheet.write(5, 27, "Aug/"+str(y_1), merge_format4)
        sheet.write(5, 28, "Sep/"+str(y_1), merge_format4)
        sheet.write(5, 29, "Oct/"+str(y_1), merge_format4)
        sheet.write(5, 30, "Nov/"+str(y_1), merge_format4)
        sheet.write(5, 31, "Dec/"+str(y_1), merge_format4)
        sheet.write(5, 32, "Jan/"+str(y_2), merge_format4)
        sheet.write(5, 33, "Feb/"+str(y_2), merge_format4)
        sheet.write(5, 34, "Mar/"+str(y_2), merge_format4)
        sheet.set_row(0,40)
        sheet.set_row(1,40)
        sheet.set_row(5,30)
        row = 6
        active_ids = self.env.context.get('active_ids', [])
        if not active_ids:
            raise UserError("No records selected!")

        # Retrieve the selected records
        selected_records = self.browse(active_ids)
        if selected_records:
            for manpower in selected_records:
                sheet.write(row, 0,manpower.tax_entity_id.name if manpower.tax_entity_id.name else '')
                sheet.write(row, 1,manpower.category_id.name if manpower.category_id.name else '')
                sheet.write(row, 2,manpower.manpower_request_type if manpower.manpower_request_type else '')
                sheet.write(row, 3,manpower.business_unit_id.name if manpower.business_unit_id.name else '')
                sheet.write(row, 4,manpower.department_id.name if manpower.department_id.name else '')
                sheet.write(row, 5,manpower.job_id.name if manpower.job_id.name else '')
                sheet.write(row, 6,manpower.job_level_id.name if manpower.job_level_id.name else '')
                sheet.write(row, 7,manpower.justification if manpower.justification else '')
                sheet.write(row, 8,manpower.ctc_annual if manpower.ctc_annual else '')
                col = 9
                for line in manpower.employee_monthly_ids:
                    sheet.write(row,col, line.employee_count)
                    col+=1
                col = 23
                for line in manpower.employee_monthly_ids:
                    sheet.write(row,col,line.ctc_month)
                    col+=1
                row += 1
        workbook.close()
        output.seek(0)

        # Encode the file and return it
        file_data = base64.b64encode(output.read())
        output.close()
        attachment = self.env['ir.attachment'].create({
            'name': 'Manpower_Budget_Report.xlsx',
            'type': 'binary',
            'datas': file_data,
            'res_model': self._name,
            'res_id': self.id,  # You can link it to the first selected record or a dummy record
            'mimetype': 'application/vnd.ms-excel',
        })
       
        # Generate a URL for the file download
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }


    def action_send_export_excel_for_approval(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('manpower_budget_sheet')
        year= self.get_financial_year(fields.Date.today())
        y_1 = year['year_one']
        y_2 = year['year_two']

        # sheet.protect()
        merge_format1 = workbook.add_format({'bold': 1,'border': 1,'align': 'center','text_wrap': True,'valign': 'vcenter',})
        merge_format2 = workbook.add_format({'bold': 1,'border': 1,'align': 'center','valign': 'vcenter','border_color': '#000000','fg_color': '#c5e0b3','text_wrap': True,})
        merge_format3 = workbook.add_format({'bold': 1,'border': 1,'align': 'center','valign': 'vcenter','border_color': '#000000','fg_color': '#b4c6e7','text_wrap': True,})
        merge_format4 = workbook.add_format({'bold': 1,'border': 1,'align': 'center','valign': 'vcenter','border_color': '#000000','fg_color': '#FFFF00','text_wrap': True,})
        merge_format5 = workbook.add_format({'bold': 1,'border': 1,'align': 'center','valign': 'vcenter','border_color': '#000000','fg_color': '#fbe4d5','text_wrap': True,})

        sheet.set_column('A:A', 30)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 40)
        sheet.set_column('D:D', 15)
        sheet.set_column('E:E', 20)
        sheet.set_column('F:F', 20)
        sheet.set_column('G:G', 15)
        sheet.set_column('H:H', 15)
        sheet.set_column('I:I', 15)
        sheet.set_column('J:J', 15)
        sheet.set_column('K:K', 15)
        sheet.set_column('L:L', 15)
        sheet.set_column('M:M', 15)
        sheet.set_column('N:N', 15)
        sheet.set_column('O:O', 15)
        sheet.set_column('P:J', 15)
        sheet.set_column('Q:Q', 15)
        sheet.set_column('R:R', 15)
        sheet.set_column('S:S', 15)
        sheet.set_column('T:T', 15)
        sheet.set_column('U:U', 15)
        sheet.set_column('V:V', 15)
        sheet.set_column('W:W', 15)
        sheet.set_column('X:X', 15)
        sheet.set_column('Y:Y', 15)
        sheet.set_column('Z:Z', 15)
        sheet.set_column('AA:AA', 15)
        sheet.set_column('AB:AB', 15)
        sheet.set_column('AC:AC', 15)
        sheet.set_column('AD:AD', 15)
        sheet.set_column('AE:AE', 15)
        sheet.set_column('AG:AG', 15)
        sheet.set_column('AH:AH', 15)
        sheet.set_column('AI:AI', 15)
        sheet.write(5, 0, "Tax Entity", merge_format3)
        sheet.write(0, 0, "Guideline", merge_format2)
        sheet.write(3, 0, " Manpower for FY "+str(y_1)+'-'+str(y_2), merge_format1)
        sheet.write(5, 1, "Category", merge_format3)
        sheet.write(5, 2, "Type of \n Manpower Request", merge_format3)
        sheet.write(5, 3, "Business Unit", merge_format3)
        sheet.write(5, 4, "Department", merge_format3)
        sheet.write(5, 5, "Role/Designation", merge_format3)
        sheet.write(5, 6, "Job Level/Grade", merge_format3)
        sheet.write(5, 7, "Justification", merge_format3)
        sheet.write(5, 8, "CTC/Annual", merge_format3)
        sheet.merge_range('J5:U5', 'No. of Employees', merge_format1)
        sheet.merge_range('X5:AI5', 'Total Salary Per Month', merge_format1)
        sheet.merge_range('D2:H2', 'If an employee is added in month 1, pls consider that employee for all the 12 months', merge_format1)
        sheet.merge_range('D1:I1', 'Kindly fill the details of existing Manpower/additional Manpower to be recruited for Budget Year FY '+str(y_1)+'-'+str(y_2), merge_format1)
        sheet.write(5, 9, "Apr/"+str(y_1), merge_format4)
        sheet.write(5, 10, "May/"+str(y_1), merge_format4)
        sheet.write(5, 11, "Jun/"+str(y_1), merge_format4)
        sheet.write(5, 12, "Jul/"+str(y_1), merge_format4)
        sheet.write(5, 13, "Aug/"+str(y_1), merge_format4)
        sheet.write(5, 14, "Sep/"+str(y_1), merge_format4)
        sheet.write(5, 15, "Oct/"+str(y_1), merge_format4)
        sheet.write(5, 16, "Nov/"+str(y_1), merge_format4)
        sheet.write(5, 17, "Dec/"+str(y_1), merge_format4)
        sheet.write(5, 18, "Jan/"+str(y_2), merge_format4)
        sheet.write(5, 19, "Feb/"+str(y_2), merge_format4)
        sheet.write(5, 20, "Mar/"+str(y_2), merge_format4)
        sheet.write(5, 21, "FY "+str(y_1)+'-'+str(y_2), merge_format4)
        sheet.write(5, 22, "", merge_format5)
        sheet.write(5, 23, "Apr/"+str(y_1), merge_format4)
        sheet.write(5, 24, "May/"+str(y_1), merge_format4)
        sheet.write(5, 25, "Jun/"+str(y_1), merge_format4)
        sheet.write(5, 26, "Jul/"+str(y_1), merge_format4)
        sheet.write(5, 27, "Aug/"+str(y_1), merge_format4)
        sheet.write(5, 28, "Sep/"+str(y_1), merge_format4)
        sheet.write(5, 29, "Oct/"+str(y_1), merge_format4)
        sheet.write(5, 30, "Nov/"+str(y_1), merge_format4)
        sheet.write(5, 31, "Dec/"+str(y_1), merge_format4)
        sheet.write(5, 32, "Jan/"+str(y_2), merge_format4)
        sheet.write(5, 33, "Feb/"+str(y_2), merge_format4)
        sheet.write(5, 34, "Mar/"+str(y_2), merge_format4)
        sheet.set_row(0,40)
        sheet.set_row(1,40)
        sheet.set_row(5,30)
        row = 6
        active_ids = self.env.context.get('active_ids', [])
        if not active_ids:
            raise UserError("No records selected!")

        # Retrieve the selected records
        selected_records = self.browse(active_ids)
        if selected_records:
            for manpower in selected_records:
                sheet.write(row, 0,manpower.tax_entity_id.name)
                sheet.write(row, 1,manpower.category_id.name)
                sheet.write(row, 2,manpower.manpower_request_type)
                sheet.write(row, 3,manpower.business_unit_id.name)
                sheet.write(row, 4,manpower.department_id.name)
                sheet.write(row, 5,manpower.job_id.name)
                sheet.write(row, 6,manpower.job_level_id.name)
                sheet.write(row, 7,manpower.justification)
                sheet.write(row, 8,manpower.ctc_annual)
                col = 9
                for line in manpower.employee_monthly_ids:
                    sheet.write(row,col, line.employee_count)
                    col+=1
                col = 23
                for line in manpower.employee_monthly_ids:
                    sheet.write(row,col,line.ctc_month)
                    col+=1
                row += 1
        workbook.close()
        output.seek(0)

        # Encode the file and return it
        file_data = base64.b64encode(output.read())
        output.close()
        attachment = self.env['ir.attachment'].create({
            'name': 'Manpower_Budget_Report.xlsx',
            'type': 'binary',
            'datas': file_data,
            'res_model': self._name,
            'res_id': self.id,  # You can link it to the first selected record or a dummy record
            'mimetype': 'application/vnd.ms-excel',
        })
        email_to = manpower.director_id.email
        user = manpower.director_id
        if not email_to:
                raise ValidationError("In-app notifications can be sent to users with mail ID")
        else:
            record = self.browse(active_ids)
            record.activity_schedule(
                activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                summary="Manpower Budget Reminder: Manpower Budget reminder",
                note=f"Kindly Verify the Manpower Budget.",
                user_id=user.id,
                date_deadline=fields.Date.today()
            )
        if not email_to:
            raise UserError("Director's email address is not configured!")

        subject = 'Manpower Budget Approval Required'
        body_html = """
            <p>Dear Director,</p>
            <p>Please find the attached manpower budget report for your approval.</p>
            <p>Kind Regards,</p>
            <p>Your Team</p>
        """

        # Send the email with the attachment
        mail_values = {
            'subject': subject,
            'body_html': body_html,
            'email_to': email_to,
            'attachment_ids': [(0, 0, {
                'name': 'Manpower_Budget_Report.xlsx',
                'datas': file_data,
                'mimetype': 'application/vnd.ms-excel',
            })],
        }
        self.env['mail.mail'].sudo().create(mail_values).send()
        self.env['director.approve.manpower'].sudo().create({'from_date':fields.datetime.today(),'to_date':fields.datetime.today(),'report':attachment.id,'report_name':'Manpower_Budget_Report.xlsx'})

        # Confirmation message
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success!',
                'message': 'Email with the manpower budget report has been sent to the Director.',
                'type': 'success',
                'sticky': False,
            },
        }
    def schedule_activity(self):
        print(self,'hhhhhhhhhhhh')
        email_to = self.director_id.email
        user = self.director_id
        self.activity_schedule(
            activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
            summary="Manpower Budget Reminder: Manpower Budget reminder",
            note=f"Kindly Verify the Manpower Budget.",
            user_id=user.id,
            date_deadline=fields.Date.today()
        )
    # def _schedule_activity(self):
    #     user = self.director_id
    #     print('jjjjjjjjjjjjjgggggggggggggggg')
    #     self.activity_schedule(
    #         activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
    #         summary="Manpower Budget Reminder",
    #         note=f"Kindly Verify the Manpower Budget: {self.name}.",
    #         user_id=user.id,
    #         date_deadline=fields.Date.today()
    #     )

    def get_financial_year(self,current_date):
        current_year = current_date.year
        # Define fiscal year start month (e.g., April = 4)
        fiscal_start_month = 4
        # Determine financial year range
        if current_date.month >= fiscal_start_month:
            start_year = current_year
            end_year = current_year + 1
        else:
            start_year = current_year - 1
            end_year = current_year

        return {'year_one':start_year,'year_two':end_year}



class ManpowerBudgetEmployeeMonthly(models.Model):
    _name = 'manpower.budget.employee.monthly'
    _description = 'Manpower Budget Employee Monthly Count'

    budget_id = fields.Many2one('manpower.budget', string="Manpower Budget")
    month = fields.Selection([
        ('04', 'April'), ('05', 'May'), ('06', 'June'),
        ('07', 'July'), ('08', 'August'), ('09', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December'),
        ('01', 'January'), ('02', 'February'), ('03', 'March'),
    ], string="Month")
    employee_count = fields.Integer(string="Position Count", required=True)
    ctc_month = fields.Float(string='CTC/Month')



class DirectorApproveManpower(models.Model):
    _name = 'director.approve.manpower'
    _description = 'Director Approve Manpower'
    _rec_name = 'report'

    from_date = fields.Date(string="From Date", required=True)
    to_date = fields.Date(string="To Date", required=True)
    report = fields.Many2one('ir.attachment',string="Attachment")
    report_name = fields.Char(string="Report Filename")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, readonly=True)
    state = fields.Selection(
        [('waiting','Waiting For Approve'),('approved', 'Approved'), ('rejected', 'Rejected')],
        string="Status",
        default='waiting',
        tracking=True
    )
    
    def get_attachment_url(self):
        if self.report:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{self.report.id}?download=true',
                'target': 'self',
            }

    def action_approve(self):
        for record in self:
            record.state = 'approved'

    def action_reject(self):
        for record in self:
            record.state = 'rejected'
