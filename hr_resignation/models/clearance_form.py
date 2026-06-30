from odoo import models, fields, api, _
from odoo.exceptions import *
from odoo.exceptions import ValidationError, UserError


class ClearanceForm(models.Model):
    _name = 'clearance.form'
    _description = 'Clearance Form'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', string='Employee Name', domain="[('company_id', '=', company_id)]",
                                  required=True, tracking=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company,
                                 domain=lambda self: [('id', '=', (self.env.company.id))])
    designation_id = fields.Many2one('hr.job', domain="[('company_id', '=', company_id)]", string="Designation",
                                     tracking=True)
    date_of_joining = fields.Date(string='Date of Joining', tracking=True)
    department_id = fields.Many2one('hr.department', domain="[('company_id', '=', company_id)]", string='Department',
                                    tracking=True)
    last_working_day = fields.Date(string='Last Working Day', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('completed', 'Completed'),
    ], string='Status', default='draft', tracking=True)
    asset_ids = fields.One2many('clearance.asset', 'clearance_form_id', string='Assets')
    function_head_ids = fields.One2many('clearance.function.head', 'clearance_form_id',
                                        string='Clearance by Function Heads')

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for record in self:
            if record.employee_id:
                record.designation_id = record.employee_id.job_id
                record.department_id = record.employee_id.department_id
                record.date_of_joining = record.employee_id.joining_date
                record.last_working_day = record.employee_id.resign_date

    def clearance_form_submit(self):
        for record in self:
            record.state = 'submitted'

    def clearance_form_complete(self):
        for record in self:
            record.state = 'completed'

    def clearance_form_draft(self):
        for record in self:
            record.state = 'draft'

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Only records in the 'Draft' state can be deleted."))
        return super(ClearanceForm, self).unlink()


class ClearanceAsset(models.Model):
    _name = 'clearance.asset'
    _description = 'Clearance Asset'

    asset_type = fields.Selection([
        ('laptop', 'Laptop'),
        ('sim_card', 'SIM Card'),
        ('mobile_handset', 'Mobile Handset'),
        ('ipad', 'iPad'),
        ('data_card', 'Data Card/Dongle'),
        ('access_card', 'Access Card'),
        ('photo_id', 'Photo ID'),
        ('system', 'System'),
        ('email_gpm', 'Email & GPM - ID/PW'),
        ('library_books', 'Library Books'),
    ], string='Asset')
    asset_category_id = fields.Many2one('assets.category', string="Asset", required=True)
    returned_to = fields.Many2one('hr.employee', string='Returned To', domain="[('company_id', '=', company_id)]",
                                  required=True)
    remarks = fields.Text(string='Remarks')
    signature = fields.Binary(string='Signature')
    clearance_form_id = fields.Many2one('clearance.form', string='Clearance Form', required=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company,
                                 domain=lambda self: [('id', '=', (self.env.company.id))])


class ClearanceFunctionHead(models.Model):
    _name = 'clearance.function.head'
    _description = 'Clearance by Function Head'

    function = fields.Selection([
        ('business_head', 'Business Head'),
        ('reporting_manager', 'Reporting Manager'),
        ('admin', 'Admin'),
        ('it', 'IT'),
        ('accounts', 'Accounts'),
        ('corporate_hr', 'Corporate HR'),
    ], string='Function', required=True)

    remarks = fields.Text(string='Remarks')
    signature = fields.Binary(string='Signature')

    clearance_form_id = fields.Many2one('clearance.form', string='Clearance Form', required=True)
