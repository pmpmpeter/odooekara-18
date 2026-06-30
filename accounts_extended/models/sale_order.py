from odoo import api, fields, models, _, Command, tools
from odoo.addons.base.models.decimal_precision import DecimalPrecision
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning
import re
import pdb
import datetime
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    def diff_month(self, d1, d2):
        return (d1.year - d2.year) * 12 + d1.month - d2.month

    def _create_invoices(self, **kwargs):
        invoice_vals = super(SaleOrderInherit, self)._create_invoices(**kwargs)
        invoices = self.mapped('invoice_ids')
        print(self)
        print(self.order_line)
        for order in self.filtered_domain([('is_subscription', '=', True)]):
            start_date = order.next_invoice_date
            end_date = order.end_date
            no_of_months = order.diff_month(end_date, start_date)
            for i in range(no_of_months):
                next_month = order.next_invoice_date.month + 1
                # pdb.set_trace()
                # order.write({'next_invoice_date': order.next_invoice_date.replace(month=next_month)})
                # order._create_recurring_invoice()
                invoices[0].write({
                    'invoice_date': order.next_invoice_date.replace(day=1),
                })
                for line in order.order_line:
                    print(line.name,'kkkkkkkkkkk')
                    next_month_date = invoices[0].invoice_date + relativedelta(months=1)
                    end_date = next_month_date - timedelta(days=1)
                    # print(invoice_line.move_id.invoice_date, before_date, 'jjj')

                    month_diff = (end_date.year - invoices[0].invoice_date.year) * 12 + end_date.month - invoices[0].invoice_date.month
                    if month_diff == 0:
                        month_value = 1
                    else:
                        month_value = month_diff
                    invoice_line_0 =  invoices[0].invoice_line_ids.filtered(
                        lambda l: l.product_id == line.product_id and l.quantity == line.product_uom_qty)
                    print(invoices[0].invoice_line_ids,'hhh')
                    invoice_line_0.write({
                        'name': f"{line.name} - {month_value} Month(s)\n{invoices[0].invoice_date.strftime('%d/%m/%Y')} to {end_date.strftime('%d/%m/%Y')}",
                        'deferred_start_date': invoices[0].invoice_date,
                        'deferred_end_date': end_date,
                    })
                # stop
                new_invoice = invoices[0].copy()
                next_invoice_date = order.next_invoice_date + timedelta(days=30 * (i + 1))
                new_invoice.write({
                    'invoice_date': next_invoice_date.replace(day=1),
                })
                for line in order.order_line:
                    invoice_line = new_invoice.invoice_line_ids.filtered(
                        lambda l: l.product_id == line.product_id and l.quantity == line.product_uom_qty)
                    if invoice_line:
                        # start_date = next_invoice_date

                        # start_date = new_invoice.invoice_date
                        next_month_date = invoice_line.move_id.invoice_date + relativedelta(months=1)
                        end_date = next_month_date - timedelta(days=1)
                        month_diff = (end_date.year - new_invoice.invoice_date.year) * 12 + end_date.month - new_invoice.invoice_date.month
                        if month_diff == 0:
                            month_value = 1
                        else:
                            month_value = month_diff
                        invoice_line.write({
                            'sale_line_ids': [(6, 0, line.ids)],
                            'name': f"{line.name} - {month_value} Month(s)\n{new_invoice.invoice_date.strftime('%d/%m/%Y')} to {end_date.strftime('%d/%m/%Y')}",
                            'deferred_start_date': new_invoice.invoice_date,
                            'deferred_end_date': end_date,
                        })

        return invoice_vals

    @api.constrains('state')
    def _check_untaxed_amount(self):
        for order in self:
            if order.state == 'sale' and order.amount_untaxed == 0:
                raise UserError(_("You cannot confirm a sale order with an untaxed amount of zero."))

    def action_confirm(self):
        for rec in self:
            if rec.is_subscription:
                rec.action_lock()
            super(SaleOrderInherit, self).action_confirm()
