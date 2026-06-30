# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class AccountAsset(models.Model):
    _inherit = 'account.asset'

    asset_tag_no = fields.Char(string="Assets Tag Number", copy=False)
    end_date = fields.Date(string="End Date", copy=False)
    life_of_asset = fields.Char(string="Life of Asset", copy=False)
    employee_id = fields.Many2one('hr.employee', string="User", copy=False)
    location = fields.Char(string="Location", copy=False)
    location_id = fields.Many2one("stock.location", string="Location")
    mobile_number = fields.Char(string="Mobile", copy=False)
    asset_value = fields.Float(string='Asset Value',compute='compute_asset_value')
    method = fields.Selection(
        selection=[
            ('linear', 'Straight Line'),
            ('degressive', 'Written Down Value'),
            ('degressive_then_linear', 'Declining then Straight Line')
        ],
        string='Method',
        default='linear',
        help="Choose the method to use to compute the amount of depreciation lines.\n"
             "  * Straight Line: Calculated on basis of: Gross Value / Duration\n"
             "  * Written Down Value: Calculated on basis of: Residual Value * Declining Factor\n"
             "  * Declining then Straight Line: Like Declining but with a minimum depreciation value equal to the straight line value."
    )
    _sql_constraints = [
        ('asset_tag_no_unique', 'unique (asset_tag_no)', 'The Asset Tag Number must be unique.'),
    ]

    can_edit_asset_fields = fields.Boolean(compute="_compute_can_edit_asset_fields", store=False,default=False)

    @api.depends_context('uid')
    def _compute_can_edit_asset_fields(self):
        for record in self:
            record.can_edit_asset_fields = self.env.user.has_group('account.group_account_manager')

    def compute_asset_value(self):
        print('jj')
        for rec in self:
            val = rec.original_value - rec.salvage_value
            if rec.depreciation_move_ids:
                entries = rec.depreciation_move_ids.filtered(lambda line: line.state == 'posted')
                # print(sum(entries.depreciation_value),'kkkkkkkkkkkkkk')
                rec.asset_value = val - sum(entry.depreciation_value for entry in entries)
                # stop
            else:
                rec.asset_value = val
