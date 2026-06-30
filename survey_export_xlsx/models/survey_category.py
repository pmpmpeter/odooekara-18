
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SurveyCategory(models.Model):
    _name = 'survey.category'
    _description = 'Survey Category'
    _order = 'sequence'

    name = fields.Char(required=True, translate=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, domain=lambda self: [('id', 'in', self.env.companies.ids)])
    sequence = fields.Integer()
    active = fields.Boolean('Active', default=True, copy=False)

    def unlink(self):
        """Check if the record is referenced before deletion."""
        related_fields = self.env['ir.model.fields'].search([
            ('ttype', 'in', ['many2one', 'many2many']),
            ('relation', '=', 'survey.category'),
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
        return super(SurveyCategory, self).unlink()
