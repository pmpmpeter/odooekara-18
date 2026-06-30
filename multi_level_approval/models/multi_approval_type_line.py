##############################################################################
#
#    Copyright Domiup (<http://domiup.com>).
#
##############################################################################

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class MultiApprovalTypeLine(models.Model):
    _name = "multi.approval.type.line"
    _description = "Multi Approval Type Lines"
    _order = "sequence"

    name = fields.Char(string="Title", required=True)
    user_id = fields.Many2many(string="User", comodel_name="res.users", required=True)
    sequence = fields.Integer()
    require_opt = fields.Selection(
        [
            ("Required", "All Must Approve"),
            ("Optional", "Any One Can Approve"),
        ],
        string="Type of Approval",
        default="Required",
        required=True,
    )
    state = fields.Selection([('Draft','Draft'),('Approved','Approved'),('Waiting for Approval','Waiting for Approval'),('Refused','Refused'),('Cancel','Cancel')])
    type_id = fields.Many2one(string="Type", comodel_name="multi.approval.type")

    def get_user(self):
        self.ensure_one()
        print(self.user_id.ids)
        return self.user_id.ids
