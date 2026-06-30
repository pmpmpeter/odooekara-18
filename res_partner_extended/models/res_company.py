from odoo import api, fields, models, _, Command, tools
from odoo.addons.base.models.decimal_precision import DecimalPrecision
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning
import pdb
from datetime import date, timedelta
import datetime

class ResCompanyInherited(models.Model):
    _inherit = 'res.company'

    company_code = fields.Char('Code')
    tcs_limit = fields.Boolean('Enable TCS Limit',default=False)
    tcs_limit_amount = fields.Float(
        'Maximum TCS Amount', help="By adding maximum limit amount will let users know about the TCS limit")
    tds_limit = fields.Boolean('Enable TDS Limit',default=False)
    tds_limit_amount = fields.Float(
        'Maximum TDS Amount', help="By adding maximum limit amount will let users know about the TDS limit")
    tds_tax_id = fields.Many2one('account.tax', string="TDS Tax", domain=[('type_tax_use', 'in', ['purchase','none'])])

    po_value_1 = fields.Float(string="PO Value Level 1")
    quotes_required_1 = fields.Integer(string="Number of Quotes Level 1")

    po_value_2 = fields.Float(string="PO Value Level 2")
    quotes_required_2 = fields.Integer(string="Number of Quotes Level 2")

    po_value_3 = fields.Float(string="PO Value Level 3")
    quotes_required_3 = fields.Integer(string="Number of Quotes Level 3")
