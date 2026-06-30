
import base64

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class HRPayslipInherit(models.Model):
    _inherit = "hr.payslip"

    batch_jv_ref = fields.Many2many('account.batch.jv',string='Batch Jv Ref')

    @api.model
    def create_batch_jv(self):
            entry_id = []
            payslip_run_ids = self.mapped('payslip_run_id')
            payslip_run_ids = payslip_run_ids.filtered(lambda r: r)
            if len(payslip_run_ids) > 1:
                raise ValidationError(
                    "Selected entries belong to multiple payslip batches. Please select entries from the same batch."
                )
            for rec in self:
                ent = rec.move_id.id
                entry_id.append(ent)
            batch = self.env['account.batch.jv'].create({
                'journal_id': self[0].journal_id.id,
                'journal_ids':[(4, eid) for eid in entry_id],
                'hr_payslip_run_id' : payslip_run_ids.id
            })
            for r in self:
                r.batch_jv_ref = [(4, batch.id)]

            return {
                "type": "ir.actions.act_window",
                "res_model": "account.batch.jv",
                "views": [[False, "form"]],
                "res_id": batch.id,
            }
