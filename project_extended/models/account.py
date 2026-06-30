from odoo import models, api, _
from odoo.exceptions import AccessError, UserError, ValidationError

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.constrains('partner_id')
    def validate_legacy_notice(self):
        for rec in self:
            legacy_notice = self.env["project.project"].search([('is_legal_notice','=', True), ('partner_id','=', rec.partner_id.id)])
            if legacy_notice:
                raise ValidationError(_(f"Legal notice {','.join(legacy_notice.mapped('name'))} is mapped to the customer ."))

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.constrains('partner_id')
    def validate_legacy_notice(self):
        for rec in self:
            legacy_notice = self.env["project.project"].search([('is_legal_notice','=', True), ('partner_id','=', rec.partner_id.id)])
            if legacy_notice:
                raise ValidationError(_(f"Legal notice {','.join(legacy_notice.mapped('name'))} is mapped to the customer ."))


