from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning
from datetime import timedelta
import pdb

class AccountSubGroup(models.Model):
    _name = "account.subgroup"
    _description = 'Account Sub Group'

    name = fields.Char(
        string="SubGroup Name",required=1,
        Copy=True,company_dependent = True
    )
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    account_id = fields.Many2many('account.account',string='Accounts')

    def write(self,vals):
        for rec in self:
            res = super().write(vals)
            if rec.account_id:
                for account in rec.account_id:
                    coa = self.env['account.account'].sudo().search([('name','=',account.name)])
                    for coa_s in coa:
                        if coa_s.id in rec.account_id.ids:
                            coa_s.subgroup = rec
                        else:
                            coa_s.subgroup = ''
                coa_rec =  self.env['account.account'].sudo().search([('subgroup','=',rec.name)])
                for coa_acc in coa_rec:
                    if coa_acc.id not in rec.account_id.ids:
                        coa_acc.subgroup = ''

            if not rec.account_id:
                    coa = self.env['account.account'].sudo().search([('subgroup','=',rec.name)])
                    for coa_rec in coa:
                        coa_rec.subgroup = ''
            return res