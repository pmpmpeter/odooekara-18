# -*- coding: utf-8 -*-

from odoo import models, fields, api
from num2words import num2words
import io
import xlsxwriter
from odoo.http import request
import base64
from datetime import datetime
from odoo.exceptions import AccessError, UserError, ValidationError
import pdb

class AccountPayment(models.Model):
    """
    This class inherits from the 'account.payment' model to add specific
    features and behavior related to printing checks and handling payment
    information. It overrides the 'print_checks' method to provide a custom
    wizard view for selecting and formatting cheque printing options.
    """
    _inherit = 'account.payment'

    cheque_format_id = fields.Many2one('cheque.format', string='Cheque Format',
                                       help='Cheque Print Formats', copy=False)
    sr_no = fields.Char(string="Sr.No", copy=False)
    assigned_by = fields.Many2one('res.users', string="Assigned By", copy=False)
    managed_by = fields.Many2one('res.users', string="Managed By", copy=False)
    comments = fields.Text(string="Comments", copy=False)
    cheque_number = fields.Char(string="Cheque / RTGS Slip No", copy=False)
    towards = fields.Text(string="Towards", copy=False)
    authorised_by = fields.Many2one('res.users', string="Authorised By", copy=False)
    authorised_date = fields.Date(string="Authorised Date", copy=False)
    is_cheque_cleared = fields.Boolean(string="Cheque Cleared", copy=False)
    cheque_cleared_date = fields.Date(string="Date of Cheque Cleared", copy=False)
    trans_id = fields.Char(string="Transaction ID", copy=False)
    sender_account_type = fields.Char(string="Sender Account Type", copy=False)
    beneficiary_account_type = fields.Char(string="Beneficiary Account Type", copy=False)
    sender_receiver_info = fields.Char(string="Sender Receiver Information", copy=False)
    sms_email = fields.Selection([('sms', 'SMS'), ('email', 'Email')], string="SMS / Email", copy=False)
    rtgs_addition = fields.Boolean(string='NEFT/RTGS', compute='compute_rtgs')

    @api.depends('partner_bank_id','journal_id')
    @api.onchange('partner_bank_id','journal_id')
    def compute_rtgs(self):
        for rec in self:
            partner_bank = rec.partner_bank_id.bank_id if rec.partner_bank_id else False
            journal_bank = rec.journal_id.bank_account_id.bank_id if rec.journal_id and rec.journal_id.bank_account_id else False

            if partner_bank and journal_bank:
                rec.rtgs_addition = (partner_bank.name != journal_bank.name)
            else:
                rec.rtgs_addition = False

    def create(self,vals):
        result = super(AccountPayment, self).create(vals)
        if result.partner_type == 'supplier':
            result.comments = "Vendor Payment"
        return result

    @api.onchange('cheque_format_id', 'payment_method_line_id')
    def _onchange_cheque_format_id(self):
        for line in self:
            if line.cheque_format_id or line.payment_method_line_id.payment_method_id.name == 'Checks':
                domain1 = [('user_id', '=', self.env.user.id)]
                employee = self.env['hr.employee'].sudo().search(domain1, limit=1)
                line.assigned_by = self.env.user
                # pdb.set_trace()
                line.managed_by = employee.parent_id.user_id.id or False

    @api.depends('partner_id', 'journal_id', 'destination_journal_id')
    def _compute_is_internal_transfer(self):
        for payment in self:
            if 'is_internal_transfer' in self.env.context:
                if self.env.context['is_internal_transfer']:
                    payment.is_internal_transfer = True
            else:
                payment.is_internal_transfer = payment.partner_id \
                                               and payment.partner_id == payment.journal_id.company_id.partner_id \
                                               and payment.destination_journal_id

    def print_checks(self):
        """
        Overriding print_checks button to generate a wizard view to print
        cheque by selecting a cheque print format.
        """
        if self.payment_method_line_id.payment_method_id.name == 'Checks':
            cheque_date = self.date
        elif self.payment_method_line_id.payment_method_id.name == 'PDC':
            cheque_date = self.effective_date
        return {
            'name': "Cheque Format",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'cheque.types',
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_cheque_amount_in_words': self.check_amount_in_words,
                'default_cheque_date': cheque_date,
                'default_cheque_amount': self.amount,
                'default_check_number': self.check_number,
                'default_payment_id': self.id
            }
        }

    def action_print_cheque_payment(self):
        if self.cheque_format_id:
            data = {
                'cheque_width': self.cheque_format_id.cheque_width,
                'cheque_height': self.cheque_format_id.cheque_height,
                'font_size': self.cheque_format_id.font_size,
                'is_account_payee': self.cheque_format_id.is_account_payee,
                'a_c_payee_top_margin': self.cheque_format_id.a_c_payee_top_margin,
                'a_c_payee_left_margin': self.cheque_format_id.a_c_payee_left_margin,
                'a_c_payee_width': self.cheque_format_id.a_c_payee_width,
                'a_c_payee_height': self.cheque_format_id.a_c_payee_height,
                'date_top_margin': self.cheque_format_id.date_top_margin,
                'date_left_margin': self.cheque_format_id.date_left_margin,
                'date_letter_spacing': self.cheque_format_id.date_letter_spacing,
                'beneficiary_top_margin': self.cheque_format_id.beneficiary_top_margin,
                'beneficiary_left_margin': self.cheque_format_id.beneficiary_left_margin,
                'amount_word_tm': self.cheque_format_id.amount_word_tm,
                'amount_word_lm': self.cheque_format_id.amount_word_lm,
                'amount_word_ls': self.cheque_format_id.amount_word_ls,
                'amount_digit_tm': self.cheque_format_id.amount_digit_tm,
                'amount_digit_lm': self.cheque_format_id.amount_digit_lm,
                'amount_digit_ls': self.cheque_format_id.amount_digit_ls,
                'partner': self.partner_id.name,
                # 'amount_in_words': self.cheque_amount_in_words,
                'amount_in_digit': self.amount,
                'cheque_date': self.date,
                'print_currency': self.cheque_format_id.print_currency,
                'currency_symbol': self.env.company.currency_id.symbol,
                'amount_digit_size': self.cheque_format_id.amount_digit_size,
                'print_cheque_number': self.cheque_format_id.print_cheque_number,
                'check_number': self.check_number,
                'cheque_no_tm': self.cheque_format_id.cheque_no_tm,
                'cheque_no_lm': self.cheque_format_id.cheque_no_lm
            }
            return self.env.ref('account.action_report_payment_receipt').report_action(self, data=data)


class AccountBatchPayment(models.Model):
    """
    This class inherits from the 'account.payment' model to add specific
    features and behavior related to printing checks and handling payment
    information. It overrides the 'print_checks' method to provide a custom
    wizard view for selecting and formatting cheque printing options.
    """
    _inherit = 'account.batch.payment'

    cheque_format_id = fields.Many2one('cheque.format', string='Cheque Format',
                                       help='Cheque Print Formats', copy=False)
    cheque_number = fields.Char(string="Cheque/RTGS Slip No", copy=False)
    towards = fields.Text(string="Towards", copy=False)
    authorised_by = fields.Many2one('res.users', string="Authorised By", copy=False)
    authorised_date = fields.Date(string="Authorised Date", copy=False)
    amount_total_words = fields.Char(
        string="Amount total in words",
        compute="_compute_amount_total_words",
    )

    def action_print_batch_payment_pdf(self):
        return self.env.ref('odoo_print_cheque.print_cheque_payment_batch').report_action(self)

    @api.depends('amount', 'currency_id')
    def _compute_amount_total_words(self):
        for rec in self:
            rec.amount_total_words = rec.currency_id.amount_to_text(abs(rec.amount)).replace(',', '')

    def action_open_mail_wizard(self):
        """ Opens a wizard to compose an email, with relevant mail template loaded by default """
        self.ensure_one()
        # self.order_line._validate_analytic_distribution()
        lang = self.env.context.get('lang')
        mail_template = self.env.ref('odoo_print_cheque.email_template_batch_payment')
        if mail_template and mail_template.lang:
            lang = mail_template._render_lang(self.ids)[self.id]

        # Generate attachments (if not already generated)
        self.action_export_payment_details_xlsx()
        # self.action_generate_pdf_attachment()

        # Search for attachments
        attachments = (self.env['ir.attachment'].search([
            ('res_model', '=', 'account.batch.payment'),
            ('res_id', '=', self.id),
            ('name', 'ilike', 'Batch_Payment_Details')
        ], limit=1))

        #     + self.env['ir.attachment'].search([
        #     ('res_model', '=', 'account.batch.payment'),
        #     ('res_id', '=', self.id),
        #     ('name', 'ilike', 'Batch_Cheque_Report')
        # ], limit=1)

        # Prepare attachment IDs
        attachment_ids = [(4, att.id) for att in attachments]

        ctx = {
            'default_model': 'account.batch.payment',
            'default_res_ids': self.ids,
            'default_template_id': mail_template.id if mail_template else None,
            'default_composition_mode': 'comment',
            'default_attachment_ids': attachment_ids,
            'mark_so_as_sent': True,
            'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
            'force_email': True,
            'model_description': self.with_context(lang=lang).name,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    def action_generate_pdf_attachment(self):
        print("confirmed")
        """ Generate and Attach PDF Report to the Record """
        self.ensure_one()

        pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(
            'odoo_print_cheque.print_cheque_payment_batch',
            res_ids=self.ids
        )

        print(self.ids)

        attachment = self.env['ir.attachment'].create({
            'name': f'Batch_Cheque_Report_{self.name}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': 'account.batch.payment',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })

        return attachment

    def action_export_payment_details_xlsx(self):
        # Create Excel Report in Memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet = workbook.add_worksheet('Payment Details')

        # Formats
        bold = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC'})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})

        # Define Headers
        headers = ['Sr.No.', 'Cheque / RTGS Slip No','SENDER ACCOUNT NO', 'AMOUNT',
                    'BENEFICIARY ACCOUNT NO', 'BENEFICIARY ACCOUNT NAME','BENEFICIARY IFSC',
                   'BENEFICIARY LEI (If applicable)','Remarks']

        for col, header in enumerate(headers):
            sheet.write(0, col, header, bold)
        amount_format = workbook.add_format({'num_format': '#,##0.00'})

        # Populate Data
        row = 1
        for index, line in enumerate(self.payment_ids, start=1):
            sheet.write(row, 0, index or '')
            sheet.write(row, 1, self.cheque_number or '')
            sheet.write(row, 2, line.journal_id.bank_account_id.acc_number or '', date_format)
            sheet.write(row, 3, line.amount or 0.0, amount_format)
            sheet.write(row, 4, line.partner_bank_id.acc_number or '')
            sheet.write(row, 5, line.partner_bank_id.partner_id.name or '')
            sheet.write(row, 6, line.partner_bank_id.bank_id.bic or '')
            sheet.write(row, 7, line.partner_bank_id.bank_id.beneficiary_lei or '')
            sheet.write(row, 8, line.comments or '')
            row += 1

        sheet.set_column(0, 0, 5)
        sheet.set_column(1, 1, 15)
        sheet.set_column(2, 2, 10)
        sheet.set_column(3, 3, 20)
        sheet.set_column(4, 4, 20)
        sheet.set_column(5, 5, 25)
        sheet.set_column(6, 6, 15)
        sheet.set_column(7, 7, 30)
        sheet.set_column(8, 8, 25)
        sheet.set_column(9, 9, 20)
        sheet.set_column(10, 10, 20)
        sheet.set_column(11, 11, 25)
        sheet.set_column(12, 12, 30)
        sheet.set_column(13, 13, 40)

        workbook.close()
        output.seek(0)

        # Encode File to Base64
        file_data = base64.b64encode(output.read())
        output.close()

        # Create Attachment
        attachment = self.env['ir.attachment'].create({
            'name': f'{self.cheque_number}.xlsx',
            'type': 'binary',
            'datas': file_data,
            'store_fname': f'{self.cheque_number}.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': 'account.batch.payment',
            'res_id': self.id,
        })

        # Return the attachment download URL
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
