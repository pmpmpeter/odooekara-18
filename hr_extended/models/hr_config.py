# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HRDepartment(models.Model):
    _inherit = 'hr.department'

    def unlink(self):
        """Check if the record is referenced before deletion."""
        related_fields = self.env['ir.model.fields'].search([
            ('ttype', 'in', ['many2one', 'many2many']),
            ('relation', '=', 'hr.department'),
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
        return super(HRDepartment, self).unlink()


class HRContractType(models.Model):
    _inherit = 'hr.contract.type'

    def unlink(self):
        """Check if the record is referenced before deletion."""
        related_fields = self.env['ir.model.fields'].search([
            ('ttype', 'in', ['many2one', 'many2many']),
            ('relation', '=', 'hr.contract.type'),
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
        return super(HRContractType, self).unlink()


class PositionNames(models.Model):
    _name = 'hr.position.names'
    _description = 'Positions/Designation'
    _order = 'sequence'

    name = fields.Char(required=True, translate=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, domain=lambda self: [('id', 'in', self.env.companies.ids)])
    code = fields.Char(compute='_compute_code', store=True, readonly=False)
    sequence = fields.Integer()
    active = fields.Boolean('Active', default=True, copy=False)

    @api.depends('name')
    def _compute_code(self):
        for position_names in self:
            if position_names.code:
                continue
            position_names.code = position_names.name

    def unlink(self):
        """Check if the record is referenced before deletion."""
        related_fields = self.env['ir.model.fields'].search([
            ('ttype', 'in', ['many2one', 'many2many']),
            ('relation', '=', 'hr.position.names'),
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
        return super(PositionNames, self).unlink()


class ContractType(models.Model):
    _name = 'hr.job.levels'
    _description = 'Job Levels'
    _order = 'sequence'

    name = fields.Char(required=True, translate=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, domain=lambda self: [('id', 'in', self.env.companies.ids)])
    code = fields.Char(compute='_compute_code', store=True, readonly=False)
    sequence = fields.Integer()
    active = fields.Boolean('Active', default=True, copy=False)
    #not using this
    country_id = fields.Many2one('res.country')

    @api.depends('name')
    def _compute_code(self):
        for job_levels in self:
            if job_levels.code:
                continue
            job_levels.code = job_levels.name

    def unlink(self):
        """Check if the record is referenced before deletion."""
        related_fields = self.env['ir.model.fields'].search([
            ('ttype', 'in', ['many2one', 'many2many']),
            ('relation', '=', 'hr.job.levels'),
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
        return super(ContractType, self).unlink()


class BusinessUnits(models.Model):
    _name = 'business.units'
    _description = 'Business Units'
    _order = 'sequence'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(compute='_compute_code', store=True, readonly=False)
    company_id = fields.Many2one('res.company', string='Tax Entity', default=lambda self: self.env.company, domain=lambda self: [('id', 'in', self.env.companies.ids)])
    sequence = fields.Integer()
    active = fields.Boolean('Active', default=True, copy=False)
    # not using this but may cause error if remove directly
    tax_entity = fields.Many2one('res.company', string='Tax Entity', default=lambda self: self.env.company, domain=lambda self: [('id', 'in', self.env.companies.ids)])

    @api.depends('name')
    def _compute_code(self):
        for business_units in self:
            if business_units.code:
                continue
            business_units.code = business_units.name

    def unlink(self):
        """Check if the record is referenced before deletion."""
        related_fields = self.env['ir.model.fields'].search([
            ('ttype', 'in', ['many2one', 'many2many']),
            ('relation', '=', 'business.units'),
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
        return super(BusinessUnits, self).unlink()


class LocationMaster(models.Model):
    _name = 'location.master'
    _description = 'Location'
    _order = 'sequence'

    name = fields.Char(required=True, translate=True)
    company_id = fields.Many2one('res.company',string='Company', default=lambda self: self.env.company, domain=lambda self: [('id', 'in', self.env.companies.ids)])
    code = fields.Char(compute='_compute_code', store=True, readonly=False)
    sequence = fields.Integer()
    active = fields.Boolean('Active', default=True, copy=False)

    @api.depends('name')
    def _compute_code(self):
        for ekara_location in self:
            if ekara_location.code:
                continue
            ekara_location.code = ekara_location.name

    def unlink(self):
        """Check if the record is referenced before deletion."""
        related_fields = self.env['ir.model.fields'].search([
            ('ttype', 'in', ['many2one', 'many2many']),
            ('relation', '=', 'location.master'),
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
        return super(LocationMaster, self).unlink()


class AssetsCategory(models.Model):
    _name = 'assets.category'
    _description = 'Assets Category'

    name = fields.Char(string='Name')
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, domain=lambda self: [('id', 'in', self.env.companies.ids)])

    def unlink(self):
        """Check if the record is referenced before deletion."""
        related_fields = self.env['ir.model.fields'].search([
            ('ttype', 'in', ['many2one', 'many2many']),
            ('relation', '=', 'assets.category'),
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
        return super(AssetsCategory, self).unlink()

class BudgetingUnits(models.Model):
    _name = 'budgeting.units'
    _description = 'Budgeting Units'

    name = fields.Char(string='Name')
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, domain=lambda self: [('id', 'in', self.env.companies.ids)])

    def unlink(self):
        """Check if the record is referenced before deletion."""
        related_fields = self.env['ir.model.fields'].search([
            ('ttype', 'in', ['many2one', 'many2many']),
            ('relation', '=', 'budgeting.units'),
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
        return super(BudgetingUnits, self).unlink()

#sub location / sub business unit
class SubLocation(models.Model):
    _name = 'sub.location'
    _description = 'SubLocation'

    name = fields.Char(string='Name')
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, domain=lambda self: [('id', 'in', self.env.companies.ids)])

    def unlink(self):
        """Check if the record is referenced before deletion."""
        related_fields = self.env['ir.model.fields'].search([
            ('ttype', 'in', ['many2one', 'many2many']),
            ('relation', '=', 'sub.location'),
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
        return super(SubLocation, self).unlink()

