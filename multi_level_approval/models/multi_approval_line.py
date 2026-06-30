##############################################################################
#
#    Copyright Domiup (<http://domiup.com>).
#
##############################################################################

import logging

from odoo import fields, models
from datetime import datetime

_logger = logging.getLogger(__name__)


class MultiApprovalLine(models.Model):
    _name = "multi.approval.line"
    _description = "Multi Approval Line"
    _order = "sequence"

    name = fields.Char(string="Title", required=True)
    user_id = fields.Many2many(string="User", comodel_name="res.users",relation="multi_approval_line_user_rel", required=True)
    sequence = fields.Integer()
    require_opt = fields.Selection(
        [
            ("Required", "All Must Approve"),
            ("Optional", "Any One Can Approve"),
        ],
        string="Type of Approval",
        default="Required",
    )
    approval_id = fields.Many2one(string="Approval", comodel_name="multi.approval")
    state = fields.Selection(
        [
            ("Draft", "Draft"),
            ("Waiting for Approval", "Waiting for Approval"),
            ("Approved", "Approved"),
            ("Refused", "Refused"),
            ("Cancel", "Cancel"),
        ],
        default="Draft",
    )
    refused_reason = fields.Text()
    deadline = fields.Date()

    approval_datetime = fields.Datetime(
        string="Action Date",
        copy=False,
        help="The date and time when this approval line was approved or rejected."
    )

    approved_users = fields.Many2many("res.users", relation="multi_approval_line_approved_user_rel", string="Approved Users", copy=False)

    # 13.0.1.1
    def set_approved(self):
        self.ensure_one()
        self.write({"state": "Approved", "approval_datetime": datetime.now()})
        # self.state = "Approved"

    def set_refused(self, reason=""):
        self.ensure_one()
        self.write({
            "state": "Refused",
            "refused_reason": reason,
            "approval_datetime": datetime.now(),
        })
        # self.write({"state": "Refused", "refused_reason": reason})
