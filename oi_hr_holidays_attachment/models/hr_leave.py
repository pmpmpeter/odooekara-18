'''
Created on Jan 9, 2019

@author: Zuhair Hammadi
'''
from odoo import models, api, _, fields
from odoo.exceptions import ValidationError

class HolidaysRequest(models.Model):
    _inherit = "hr.leave"

    request_date_from_period = fields.Selection([
        ('am', 'Session 1'), ('pm', 'Session 2')],
        string="Date Period Start", default='am')

    @api.constrains('state','holiday_status_id', 'number_of_days')
    def _check_attachment(self):
        if self.env.context.get('leave_skip_attachment_check', False):
            return

        for record in self:
            if record.state not in ['draft', 'cancel', 'refuse'] and record.holiday_status_id.attachment_required and record.number_of_days > 3:
                if not self.env['ir.attachment'].search([('res_model','=', self._name), ('res_id','=', record.id)], limit = 1):
                    raise ValidationError(_('You cannot send the leave request without attaching a document.'))

    def write(self, vals):
        result = super(HolidaysRequest, self).write(vals)
        self._check_attachment()
        return result
