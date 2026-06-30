# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class GrievanceTypeNames(models.Model):
    _name = 'grievance.type.names'
    _description = 'Grievance Type'
    _order = 'sequence'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(compute='_compute_code', store=True, readonly=False)
    sequence = fields.Integer()
    active = fields.Boolean('Active', default=True, copy=False)
    respective_hod_id = fields.Many2one('hr.employee', string="HOD", copy=False)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company,
                                 domain=lambda self: [('id', 'in', self.env.companies.ids)])
    @api.depends('name')
    def _compute_code(self):
        for grievance_types in self:
            if grievance_types.code:
                continue
            grievance_types.code = grievance_types.name

    def unlink(self):
        """Check if the record is referenced before deletion."""
        related_fields = self.env['ir.model.fields'].search([
            ('ttype', 'in', ['many2one', 'many2many']),
            ('relation', '=', 'grievance.type.names'),
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
                        f"You cannot delete the record '{record.name}' as it is referenced in the model '{model_name}'."
                    )
        return super(GrievanceTypeNames, self).unlink()
