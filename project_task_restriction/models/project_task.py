# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from odoo import api, Command, fields, models, _, _lt
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProjectTask(models.Model):
    _inherit = 'project.task'

    is_credit_expense = fields.Boolean(string='Is Credit Expense',default=False)
    x_has_request_approval = fields.Boolean(string="Has Request Approval",default=False)
    x_review_result = fields.Char(string="Review Result",store=True)

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            self.env['multi.approval.type'].compute_need_approval(rec)
        return res


class MultiApprovalType(models.Model):
    _inherit = "multi.approval.type"
    _order = "priority"

    @api.model
    def compute_need_approval(self, rec):
        dmain = self.domain_get(rec._name)
        if not dmain:
            return False
        if rec._name == "project.task":
            rec_id = rec.id
            if not isinstance(rec.id, fields.Integer):
                rec_id = rec._origin.id
            dmain = [("id", "=", rec_id), ('is_credit_expense', '=', True)] + dmain
        else:
            dmain = [("id", "=", rec.id)] + dmain
        try:
            res = rec.sudo().search_count(dmain)
            if res:
                return True
        except ValueError:
            _logger.error(_("Domain of an Approval type is not set properly!"))
        return False