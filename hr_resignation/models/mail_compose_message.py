from odoo import models,fields,api,_
import ast


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def _action_send_mail(self, auto_commit=False):
        result_mails_su, result_messages = super(MailComposeMessage, self)._action_send_mail(auto_commit=auto_commit)
        template_resignation_submission_letter = self.env.ref('hr_resignation.email_template_resignation_confirm',
                                                   raise_if_not_found=False)
        template_resignation_rejection_letter = self.env.ref('hr_resignation.email_template_resignation_reject',
                                                   raise_if_not_found=False)
        # template_resignation_hr_approve_letter = self.env.ref('hr_resignation.email_template_resignation_approve_hr',
        #                                                      raise_if_not_found=False)

        for wizard in self:
            if wizard.template_id and wizard.template_id.id == template_resignation_submission_letter.id:
                if wizard.model == 'hr.resignation' and wizard.res_ids:
                    try:
                        res_ids_list = ast.literal_eval(wizard.res_ids)
                        for res_id in res_ids_list:
                            resignation = self.env['hr.resignation'].browse(res_id)
                            resignation.state = 'confirm'
                            resignation.resign_confirm_date = fields.Datetime.now()
                    except (SyntaxError, ValueError):
                        print("not working")

            if wizard.template_id and wizard.template_id.id == template_resignation_rejection_letter.id:
                if wizard.model == 'hr.resignation' and wizard.res_ids:
                    try:
                        res_ids_list = ast.literal_eval(wizard.res_ids)
                        for res_id in res_ids_list:
                            resignation = self.env['hr.resignation'].browse(res_id)
                            resignation.state = 'cancel'
                    except (SyntaxError, ValueError):
                        print("not working")

            # if wizard.template_id and wizard.template_id.id == template_resignation_hr_approve_letter.id:
            #     if wizard.model == 'hr.resignation' and wizard.res_ids:
            #         try:
            #             res_ids_list = ast.literal_eval(wizard.res_ids)
            #             for res_id in res_ids_list:
            #                 resignation = self.env['hr.resignation'].browse(res_id)
            #                 resignation.state = 'cancel'
            #         except (SyntaxError, ValueError):
            #             print("not wroking")

        return result_mails_su, result_messages
