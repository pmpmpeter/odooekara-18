from odoo import models, fields
from odoo.tools.misc import formatLang
from collections import defaultdict
from odoo.exceptions import UserError, ValidationError
import base64
from io import BytesIO

class GeneratePdfReport(models.TransientModel):
    _name = 'generate.pdf.report'
    _description = 'Generate PDF Report Wizard'

    vendor_id = fields.Many2one('res.partner', string='Vendor')
    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        readonly=True
    )
    partner_ids = fields.Many2many('res.partner', string="Email To")
    report_file = fields.Binary(string="Report File", readonly=True)
    file_name = fields.Char(string="File Name", readonly=True)

    def action_send_balance_confirmation_report_mail(self):
        template = self.env.ref('ekara_pdf_report.balance_confirmtaion_share_email_template')
        for record in self:
            if not record.partner_ids:
                raise ValidationError("Please add at least one partner to send the email.")

            missing = [p.name for p in record.partner_ids if not p.email]
            if missing:
                raise ValidationError(f"Missing email for: {', '.join(missing)}")

            if not record.report_file:
                raise ValidationError("Please upload the report file before sending the email.")

            attachment = self.env['ir.attachment'].create({
                'name': record.file_name or 'report.pdf',
                'type': 'binary',
                'datas': record.report_file,
                'res_model': record._name,
                'res_id': record.id,
                'mimetype': 'application/pdf',
            })

            template.send_mail(record.id, force_send=True, email_values={
                'attachment_ids': [attachment.id],
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Email sent to selected recipients.',
                'type': 'success',
                'sticky': True,
            }
        }

    def get_paymenet_id(self, move):
        self._cr.execute('''
                           SELECT
                               payment.id as payment_ids,
                                ARRAY_AGG(DISTINCT invoice.id) AS invoice_ids
                           FROM account_payment payment
                           JOIN account_move move ON move.id = payment.move_id
                           JOIN account_move_line line ON line.move_id = move.id
                           JOIN account_partial_reconcile part ON
                               part.debit_move_id = line.id
                               OR
                               part.credit_move_id = line.id
                           JOIN account_move_line counterpart_line ON
                               part.debit_move_id = counterpart_line.id
                               OR
                               part.credit_move_id = counterpart_line.id
                           JOIN account_move invoice ON invoice.id = counterpart_line.move_id
                           JOIN account_account account ON account.id = line.account_id
                           WHERE account.account_type IN ('asset_receivable', 'liability_payable')
                               AND invoice.id IN %(payment_ids)s
                               AND line.id != counterpart_line.id
                               AND invoice.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')
                           GROUP BY payment.id, invoice.move_type
                       ''', {
            'payment_ids': tuple(move.ids)
        })
        query_res = self._cr.dictfetchall()
        return query_res

    def get_invoice_data(self):
        account_moves = self.env['account.move'].search([
            ('move_type', '=', 'in_invoice'),
            ('partner_id', '=', self.vendor_id.id),
            ('invoice_date', '>=', self.from_date),
            ('invoice_date', '<=', self.to_date),
            ('state', '=', 'posted')
        ], order='invoice_date')

        # Fetch payments
        payments = self.env['account.payment'].search([
            ('partner_id', '=', self.vendor_id.id),
            ('date', '>=', self.from_date),
            ('date', '<=', self.to_date),
            ('state', '=', 'posted')
        ], order='date')
        # Fetch payments
        self.ensure_one()
        partner_id = self.vendor_id.id
        from_date = self.from_date

        query = """
                SELECT 
                    COALESCE(SUM(aml.debit), 0) - COALESCE(SUM(aml.credit), 0) AS opening_balance
                FROM 
                    account_move_line aml
                JOIN 
                    account_account acc ON aml.account_id = acc.id
                WHERE 
                    aml.partner_id = %s
                    AND aml.date < %s
                    AND aml.parent_state = 'posted'
                    AND acc.account_type = 'liability_payable'
            """

        self.env.cr.execute(query, (partner_id, from_date))
        result = self.env.cr.fetchone()

        opening_balance = abs(result[0] if result else 0.0)

        # Combine into one list
        combined = [
                       {
                           'date': inv.invoice_date,
                           'type': 'invoice',
                           'amount': inv.amount_total,
                           'record': inv,
                       }
                       for inv in account_moves
                   ] + [
                       {
                           'date': pay.date,
                           'type': 'payment',
                           'amount': pay.amount,
                           'record': pay,
                       }
                       for pay in payments
                   ]+[
                       {
                           'date': self.from_date,
                           'type': 'opening_balance',
                           'amount':opening_balance,
                           'record': '',
                       }

                   ]

        # Sort by date
        combined.sort(key=lambda x: x['date'])

        # Group by month
        grouped = defaultdict(list)
        for entry in combined:
            month_key = entry['date'].strftime("%Y-%m")  # example: "2025-09"
            grouped[month_key].append(entry)


        result = []
        pay_result = []
        payment_ids = []
        total_credit = 0.0
        total_debit = 0.0

        # payment_ids = self.env['account.payment'].search([('reconciled_bill_ids','in',account_moves.ids)],order='id')
        for month, records in grouped.items():
            print(f"\nMonth: {month}")
            for rec in records:
                print(f"  {rec['date']} | {rec['type']} | {rec['record']}")
                if rec['type'] == 'payment':
                    pay = rec['record']
                    debit_date = pay.date.strftime('%d-%b-%y') if pay.date else ''
                    debit_label = pay.journal_id.display_name
                    debit_amount = pay.amount
                    total_debit += pay.amount
                    result.append({
                        'debit_date': debit_date,
                        'debit_label': debit_label,
                        'debit_amount': debit_amount,
                        'credit_date':'',
                        'credit_label': '',
                        'credit_amount': 0,
                    })
                elif rec['type'] == 'invoice':
                    invoice = rec['record']
                    for line in invoice.invoice_line_ids:
                        result.append({
                            'debit_date': '',
                            'debit_label': '',
                            'debit_amount': 0,
                            'credit_date': invoice.invoice_date.strftime('%d-%b-%y') if invoice.invoice_date else '',
                            'credit_label': line.account_id.display_name,
                            'credit_amount': invoice.amount_total,
                        })
                    total_credit += invoice.amount_total
                elif rec['type'] == 'opening_balance':
                    result.append({
                        'debit_date': '',
                        'debit_label': '',
                        'debit_amount': 0,
                        'credit_date': self.from_date.strftime('%d-%b-%y') if self.from_date else '',
                        'credit_label':'Opening Balance',
                        'credit_amount': opening_balance,
                    })


                    total_credit += opening_balance

        # for move in account_moves:
        #     payment = self.get_paymenet_id(move)
        #     if payment and payment[0]['payment_ids'] not in payment_ids:
        #         pay = self.env['account.payment'].browse(payment[0]['payment_ids'])
        #         payment_ids.append(pay.id)
        #         debit_date = pay.date.strftime('%d-%b-%y') if pay.date else ''
        #         debit_label = pay.journal_id.display_name
        #         debit_amount = pay.amount
        #         total_debit += pay.amount
        #         for line in move.invoice_line_ids:
        #             result.append({
        #                 'debit_date': debit_date,
        #                 'debit_label': debit_label,
        #                 'debit_amount': debit_amount,
        #                 'credit_date': move.invoice_date.strftime('%d-%b-%y') if move.invoice_date else '',
        #                 'credit_label': line.account_id.display_name,
        #                 'credit_amount': move.amount_total,
        #             })
        #     else:
        #         for line in move.invoice_line_ids:
        #             result.append({
        #                 'debit_date': '',
        #                 'debit_label': '',
        #                 'debit_amount': 0,
        #                 'credit_date': move.invoice_date.strftime('%d-%b-%y') if move.invoice_date else '',
        #                 'credit_label': line.account_id.display_name,
        #                 'credit_amount': move.amount_total,
        #             })
        #
        #     total_credit += move.amount_total
        return {
            'rows': result,
            'total_credit': total_credit,
            'total_debit': float(total_debit),
            'closing_balance_debit':total_credit-total_debit if total_credit > total_debit else 0,
            'closing_balance_credit':total_debit-total_credit if total_debit > total_credit else 0 ,
        }

    def action_generate_pdf(self):
        self.ensure_one()
        pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(
            'ekara_pdf_report.action_pdf_report_creation',
            res_ids=self.ids
        )
        print(self.ids)
        pdf_base64 = base64.b64encode(pdf_content)
        self.report_file = pdf_base64
        attachment = self.env['ir.attachment'].create({
            'name': f'Balance Confirmation',
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': 'generate.pdf.report',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

