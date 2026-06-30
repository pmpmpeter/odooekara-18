from odoo import api, fields, models, _, Command, tools
from odoo.exceptions import UserError, AccessError,ValidationError
import datetime
from datetime import date, timedelta, datetime

class PurchaseType(models.Model):
    _name='purchase.orders.type'
    _description = 'Purchase Types'

    name = fields.Char(string='Purchase Types', required=1)
    # sequence = fields.Many2one('ir.sequence',string='Sequence' ,required=1)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.constrains("name")
    def unique_name(self):
        for record in self:
            domain = [("name", "=ilike", record.name), ("id", "!=", record.id)]
            duplicate = self.search(domain)
            if duplicate:
                raise ValidationError(
                    _("The type '%s' already exists. Please choose a different name.") % record.name
                )
