from odoo import api, fields, models, _, tools

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    po_value_1 = fields.Float(string="PO Value Level 1",related='company_id.po_value_1',readonly=False)
    quotes_required_1 = fields.Integer(string="Number of Quotes Level 1",related='company_id.quotes_required_1',readonly=False)

    po_value_2 = fields.Float(string="PO Value Level 2",related='company_id.po_value_2',readonly=False)
    quotes_required_2 = fields.Integer(string="Number of Quotes Level 2",related='company_id.quotes_required_2',readonly=False)

    po_value_3 = fields.Float(string="PO Value Level 3",related='company_id.po_value_3',readonly=False)
    quotes_required_3 = fields.Integer(string="Number of Quotes Level 3",related='company_id.quotes_required_3',readonly=False)

    