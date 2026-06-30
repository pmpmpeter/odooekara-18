# -*- coding: utf-8 -*-

import base64
import json
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import time
from datetime import datetime, timedelta, date
import calendar
import pdb
import datetime
from datetime import date
from datetime import timedelta, datetime


class JournalItemsTotalView(models.Model):
    _inherit = 'accounting.balance.report'

    journal_items_count = fields.Integer(string='Journal Items(s)', default=0, compute='_compute_journal_items_total')
    journal_item_ids = fields.Many2many('account.move.line', compute='_compute_journal_items_total',
                                        string='Journal Items', copy=False)

    def action_open_journal_items_total(self):
        action = self.env.ref('account.action_account_moves_all_a')
        result = action.sudo().read()[0]
        result.pop('id', None)
        result['context'] = {}
        journal_item_ids = sum([item.journal_item_ids.ids for item in self], [])
        if len(journal_item_ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, journal_item_ids)) + "])]"
        elif len(journal_item_ids) == 1:
            res = self.env.ref('account.view_move_line_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = journal_item_ids and journal_item_ids[0] or False
        return result

    def _compute_journal_items_total(self):
        for item in self:
            domain = [('move_id.state', '=', 'posted'), ('account_id', '=', item.account_id.id),
                      ('date', '>=', item.date_from), ('date', '<=', item.date_to)]
            if item.partner_ids:
                domain += [('partner_id', 'in', item.partner_ids.ids)]
            if item.analytic_account_ids:
                domain += [('analytic_account_id', 'in', item.analytic_account_ids.ids)]
            if item.journal_ids:
                domain += [('journal_id', 'in', item.journal_ids.ids)]
            journal_item_ids = self.env['account.move.line'].search(domain)
            item.journal_item_ids = journal_item_ids
            item.journal_items_count = len(journal_item_ids)


class JournalItemsView(models.Model):
    _inherit = 'ledger.monthly.report.lines'

    journal_items_count = fields.Integer(string='Journal Items(s)', default=0, compute='_compute_journal_items')
    journal_item_ids = fields.Many2many('account.move.line', compute='_compute_journal_items', string='Journal Items',
                                        copy=False)

    def action_open_journal_items(self):
        action = self.env.ref('account.action_account_moves_all_a')
        result = action.sudo().read()[0]
        result.pop('id', None)
        result['context'] = {}
        journal_item_ids = sum([item.journal_item_ids.ids for item in self], [])
        if len(journal_item_ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, journal_item_ids)) + "])]"
        elif len(journal_item_ids) == 1:
            res = self.env.ref('account.view_move_line_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = journal_item_ids and journal_item_ids[0] or False
        return result

    def _compute_journal_items(self):
        for item in self:
            domain = [('move_id.state', '=', 'posted'), ('account_id', '=', item.account_id.id),
                      ('date', '>=', item.date_from), ('date', '<=', item.date_to)]
            if item.partner_ids:
                domain += [('partner_id', 'in', item.partner_ids.ids)]
            if item.analytic_account_ids:
                domain += [('analytic_account_id', 'in', item.analytic_account_ids.ids)]
            if item.journal_ids:
                domain += [('journal_id', 'in', item.journal_ids.ids)]
            journal_item_ids = self.env['account.move.line'].search(domain)
            item.journal_item_ids = journal_item_ids
            item.journal_items_count = len(journal_item_ids)
