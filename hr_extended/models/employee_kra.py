from odoo import models, fields, api, _
from odoo.exceptions import *
from odoo.exceptions import ValidationError, UserError


class EmployeeKra(models.Model):
    _name = "employee.kra"
    _description = "Employee KRA"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    kra_date = fields.Date(string="Date", default=fields.Date.context_today)
    employee_id = fields.Many2one('hr.employee', string='Employee', domain=lambda self: self._compute_employee_domain())
    emp_job_id = fields.Many2one('hr.job', string='Job Position')
    kra_master = fields.Many2one('kra.master', string="KRA")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit_to_supervisor', 'Waiting Review'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True, copy=False)
    remarks = fields.Text(string="Remarks")

    kra_details_ids = fields.One2many('employee.kra.details', 'emp_kra_id', string="Employee Details")
    employee_parent_id = fields.Many2one(related='employee_id.parent_id', readonly=True, related_sudo=True)
    company_id = fields.Many2one('res.company', string='Company ID', default=lambda self: self.env.company,
                                 domain=lambda self: [('id', '=', (self.env.company.id))])
    user_id = fields.Many2one('res.users', string='User ID', default=lambda self: self.env.user)
    overall_weightage = fields.Integer(string='Total Weightage', copy=False)
    remaining = fields.Char(copy=False, readonly=True)
    x_review_result = fields.Char(string="Review Result")

    @api.model
    def _compute_employee_domain(self):
        """ Dynamically restrict employee selection based on user group """
        user = self.env.user
        if user.has_group('hr.group_hr_user') or user.has_group('hr.group_hr_manager'):
            return []
        else:
            return [('user_id', '=', user.id)]

    @api.onchange('kra_details_ids')
    def onchange_weightage(self):
        overall = 0.0
        for rec in self.kra_details_ids:
            overall += rec.weightage
        self.overall_weightage = int(overall)
        self.remaining = "Remaining weightage %s" % (100 - int(overall))

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.emp_job_id = self.employee_id.job_id
            self.kra_master = self.emp_job_id.kra_master

    def action_submit_to_supervisor(self):
        for record in self:
            if hasattr(self, 'x_has_request_approval'):
                self.x_has_request_approval = False

            if not record.employee_parent_id:
                raise UserError("Please set the Manager for the Employee.")

            if not record.kra_details_ids:
                raise UserError("You cannot submit to supervisor as no KRA details are available for this employee.")

            manager_user_id = record.employee_parent_id.user_id.id
            if not manager_user_id:
                raise UserError("Manager does not have a corresponding user in the system.")

            total_weightage = sum(detail.weightage for detail in record.kra_details_ids)
            if total_weightage != 100:
                raise ValidationError(
                    f"The total weightage of KRA details must equal 100. Currently, it is {total_weightage}."
                )
            record.state = 'submit_to_supervisor'
        # approval_type_model = self.env['multi.approval.type']
        # approval_type_line_model = self.env['multi.approval.type.line']
        #
        # for record in self:
        #     if not record.employee_parent_id:
        #         raise UserError("Please set the Manager for the Employee.")
        #
        #     if not record.kra_details_ids:
        #         raise UserError("You cannot submit to supervisor as no KRA details are available for this employee.")
        #
        #     total_weightage = sum(detail.weightage for detail in record.kra_details_ids)
        #     if total_weightage != 100:
        #         raise ValidationError(
        #             f"The total weightage of KRA details must equal 100. Currently, it is {total_weightage}."
        #         )
        #
        #     if hasattr(self, 'x_has_request_approval'):
        #         self.x_has_request_approval = False
        #
        #         # Search for the approval type
        #         approval_type = approval_type_model.search([
        #             ('model_id', '=', 'employee.kra'),
        #             ('domain', 'ilike', '"state"')
        #         ], limit=1)
        #
        #         if approval_type and approval_type.state == 'confirm':
        #             approval_lines = approval_type_line_model.search([('type_id', '=', approval_type.id)])
        #             if not approval_lines:
        #                 raise UserError("No approval lines found for the selected approval type.")
        #
        #             approval_line = approval_lines[0]
        #             manager_user_id = record.employee_parent_id.user_id.id
        #
        #             if manager_user_id:
        #                 approval_line.write({
        #                     'user_id': [(6, 0, [manager_user_id])]
        #                 })
        #                 # record.state = 'submit_to_supervisor'
        #                 # action = self.env.ref("multi_level_approval_configuration.request_approval_action", False)
        #                 # if action:
        #                 #     return action.read()[0]
        #             else:
        #                 raise UserError("The Manager does not have a corresponding user in the system.")

    def send_email(self):
        for record in self:
            template = self.env.ref('hr_extended.email_template_kra_submit')
            if template:
                if not record.employee_parent_id.work_email:
                    raise UserError("Please check the Manager work email")

                compose_form = self.env.ref('mail.email_compose_message_wizard_form', raise_if_not_found=True)
                ctx = {
                    'default_model': 'employee.kra',
                    'default_res_ids': self.ids,
                    'default_template_id': template.id,
                    'default_composition_mode': 'comment',
                    'default_email_layout_xmlid': "mail.mail_notification_light",
                }

                return {
                    'name': _('Compose KRA Email'),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'mail.compose.message',
                    'views': [(compose_form.id, 'form')],
                    'view_id': compose_form.id,
                    'target': 'new',
                    'context': ctx,
                }

    def action_cancel(self):
        for record in self:
            record.state = 'cancel'

    def action_approve(self):
        for record in self:
            employee = record.employee_id.sudo()  # Use sudo() once to avoid repeating

            if not employee.contract_id:
                raise ValidationError("There is no Compensation Master in Running state for the Employee")
            if not employee.contract_id.grade:
                raise ValidationError("Please Select the Grade for the Employee in Compensation Master")
            if not employee.contract_id.location_id:
                raise ValidationError("Please Select the Location for the Employee in Compensation Master")
            if not employee.department_id:
                raise ValidationError("Please Select the Department for the Employee")

            self_rating_id = self.env['self.rating'].sudo().create({
                'employee_id': employee.id,
                'designation_id': employee.job_id.id,
                'department_id': employee.department_id.id,
                'grade': employee.contract_id.grade,
                'location_id': employee.contract_id.location_id.id,
                'goal_sets_kras': [(0, 0, {
                    'category': detail.category,
                    'kra': detail.kra_type,
                    'goal_description': detail.goal_description,
                    'weightage': detail.weightage,
                }) for detail in record.kra_details_ids],
                'kra_ids': [(0, 0, {
                    'name': detail.kra_type,
                    'weightage': detail.weightage,
                    'goal_description': detail.goal_description,
                }) for detail in record.kra_details_ids],
                'manager_rating_ids': [(0, 0, {
                    'name': detail.goal_description,
                    'weightage': detail.weightage,
                }) for detail in record.kra_details_ids],
                # 'director_rating_ids': [(0, 0, {
                #     'name': detail.goal_description,
                #     'weightage': detail.weightage,
                # }) for detail in record.kra_details_ids],
                'assessment_kra_ids': [(0, 0, {
                    'name': detail.kra_type,
                    'weightage': detail.weightage,
                }) for detail in record.kra_details_ids],
                'review_line_ids': [(0, 0, {
                    'kra': detail.kra_type,
                    'description': detail.goal_description,
                    'weightage': detail.weightage,
                }) for detail in record.kra_details_ids],
            })
            self_rating_id._compute_contract_self_rating()
            self_rating_id._onchange_employee_id()
            record.state = 'done'

    def action_reset(self):
        for record in self:
            record.state = 'draft'

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Only records in the 'Draft' state can be deleted."))
        return super(EmployeeKra, self).unlink()

    def action_fetch_kra_details(self):
        if not self.kra_master:
            raise UserError("No KRA Master found for this employee.")
        self.kra_details_ids.unlink()

        for kra_detail in self.kra_master.details_ids:
            self.env['employee.kra.details'].create({
                'emp_kra_id': self.id,
                'category': kra_detail.category,
                'business_unit_id': kra_detail.business_unit_id.id,
                'kra_type': kra_detail.kra_type,
                'goal_description': kra_detail.goal_description,
                'weightage': kra_detail.weightage,
                'company_id': kra_detail.kra_id.company_id.id,
            })
        overall = 0.0
        for rec in self.kra_details_ids:
            overall += rec.weightage
        self.overall_weightage = int(overall)
        self.remaining = "Remaining weightage %s" % (100 - int(overall))

        return True


class KraDetails(models.Model):
    _name = "employee.kra.details"
    _description = "Employee KRA Details"

    emp_kra_id = fields.Many2one('employee.kra', string="KRA Questions", ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company')
    category = fields.Char(string="Category", required=True)
    business_unit_id = fields.Many2one('business.units', string="Business Units", domain="[('company_id', '=', company_id)]")
    kra_type = fields.Char(string="KRA")
    goal_description = fields.Char(string="Goal Description")
    weightage = fields.Float(string="Weightage")
    employee_rating = fields.Float(string="Employee Rating")
    employee_remark = fields.Char(string="Employee Remark")
    manager_rating = fields.Float(string="Manager Rating")
    manager_remark = fields.Char(string="Manager Remark")
    bu_head_rating = fields.Float(string="BU Head Rating")
    bu_head_remark = fields.Char(string="BU Head Remark")
    director_hr_rating = fields.Float(string="Director & HR Rating")
    director_hr_remark = fields.Char(string="Director & HR Remark")
    final_score = fields.Float(string="Final Score", compute="_compute_final_score", store=True)

    @api.constrains('weightage')
    def _validate_weightage_values(self):
        for record in self:
            if record.weightage < 0:
                raise ValidationError("Negative values are not allowed for Weightage.")
            print(record.company_id)

    @api.depends('weightage', 'employee_rating', 'manager_rating')
    def _compute_final_score(self):
        for record in self:
            # Ensure ratings do not exceed 100
            employee_rating = min(record.employee_rating, 100)
            manager_rating = min(record.manager_rating, 100)

            # Calculate weighted scores
            employee_weighted_score = (employee_rating / 100) * record.weightage
            manager_weighted_score = (manager_rating / 100) * record.weightage

            # Calculate final score
            record.final_score = employee_weighted_score + manager_weighted_score
