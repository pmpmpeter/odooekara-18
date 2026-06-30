from odoo import models, fields, api
from odoo.exceptions import UserError


class EmployeeJoinDocConfig(models.Model):
    _name = "employee.join.doc.config"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Employee Join Document Configuration"

    name = fields.Char(string="Name")
    document_type = fields.Selection(
        [('it_declaration', 'IT Declaration'),
         ('ebp_claim', 'EBP Claim Form'),
         ('app_order_form', 'Appointment Order Form'),
         ('bgv', 'BGV Email Template'),
         ('code_of_conduct', 'CODE OF CONDUCT'),
         ('consent', 'Consent Form'),
         ('criminal_case', 'Criminal Case'),
         ('emp_verifi_form', 'Employee Verification Form'),
         ('epf', 'EPF Form 11 Declaration Doc'),
         ('ex_media_comm', 'External Media Communication - Declaration (IIM)'),
         ('gmc', 'GMC and GPA Details'),
         ('joining_form', 'Joining form'),
         ('nda', 'NDA (Intellectual Property) Form'),
         ('pf_nomination', 'PF Nomination Form'),
         ('emp_ref_check', 'Pre - Employment Reference Check Form'),
         ('she_nda', 'SHE NDA- 2022 updated Form')],
        string="Document Type")
    active = fields.Boolean('Active', default=True)
    file = fields.Binary(attachment=True, string="File")
    file_name = fields.Char(string="File Name")
    subject = fields.Html(string="Subject")
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company,
                                 domain=lambda self: [('id', 'in', self.env.companies.ids)], readonly=True)
    contact_id = fields.Many2one('res.partner', 'Contact', copy=False)
    sequence = fields.Integer(string="Sequence")

    def unlink(self):
        for record in self:
            if record.active:
                raise UserError("You can't delete a record in Active.")
        return super(EmployeeJoinDocConfig, self).unlink()
