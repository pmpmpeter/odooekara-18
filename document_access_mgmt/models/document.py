# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models,_

class DocumentItem(models.Model):
    _name = 'document.item'
    _description = "Documents Items"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", required=True)
    description = fields.Html(string='Description')
    doc_available_hours = fields.Integer(string='Document Available Hours',default=0)
