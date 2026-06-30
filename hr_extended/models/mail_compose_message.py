from odoo import models,fields,api,_
import ast


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    load_template_readonly = fields.Boolean(string="Load Template Readonly", default=False)

    # @api.onchange('template_id')
    # def _change_readonly_template_id(self):
    #     for record in self:
    #         template_appointment_letter = self.env.ref('hr_extended.mail_appointment_letter_employee',
    #                                                    raise_if_not_found=False)
    #         print(record.model, record.template_id.id, record.load_template_readonly,"testing tam")
    #         if record.model == 'hr.employee' and record.template_id.id == template_appointment_letter.id:
    #             record.load_template_readonly=True

    def _action_send_mail(self, auto_commit=False):
        result_mails_su, result_messages = super(MailComposeMessage, self)._action_send_mail(auto_commit=auto_commit)
        template_appointment_letter = self.env.ref('hr_extended.mail_appointment_letter_employee',
                                                   raise_if_not_found=False)

        for wizard in self:
            print(wizard.template_id, wizard.model, wizard.res_ids, template_appointment_letter.id,"working or not")
            if wizard.template_id and wizard.template_id.id == template_appointment_letter.id:
                if wizard.model == 'hr.employee' and wizard.res_ids:
                    try:
                        res_ids_list = ast.literal_eval(wizard.res_ids)
                        for res_id in res_ids_list:
                            employee = self.env['hr.employee'].browse(res_id)
                            employee.appointment_letter_sent = True
                    except (SyntaxError, ValueError):
                        print("not wroking")

        return result_mails_su, result_messages
