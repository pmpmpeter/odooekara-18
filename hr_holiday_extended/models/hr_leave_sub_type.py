from odoo import models, api, _, fields
from odoo.exceptions import ValidationError


class HrLeaveSubType(models.Model):
    _name = "hr.leave.sub.type"
    _description = "HR Leave SubCategories"

    name = fields.Char(required=True)
    leave_type_id = fields.Many2many('hr.leave.type', copy=False, required=True)
    days = fields.Integer(string="Restricted Before (Days)")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company,
                                 domain=lambda self: [('id', 'in', self.env.companies.ids)])
    active = fields.Boolean('Active', default=True, copy=False)

    def unlink(self):
        """Check if the record is referenced before deletion."""
        related_fields = self.env['ir.model.fields'].search([
            ('ttype', 'in', ['many2one', 'many2many']),
            ('relation', '=', 'hr.leave.sub.type'),
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
        return super(HrLeaveSubType, self).unlink()


