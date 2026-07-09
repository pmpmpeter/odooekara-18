from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning

class AccountReportBudget(models.Model):
    _name = 'account.report.budget'
    _inherit = ['account.report.budget', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    sequence = fields.Integer(tracking=True)

    company_id = fields.Many2one('res.company',required=True,copy=False,default=lambda self: self.env.company,)

    budget_type = fields.Selection(
        [
            ('capex', 'Capex'),
            ('opex', 'Opex'),
            ('ocif', 'OCIF'),
            ('noocif', 'NOOCIF'),
        ],
        tracking=True,
        index=True,
    )

    budget_category = fields.Selection(
        [
            ('regular', 'Regular'),
            ('consolidate', 'Consolidate'),
        ],
        tracking=True,
    )

    state = fields.Selection(
        [
            ('locked', 'Locked'),
            ('unlocked', 'Unlocked'),
        ],
        default='unlocked',
        tracking=True,
    )

    is_locked = fields.Integer()   # Consider Boolean if possible.

    def action_lock(self):
        self.write({'state': 'locked'})

    def action_unlock(self):
        self.write({'state': 'unlocked'})