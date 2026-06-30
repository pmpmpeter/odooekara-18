# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, _


class MailActivitySchedule(models.TransientModel):
    _inherit = 'mail.activity.schedule'

    def action_create_task(self):
        print(self.res_ids, "================")
        project_task_obj = self.env['project.task']
        project_obj = self.env['project.project']
        project_task_type_obj = self.env['project.task.type']
        context = self.env.context

        # Fetch the employee based on active_id
        emp_ids = self.env['hr.employee'].search([('id', '=', context.get('active_id'))])
        print(emp_ids, "--------------------------------")

        # Fetch tasks from the selected activity plan template
        activity_templates = self.env['mail.activity.plan.template'].search([
            ('plan_id', '=', self.plan_id.id)
        ])

        # Create the project for the employee
        for emp_id in emp_ids:
            project_id = project_obj.create({
                'name': f"{emp_id.name} {self.plan_id.name} for {emp_id.department_id.name}",
                'display_name': f"{emp_id.name} {self.plan_id.name} for {emp_id.department_id.name}",
                'label_tasks': f"{self.plan_id.name} Tasks",
                'user_id': emp_id.parent_id.user_id.id,
            })

            # Create the required stages for the project
            stage_initial = project_task_type_obj.create({
                'name': 'Initial',
                'sequence': 1,
                'project_ids': [(4, project_id.id)],
            })
            stage_in_progress = project_task_type_obj.create({
                'name': 'In Progress',
                'sequence': 2,
                'project_ids': [(4, project_id.id)],
            })
            stage_done = project_task_type_obj.create({
                'name': 'Done',
                'sequence': 3,
                'project_ids': [(4, project_id.id)],
            })

            # Create individual tasks for each activity template
            for template in activity_templates:
                    project_task_obj.create({
                        'name': template.summary,
                        'project_id': project_id.id,
                        'user_ids': emp_id.user_id.ids,
                        'display_in_project': True,
                        'stage_id': stage_initial.id,
                    })

        return True
