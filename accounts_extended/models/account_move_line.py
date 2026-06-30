# -*- coding: utf-8 -*-
from collections import defaultdict
from contextlib import ExitStack, contextmanager
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from hashlib import sha256
from json import dumps
import logging
from markupsafe import Markup
from psycopg2 import OperationalError
import re
from textwrap import shorten
from unittest.mock import patch
import base64
from io import BytesIO
from odoo.tools.misc import xlsxwriter
from odoo.tools import html2plaintext, plaintext2html
from num2words import num2words
from odoo import api, fields, models, _, Command
from odoo.addons.base.models.decimal_precision import DecimalPrecision
from odoo.addons.account.tools import format_structured_reference_iso
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning
import io
import xlsxwriter
from datetime import datetime
from odoo.tools import (
    date_utils,
    email_split,
    float_compare,
    float_is_zero,
    float_repr,
    format_amount,
    format_date,
    formatLang,
    frozendict,
    get_lang,
    groupby,
    index_exists,
    is_html_empty,
)

_logger = logging.getLogger(__name__)
import pdb
month_field_map = {
                1: 'january_cur_budget',
                2: 'february_cur_budget',
                3: 'march_cur_budget',
                4: 'april_cur_budget',
                5: 'may_cur_budget',
                6: 'june_cur_budget',
                7: 'july_cur_budget',
                8: 'august_cur_budget',
                9: 'september_cur_budget',
                10: 'october_cur_budget',
                11: 'november_cur_budget',
                12: 'december_cur_budget',
            }

MAX_HASH_VERSION = 3

PAYMENT_STATE_SELECTION = [
    ('not_paid', 'Not Paid'),
    ('in_payment', 'In Payment'),
    ('paid', 'Paid'),
    ('partial', 'Partially Paid'),
    ('reversed', 'Reversed'),
    ('invoicing_legacy', 'Invoicing App Legacy'),
]

TYPE_REVERSE_MAP = {
    'entry': 'entry',
    'out_invoice': 'out_refund',
    'out_refund': 'entry',
    'in_invoice': 'in_refund',
    'in_refund': 'entry',
    'out_receipt': 'out_refund',
    'in_receipt': 'in_refund',
}

EMPTY = object()

BILL_APPR = ['in_invoice', 'in_receipt', 'in_refund']

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # budget_id  = fields.Many2many('crossovered.budget.lines', string='Budget Code', copy=False, required=0)
    other_charges_payment_line = fields.Boolean(string="Other Charges Payment Line", copy=False,default=False)

    # @api.onchange('account_id')
    # def update_budget_code(self):
    #     for rec in self:
    #             if rec.move_id.crossovered_budget:
    #                 if rec.account_id:
    #                     budget_post = self.env['account.budget.post'].sudo().search([('account_ids.name','in',[rec.account_id.name])])
    #                     budget_id = rec.move_id.crossovered_budget.crossovered_budget_line.filtered(lambda l:l.general_budget_id in budget_post)
    #                     rec.budget_id = [(6, 0, budget_id.ids)]

    

    # def update_actual_aml_cur_figure_server_action(self):
    #     record_ids = self._context.get('active_ids')
    #     if record_ids:
    #         month_list = []
    #         entry_list =[]
    #         for rec in record_ids:
    #             aml = self.env['account.move.line'].browse(rec)
    #             move = aml.move_id
    #             month_field = month_field_map.get(move.date.month)
    #             if month_field not in month_list:
    #                 if move not in entry_list:
    #                     print(aml.budget_id,'pppp')
    #                     rec_id = aml.budget_id
    #                     # setattr(rec_id.crr_budget_line_id, month_field, 0)
    #                     balance = sum(aml.mapped('balance'))
    #                     for line in aml.budget_id.crr_budget_line_id:
    #                         setattr(line, month_field, getattr(line, month_field) + balance)
