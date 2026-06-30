from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class PerformanceConfig(models.Model):
    _name = 'performance.config'
    _description = '360 Performance Configuration'

    sequence = fields.Integer(string="Sequence")
    name = fields.Char(string="Name")
    active = fields.Boolean(string="Active", default=True)
    review_types = fields.Selection([('communication', 'Communication'),
                                     ('team_working','Team Working'),
                                     ('problem_solving','Problem-solving and Decision-Making'),
                                     ('continuous','Continuous Improvement'),
                                     ('organisation_time','Organisation and Time Management'),
                                     ('customer_focus','Customer Focus'),
                                     ('interpersonal_skills','Interpersonal Skills'),
                                     ('motivation','Motivation'),
                                     ], string="Review Type")

    def unlink(self):
        """Check if the record is referenced before deletion."""
        related_fields = self.env['ir.model.fields'].search([
            ('ttype', 'in', ['many2one', 'many2many']),
            ('relation', '=', 'performance.config'),
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
        return super(PerformanceConfig, self).unlink()


