# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Jumana Haseen @cybrosys(odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import models, fields
from odoo.exceptions import ValidationError, UserError


class OrientationChecklist(models.Model):
    """This class creates a model 'orientation.checklist' and added fields"""
    _name = 'orientation.checklist'
    _description = "Checklist"
    _rec_name = 'checklist_name'
    _inherit = 'mail.thread'

    checklist_name = fields.Char(string='Name', required=True,
                                 help="Give the checklist name.")
    checklist_department_id = fields.Many2one('hr.department',
                                              domain="[('company_id', '=', company_id)]",
                                              string='Department',
                                              required=True,
                                              help="Give the corresponding"
                                                   "department.")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, readonly=True)
    active = fields.Boolean(string='Active', default=True,
                            help="Set active to false to hide the Orientation "
                                 "Checklist without removing it.")
    checklist_line_ids = fields.Many2many('checklist.line',
                                          'checklist_line_rel',
                                          help="Specify all the checklists.")

    def unlink(self):
        """Check if the record is referenced before deletion."""
        related_fields = self.env['ir.model.fields'].search([
            ('ttype', 'in', ['many2one', 'many2many']),
            ('relation', '=', 'orientation.checklist'),
        ])
        for record in self:
            for field in related_fields:
                model = self.env[field.model]
                if field.ttype == 'many2one':
                    references = model.search([(field.name, '=', record.id)])
                elif field.ttype == 'many2many':
                    references = model.search([(field.name, 'in', [record.id])])
                else:
                    continue

                if references:
                    model_name = self.env['ir.model']._get(field.model).name
                    referenced_ids = references.mapped('id')
                    raise ValidationError(
                        f"You cannot delete the record '{record.checklist_name}' as it is referenced in the model '{model_name}'."
                    )
        return super(OrientationChecklist, self).unlink()
