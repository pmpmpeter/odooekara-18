'''
Created on Jan 9, 2019

@author: Zuhair Hammadi
'''
from odoo import models, fields


class HolidaysType(models.Model):
    _inherit = "hr.leave.type"

    code = fields.Char(string='Code',copy=False)
    type = fields.Selection([
        ('corporate', 'Corporate (Per Year)'),
        ('unit', 'Unit/Centre (Per Year)')],string="Type")
    attachment_required = fields.Boolean('Attachment Required')
