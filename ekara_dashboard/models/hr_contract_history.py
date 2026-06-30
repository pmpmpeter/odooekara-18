# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from collections import defaultdict

class ContractHistory(models.Model):
    _inherit = 'hr.contract.history'

    default_contract_id = fields.Many2one('hr.contract', string='Contract Template', readonly=True,
        help='Default contract used when making an offer to an applicant.')

class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    last_appraisal_id = fields.Many2one(readonly=True)