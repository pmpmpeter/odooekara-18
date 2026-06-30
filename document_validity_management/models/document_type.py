from odoo import models, fields, api

class DocumentType(models.Model):
    _name = 'document.type'
    _description = 'Document Type Master'

    name = fields.Char(string="Document Type", required=True)
    description = fields.Text(string="Description")
    default_validity_period = fields.Integer(string="Default Validity Period (Days)",
                                              help="Default validity duration for this document type.")
    active = fields.Boolean(string="Active",default=True)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            domain = ['|', ('name', operator, name), ('default_validity_period', operator, name)]
            records = self.search(domain + args, limit=limit)
        else:
            records = self.search(args, limit=limit)
        return records.name_get()

    def name_get(self):
        result = []
        for record in self:
            display_name = f"{record.name} - {record.default_validity_period} days"
            result.append((record.id, display_name))
        return result

    project_count = fields.Integer(string="Project Count", compute="_compute_project_count")
    task_count = fields.Integer(string="Task Count", compute="_compute_task_count")

    @api.depends('name')
    def _compute_project_count(self):
        for record in self:
            record.project_count = self.env['project.project'].search_count([('document_type_id', '=', record.id)])

    @api.depends('name')
    def _compute_task_count(self):
        for record in self:
            record.task_count = self.env['project.task'].search_count([('document_type_id', '=', record.id)])

    def action_view_projects(self):
        self.ensure_one()
        action = self.env.ref('project.open_view_project_all').read()[0]
        action['domain'] = [('document_type_id', '=', self.id)]
        return action

    def action_view_tasks(self):
        self.ensure_one()
        action = self.env.ref('project.action_view_task').read()[0]
        action['domain'] = [('document_type_id', '=', self.id)]
        return action
