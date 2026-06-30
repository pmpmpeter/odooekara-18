from markupsafe import Markup

from odoo import _, api, Command, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare

class L10nInWithholdWizardLine(models.TransientModel):
    _inherit = 'l10n_in.withhold.wizard.line'

    amount = fields.Monetary(
        string="TDS11111 Amount",
        store=True,
    )

    @api.onchange('tax_id', 'base')
    def _onchange_tax_amount(self):
        # Recomputes amount according to "base amount" and tax percentage
        for line in self:
            tax_amount = 0.0
            if line.tax_id:
                tax_amount = line._tax_compute_all_helper(line.base, line.tax_id)
            line.amount = tax_amount

    @api.depends('tax_id', 'base')
    def _compute_amount(self):
        # Recomputes amount according to "base amount" and tax percentage
        for line in self:
            tax_amount = 0.0
            if line.tax_id:
                tax_amount = line._tax_compute_all_helper(line.base, line.tax_id)
            line.amount = tax_amount
            # pass
