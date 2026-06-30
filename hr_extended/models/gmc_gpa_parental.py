# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date
from odoo.exceptions import ValidationError, UserError

class GmcGpaParental(models.Model):
    _name = 'gmcgpa.parental'
    _description = 'GMC GPA Parental'
    _rec_name = "employee_id"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    emp_code = fields.Char(string="Employee Code")
    employee_id = fields.Many2one('hr.employee', string="Employee Name")
    email = fields.Char(string="Email")
    contact_no = fields.Char(string="Contact Number")

    dependent_name = fields.Char(string="Dependent Name")
    relationship = fields.Char(string="Relationship")
    age = fields.Integer(string="Age")
    gender = fields.Selection([('male', 'Male'),
                               ('female', 'Female'),
                               ('other', 'Other')], required = True, string="Gender")

    designation = fields.Char(string="Designation")  # job_title
    doj = fields.Date(string="Date of Joining")
    dob = fields.Date(string="Date of Birth", required=False)
    lwd = fields.Date(string="Last Working Day", required=False)

    sum_insured_gmc = fields.Float(string="GMC Sum Insured")
    sum_insured_gpa = fields.Float(string="GPA Sum Insured")
    insurance_type = fields.Selection([('gmc', 'GMC'), ('gpa', 'GPA')], string="Insurance Type")

    company_id = fields.Many2one('res.company',string="Company")
    state = fields.Selection(
        [('draft', 'Draft'),
         ('active', 'Active'),
         ('inactive', 'Inactive'),
         ('terminated', 'Terminated')],
        default='draft', string="Status")
    remarks = fields.Text(string="Remarks")

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            # self.emp_code = self.employee_id.employee_number
            self.email = self.employee_id.work_email
            self.contact_no = self.employee_id.work_phone
            self.designation = self.employee_id.job_title
            self.company_id = self.employee_id.company_id.id

    @api.onchange('dob')
    def _compute_age(self):
        for record in self:
            if record.dob:
                today = date.today()
                dob = record.dob
                record.age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            else:
                record.age = 0

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Only records in the 'Draft' state can be deleted."))
        return super(GmcGpaParental, self).unlink()
