import re
from itertools import groupby

from markupsafe import Markup
import werkzeug

from odoo import api, fields, Command, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date, clean_context
from odoo.tools import email_split, float_repr, float_round, is_html_empty
import pdb

class InvoiceType(models.Model):
    _name = "invoice.type"
    _description = "Invoice Type"

    name = fields.Char(string="Invoice Type", required=True)
    active = fields.Boolean(string="Active", default=True)

class HrExpense(models.Model):
    _inherit = "hr.expense"

    sequence = fields.Char(string='Task ID', readonly=1,copy=False)
    type = fields.Selection([
        ("capex", "Capex"),
        ("opex", "Opex")], default='opex', string="Capex/Opex")
    invoice_no = fields.Char(string="Tax/Proforma Invoice No")
    invoice_type_id = fields.Many2one('invoice.type', string="Type of Invoice")
    user_id = fields.Many2one('res.users', string="Requested By", default=lambda self: self.env.user)
    is_payment_approval = fields.Boolean(string="Is Payment Approval", default=False)
    supplier_id = fields.Many2one('res.partner', string="Supplier")
    # basic_price = fields.Float(string="Basic Amount")
    total_invoice_value = fields.Monetary(
        string="Total Invoice Value",
        currency_field='company_currency_id',
        compute='_compute_expense_total_amount', store=True, readonly=False,
        tracking=True,
    )
    state = fields.Selection(selection_add=[
        ('to approve', 'To Approve')],
        string="Status",
        index=True, required=True, readonly=True, copy=False, tracking=True,
        ondelete={'to approve': 'set default'},
        default='draft')

    def action_submit_expenses(self):
        for record in self.filtered(lambda s: s.state in ['draft'] and s.is_payment_approval):
            # if not record.supplier_id:
            #     raise UserError(_("Cannot submit the bill without Supplier!"))
            if not record.invoice_type_id:
                raise UserError(_("Cannot submit the bill without Invoice Type!"))
            if not record.invoice_no:
                raise UserError(_("Cannot submit the bill without Invoice No.!"))
            if not record.type:
                raise UserError(_("Alert !! Kindly update the expense type as Capex/Opex."))
        res = super().action_submit_expenses()
        if res.get('res_id'):
            sheets = self.env['hr.expense.sheet'].browse(res.get('res_id', []))
            sheets.write({'sequence':self.sequence})       
        return res

    # Amount fields
    # tax_amount_currency = fields.Monetary(
    #     string="Tax amount in Currency",
    #     currency_field='currency_id',
    #     compute='_compute_tax_amount_currency', precompute=True, store=True,
    #     help="Tax amount in currency",
    # )
    # tax_amount = fields.Monetary(
    #     string="Tax amount",
    #     currency_field='company_currency_id',
    #     compute='_compute_tax_amount', precompute=True, store=True,
    #     help="Tax amount in company currency",
    # )
    # total_amount_currency = fields.Monetary(
    #     string="Total In Currency",
    #     currency_field='currency_id',
    #     compute='_compute_total_amount_currency', precompute=True, store=True, readonly=False,
    #     tracking=True,
    # )
    # untaxed_amount_currency = fields.Float(
    #     string="Untaxed Amount", store=True,
    # )
    # total_amount = fields.Monetary(
    #     string="Total",
    #     currency_field='company_currency_id',
    #     compute='_compute_total_amount', inverse='_inverse_total_amount', precompute=True, store=True, readonly=False,
    #     tracking=True,
    # )
    # price_unit = fields.Float(
    #     string="Unit Price",
    #     compute='_compute_price_unit', store=True, required=True, readonly=True,
    #     copy=True,
    #     digits='Product Price',
    # )

    # # Account fields
    # tax_ids = fields.Many2many(
    #     comodel_name='account.tax',
    #     relation='expense_tax',
    #     column1='expense_id',
    #     column2='tax_id',
    #     string="Included taxes",
    #     compute='_compute_tax_ids', precompute=True, store=True, readonly=False,
    #     domain="[('type_tax_use', '=', 'purchase')]",
    #     check_company=True,
    #     help="Both price-included and price-excluded taxes will behave as price-included taxes for expenses.",
    # )

    # @api.depends('currency_id', 'untaxed_amount_currency', 'date')
    # def _compute_currency_rate(self):
    #     """
    #         We want the default odoo rate when the following change:
    #         - the currency of the expense
    #         - the total amount in foreign currency
    #         - the date of the expense
    #         this will cause the rate to be recomputed twice with possible changes but we don't have the required fields
    #         to store the override state in stable
    #     """
    #     date_today = fields.Date.context_today(self)
    #     for expense in self:
    #         if expense.is_multiple_currency:
    #             if (
    #                     expense.currency_id != expense._origin.currency_id
    #                     or expense.untaxed_amount_currency != expense._origin.untaxed_amount_currency
    #                     or expense.date != expense._origin.date
    #             ):
    #                 expense.currency_rate = self.env['res.currency']._get_conversion_rate(
    #                     from_currency=expense.currency_id,
    #                     to_currency=expense.company_currency_id,
    #                     company=expense.company_id,
    #                     date=expense.date or date_today,
    #                 )
    #             else:
    #                 expense.currency_rate = expense.total_amount / expense.untaxed_amount_currency if expense.total_amount_currency else 1.0
    #         else:  # Mono-currency case computation shortcut, no need for the label if there is no conversion
    #             expense.currency_rate = 1.0
    #             expense.label_currency_rate = False
    #             continue

    #         expense.label_currency_rate = _(
    #             '1 %(exp_cur)s = %(rate)s %(comp_cur)s',
    #             exp_cur=expense.currency_id.name,
    #             rate=float_repr(expense.currency_rate, 6),
    #             comp_cur=expense.company_currency_id.name,
    #         )

    # @api.depends('currency_id', 'company_currency_id')
    # def _compute_is_multiple_currency(self):
    #     for expense in self:
    #         expense.is_multiple_currency = expense.currency_id != expense.company_currency_id

    # @api.depends('product_id.standard_price')
    # def _compute_from_product(self):
    #     for expense in self:
    #         expense.product_has_cost = expense.product_id and not expense.company_currency_id.is_zero(expense.product_id.standard_price)
    #         tax_ids = expense.product_id.supplier_taxes_id.filtered_domain(self.env['account.tax']._check_company_domain(expense.company_id))
    #         expense.product_has_tax = bool(tax_ids)
    #         if not expense.product_has_cost and expense.state in {'draft', 'reported'} and expense.quantity != 1:
    #             expense.quantity = 1

    # @api.depends('quantity', 'untaxed_amount_currency', 'tax_ids')
    # def _compute_total_amount_currency(self):
    #     for expense in self.filtered('product_has_cost'):
    #         base_lines = [expense._convert_to_tax_base_line_dict(price_unit=expense.untaxed_amount_currency, quantity=expense.quantity)]
    #         taxes_totals = self.env['account.tax']._compute_taxes(base_lines)['totals'][expense.currency_id]
    #         expense.total_amount_currency = taxes_totals['amount_untaxed'] + taxes_totals['amount_tax']

    # @api.onchange('untaxed_amount_currency')
    # def _inverse_total_amount_currency(self):
    #     for expense in self:
    #         if not expense.is_editable:
    #             raise UserError(_('You are not authorized to edit this expense.'))
    #         # expense.price_unit = (expense.untaxed_amount_currency / expense.quantity) if expense.quantity != 0 else 0.
    #         # expense.price_unit = expense.untaxed_amount_currency

    # @api.depends(
    #     'date',
    #     'company_id',
    #     'currency_id',
    #     'company_currency_id',
    #     'is_multiple_currency',
    #     'untaxed_amount_currency',
    #     'product_id',
    #     'employee_id.user_id.partner_id',
    #     'quantity',
    # )
    # def _compute_total_amount(self):
    #     for expense in self:
    #         if expense.is_multiple_currency:
    #             base_lines = [expense._convert_to_tax_base_line_dict(
    #                 price_unit=expense.untaxed_amount_currency * expense.currency_rate,
    #                 currency=expense.company_currency_id,
    #             )]
    #             taxes_totals = self.env['account.tax']._compute_taxes(base_lines)['totals'][expense.company_currency_id]
    #             expense.total_amount_currency = taxes_totals['amount_untaxed'] + taxes_totals['amount_tax']
    #             expense.total_amount = taxes_totals['amount_untaxed'] + taxes_totals['amount_tax']
    #         else:  # Mono-currency case computation shortcut
    #             expense.total_amount = expense.untaxed_amount_currency + expense.tax_amount_currency
    #             expense.total_amount_currency = expense.untaxed_amount_currency + expense.tax_amount_currency

    # def _inverse_total_amount(self):
    #     """ Allows to set a custom rate on the expense, and avoid the override when it makes no sense """
    #     for expense in self:
    #         if expense.is_multiple_currency:
    #             base_lines = [expense._convert_to_tax_base_line_dict(
    #                 price_unit=expense.untaxed_amount_currency,
    #                 currency=expense.company_currency_id,
    #             )]
    #             taxes_totals = self.env['account.tax']._compute_taxes(base_lines)['totals'][expense.company_currency_id]
    #             expense.tax_amount = taxes_totals['amount_tax']
    #         else:
    #             expense.total_amount_currency = expense.total_amount
    #             expense.tax_amount = expense.tax_amount_currency
    #         expense.currency_rate = expense.total_amount / expense.total_amount_currency if expense.total_amount_currency else 1.0
            # expense.price_unit = expense.total_amount / expense.quantity if expense.quantity else expense.total_amount
            # expense.price_unit = expense.untaxed_amount_currency

    # @api.depends('product_id', 'company_id')
    # def _compute_tax_ids(self):
    #     for _expense in self:
    #         expense = _expense.with_company(_expense.company_id)
    #         # taxes only from the same company
    #         expense.tax_ids = expense.product_id.supplier_taxes_id.filtered_domain(self.env['account.tax']._check_company_domain(expense.company_id))

    # @api.depends('untaxed_amount_currency', 'tax_ids')
    # def _compute_tax_amount_currency(self):
    #     # changed
    #     """
    #          Note: as total_amount_currency can be set directly by the user (for product without cost)
    #          or needs to be computed (for product with cost), `untaxed_amount_currency` can't be computed in the same method as `total_amount_currency`.
    #     """
    #     for expense in self:
    #         base_lines = [expense._convert_to_tax_base_line_dict(price_unit=expense.untaxed_amount_currency)]
    #         taxes_totals = self.env['account.tax']._compute_taxes(base_lines)['totals'][expense.currency_id]
    #         # pdb.set_trace()
    #         # print("Sumit Sinha", taxes_totals['amount_tax'],taxes_totals['amount_untaxed'])
    #         expense.tax_amount_currency = taxes_totals['amount_tax']
    #         expense.total_amount_currency = taxes_totals['amount_untaxed'] + taxes_totals['amount_tax']

    # @api.depends('untaxed_amount_currency', 'currency_rate', 'tax_ids', 'is_multiple_currency')
    # def _compute_tax_amount(self):
    #     """
    #          Note: as total_amount can be set directly by the user when the currency_rate is overriden,
    #          the tax must be computed after the total_amount.
    #     """
    #     for expense in self:
    #         if expense.is_multiple_currency:
    #             base_lines = [expense._convert_to_tax_base_line_dict(
    #                 price_unit=expense.untaxed_amount_currency,
    #                 currency=expense.company_currency_id,
    #             )]
    #             taxes_totals = self.env['account.tax']._compute_taxes(base_lines)['totals'][expense.company_currency_id]
    #             expense.tax_amount = taxes_totals['amount_tax']
    #         else:  # Mono-currency case computation shortcut
    #             expense.tax_amount = expense.tax_amount_currency

    # @api.depends('total_amount', 'untaxed_amount_currency')
    # def _compute_price_unit(self):
    #     """
    #        The price_unit is the unit price of the product if no product is set and no attachment overrides it.
    #        Otherwise it is always computed from the total_amount and the quantity else it would break the vendor bill
    #        when edited after creation.
    #     """
    #     for expense in self:
    #         expense.price_unit = expense.untaxed_amount_currency
    #     #     if expense.state not in {'draft', 'reported'}:
    #     #         continue
    #     #     product_id = expense.product_id
    #     #     if expense._needs_product_price_computation():
    #     #         expense.price_unit = product_id._price_compute(
    #     #             'standard_price',
    #     #             uom=expense.product_uom_id,
    #     #             company=expense.company_id,
    #     #         )[product_id.id]
    #     #     else:
    #     #         expense.price_unit = expense.company_currency_id.round(expense.untaxed_amount_currency / expense.quantity) if expense.quantity else 0.    

    # def _convert_to_tax_base_line_dict(self, base_line=None, currency=None, price_unit=None, quantity=None):
    #     self.ensure_one()
    #     return self.env['account.tax']._convert_to_tax_base_line_dict(
    #         base_line,
    #         currency=currency or self.currency_id,
    #         product=self.product_id,
    #         taxes=self.tax_ids,
    #         price_unit=self.untaxed_amount_currency,
    #         quantity=quantity if quantity is not None else 1,
    #         account=self.account_id,
    #         analytic_distribution=self.analytic_distribution,
    #     )    
    
    # def action_submit_expenses(self, **kwargs):
    #     res = super().action_submit_expenses(**kwargs)
    #     self._validate_ocr()
    #     return res

    # @api.model_create_multi
    # def create(self, vals_list):
    #     for vals in vals_list:
    #         product = vals.get('product_id', False)
    #     res = super().create(vals_list)
    #     return res

    # @api.model
    # def create(self, vals):
    #     # Create the record
    #     record = super(HrExpense, self).create(vals)
    #     # Calculate total_invoice_value
    #     record._compute_total_invoice_value()
    #     return record

    # def write(self, vals):
    #     # Call the super method to perform the write operation
    #     result = super(HrExpense, self).write(vals)
    #     # Calculate total_invoice_value for the current records
    #     for record in self:
    #         # Only compute if relevant fields are in vals or if they have changed
    #         if 'total_amount_currency' in vals or 'tax_amount_currency' in vals:
    #             record._compute_total_invoice_value()
    #     return result

    @api.model
    def create(self, vals):
        sequence_code = self.env['ir.sequence'].next_by_code('expense.sequence.code')
        if sequence_code:
            vals['sequence'] = sequence_code
        return super(HrExpense, self).create(vals)

    @api.depends('price_unit', 'untaxed_amount_currency', 'tax_amount')
    def _compute_expense_total_amount(self):
        for record in self:
            total_amount = record.untaxed_amount_currency or 0.0
            tax_amount = record.tax_amount_currency or 0.0
            record.total_invoice_value = total_amount + tax_amount

    @api.model
    def read(self, fields=None, load='_classic_read'):
        result = super(HrExpense, self).read(fields, load)
        for record in result:
            record['is_payment_approval'] = self.env.context.get('is_payment_approval_option', False)
        return result

    def _prepare_payments_vals(self):
        self.ensure_one()

        journal = self.sheet_id.journal_id
        payment_method_line = self.sheet_id.payment_method_line_id
        if not payment_method_line:
            raise UserError(_("You need to add a manual payment method on the journal (%s)", journal.name))
        move_lines = []
        tax_data = self.env['account.tax']._compute_taxes(
            [self._convert_to_tax_base_line_dict(price_unit=self.price_unit, currency=self.currency_id)],
            include_caba_tags=(self.payment_mode == 'company_account')
        )
        rate = abs(self.total_amount_currency / self.total_amount) if self.total_amount else 1.0
        base_line_data, to_update = tax_data['base_lines_to_update'][0]  # Add base line
        amount_currency = to_update['price_subtotal']
        expense_name = self.name.split("\n")[0][:64]
        base_move_line = {
            'name': f'{self.employee_id.name}: {expense_name}',
            'account_id': base_line_data['account'].id,
            'product_id': base_line_data['product'].id,
            'analytic_distribution': base_line_data['analytic_distribution'],
            'expense_id': self.id,
            'tax_ids': [Command.set(self.tax_ids.ids)],
            'tax_tag_ids': to_update['tax_tag_ids'],
            'amount_currency': amount_currency,
            'currency_id': self.currency_id.id,
        }
        move_lines.append(base_move_line)
        total_tax_line_balance = 0.0
        for tax_line_data in tax_data['tax_lines_to_add']:  # Add tax lines
            tax_line_balance = self.company_currency_id.round(tax_line_data['tax_amount'] / rate)
            total_tax_line_balance += tax_line_balance
            tax_line = {
                'name': self.env['account.tax'].browse(tax_line_data['tax_id']).name,
                'account_id': tax_line_data['account_id'],
                'analytic_distribution': tax_line_data['analytic_distribution'],
                'expense_id': self.id,
                'tax_tag_ids': tax_line_data['tax_tag_ids'],
                'balance': tax_line_balance,
                'amount_currency': tax_line_data['tax_amount'],
                'tax_base_amount': self.company_currency_id.round(tax_line_data['base_amount'] / rate),
                'currency_id': self.currency_id.id,
                'tax_repartition_line_id': tax_line_data['tax_repartition_line_id'],
            }
            move_lines.append(tax_line)
        base_move_line['balance'] = self.total_amount - total_tax_line_balance
        expense_name = self.name.split("\n")[0][:64]
        move_lines.append({  # Add outstanding payment line
            'name': f'{self.employee_id.name}: {expense_name}',
            'account_id': self.sheet_id._get_expense_account_destination(),
            'balance': -self.total_amount,
            'amount_currency': self.currency_id.round(-self.total_amount_currency),
            'currency_id': self.currency_id.id,
        })
        return {
            **self.sheet_id._prepare_move_vals(),
            'date': self.date,  # Overidden from self.sheet_id._prepare_move_vals() so we can use the expense date for the account move date
            'ref': self.name,
            'journal_id': journal.id,
            'move_type': 'entry',
            'amount': self.total_amount_currency,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'payment_method_line_id': payment_method_line.id,
            'currency_id': self.currency_id.id,
            'line_ids': [Command.create(line) for line in move_lines],
            'attachment_ids': [
                Command.create(attachment.copy_data({'res_model': 'account.move', 'res_id': False, 'raw': attachment.raw})[0])
                for attachment in self.message_main_attachment_id]
        }

    def _prepare_move_lines_vals(self):
        self.ensure_one()
        account = self.account_id
        if not account:
            # We need to do this as the installation process may delete the original account, and it doesn't recompute properly after.
            # This forces the default values if none is found
            if self.product_id:
                account = self.product_id.product_tmpl_id._get_product_accounts()['expense']
            else:
                account = self.env['ir.property']._get('property_account_expense_categ_id', 'product.category')
        expense_name = self.name.split('\n')[0][:64]
        return {
            'name': f'{self.employee_id.name}: {expense_name}',
            'account_id': account.id,
            'quantity': self.quantity or 1,
            'price_unit': self.price_unit,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom_id.id,
            'analytic_distribution': self.analytic_distribution,
            'expense_id': self.id,
            'partner_id': self.supplier_id.id if self.is_payment_approval else self.employee_id.sudo().work_contact_id.id,
            'tax_ids': [Command.set(self.tax_ids.ids)],
        }

    def _get_default_expense_sheet_values(self):
        # If there is an expense with total_amount == 0, it means that expense has not been processed by OCR yet
        expenses_with_amount = self.filtered(lambda expense: not (
            expense.currency_id.is_zero(expense.total_amount_currency)
            or expense.company_currency_id.is_zero(expense.total_amount)
            or (expense.product_id and not float_round(expense.quantity, precision_rounding=expense.product_uom_id.rounding))
        ))

        if any(expense.state != 'draft' or expense.sheet_id for expense in expenses_with_amount):
            raise UserError(_("You cannot report twice the same line!"))
        if not expenses_with_amount:
            raise UserError(_("You cannot report the expenses without amount!"))
        if len(expenses_with_amount.mapped('employee_id')) != 1:
            raise UserError(_("You cannot report expenses for different employees in the same report."))
        if any(not expense.product_id for expense in expenses_with_amount):
            raise UserError(_("You can not create report without category."))
        if len(self.company_id) != 1:
            raise UserError(_("You cannot report expenses for different companies in the same report."))

        # Check if two reports should be created
        own_expenses = expenses_with_amount.filtered(lambda x: x.payment_mode == 'own_account')
        company_expenses = expenses_with_amount - own_expenses
        create_two_reports = own_expenses and company_expenses

        sheets = (own_expenses, company_expenses) if create_two_reports else (expenses_with_amount,)
        values = []

        # We use a fallback name only when several expense sheets are created,
        # else we use the form view required name to force the user to set a name
        for todo in sheets:
            paid_by = 'company' if todo[0].payment_mode == 'company_account' else 'employee'
            sheet_name = _("New Expense Report, paid by %(paid_by)s", paid_by=paid_by) if len(sheets) > 1 else False
            if len(todo) == 1:
                sheet_name = todo.name
            else:
                dates = todo.mapped('date')
                if False not in dates:  # If at least one date isn't set, we don't set a default name
                    min_date = format_date(self.env, min(dates))
                    max_date = format_date(self.env, max(dates))
                    if min_date == max_date:
                        sheet_name = min_date
                    else:
                        sheet_name = _("%(date_from)s - %(date_to)s", date_from=min_date, date_to=max_date)

            values.append({
                'company_id': self.company_id.id,
                'employee_id': self[0].employee_id.id,
                'name': sheet_name,
                'expense_line_ids': [Command.set(todo.ids)],
                'state': 'draft',
                'invoice_no': self[0].invoice_no,
                'type': self[0].type,
                'invoice_type_id': self[0].invoice_type_id.id,
                'user_id': self[0].user_id.id,
                'is_payment_approval': self[0].is_payment_approval,
                'supplier_id': self[0].supplier_id.id,
            })
        return values

class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    sequence = fields.Char('Task ID',readonly=1)
    type = fields.Selection([
        ("capex", "Capex"),
        ("opex", "Opex")], default='opex', string="Capex/Opex")
    invoice_no = fields.Char(string="Tax/Proforma Invoice No")
    invoice_type_id = fields.Many2one('invoice.type', string="Type of Invoice")
    user_id = fields.Many2one('res.users', string="Requested By", default=lambda self: self.env.user)
    is_payment_approval = fields.Boolean(string="Is Payment Approval", default=False)
    supplier_id = fields.Many2one('res.partner', string="Supplier")
    state = fields.Selection(
        selection=[
            ('draft', 'To Submit'),
            ('submit', 'Submitted'),
            ('to approve', 'To Approve'),
            ('approve', 'Approved'),
            ('post', 'Posted'),
            ('done', 'Done'),
            ('cancel', 'Refused')
        ],
        string="Status",
        compute='_compute_state', store=True, readonly=True,
        index=True,
        required=True,
        default='draft',
        tracking=True,
        copy=False,
    )
    approval_status = fields.Char(string='Approval Status', compute='compute_approval_state', store=True, copy=False,
                                 tracking=True)
    approval_document = fields.Many2one('multi.approval', string='Approval Record', copy=False)

    reason_approved = fields.Text(string='Approval Comments')
    approval_level = fields.Selection([
        ("none", "None"),
        ("level1", "1 Level"),
        ("level2", "2 Level"),
        ("level3", "3 Level"),
        ("level4", "4 Level"),
        ("level5", "5 Level"),
        ("level6", "6 Level"),
    ], default="none", string="Approval Level", tracking=True,store=True,compute='_compute_approval_level')
    x_has_request_approval = fields.Boolean(string="Has Request Approval")
    x_review_result = fields.Char(string="Review Result")

    @api.depends("employee_id")
    def _compute_approval_level(self):
        for rec in self:
            rec.approval_level = "none"
            if not rec.employee_id or not rec.employee_id.department_id:
                continue

            # all approval lines linked to this department
            approval_ids = self.env["multi.approval.type.line"].search([
                ("type_id.department_id", "=", rec.employee_id.department_id.id)
            ])

            if not approval_ids:
                continue
            employee_user = rec.employee_id.user_id
            # find parent type_ids that have current employee
            parent_with_emp = approval_ids.filtered(
                lambda l: l.user_id == employee_user
            ).mapped("type_id")

            # keep only parents NOT containing employee
            filtered_parents = approval_ids.filtered(
                lambda l: l.type_id not in parent_with_emp
            )

            if filtered_parents:
                # group by parent type_id
                grouped = {}
                for line in filtered_parents:
                    grouped.setdefault(line.type_id, []).append(line)

                # pick parent with max children
                max_parent, max_lines = max(grouped.items(), key=lambda x: len(x[1]))
                max_len = len(max_parent.line_ids)
                # map length → level
                if max_len >= 6:
                    rec.approval_level = "level6"
                else:
                    rec.approval_level = f"level{max_len}"

    @api.depends('approval_document.type_id.state', 'approval_document.line_ids.state')
    def compute_approval_state(self):
        for record in self:
            if record.approval_document:
                line_states = record.approval_document.line_ids.mapped('state')
                if all(state == 'Draft' for state in line_states):
                    record.approval_status = 'Waiting For Approval'
                elif 'Waiting for Approval' in line_states:
                    waiting_lines = record.approval_document.line_ids.filtered(
                        lambda l: l.state == 'Waiting for Approval')
                    if waiting_lines:
                        record.approval_status = f"Waiting for {', '.join(waiting_lines.mapped('name'))} Approval"
                elif all(state == 'Approved' for state in line_states):
                    record.approval_status = 'Approved'
                elif 'Refused' in line_states:
                    record.approval_status = 'Rejected'
                elif 'Cancel' in line_states:
                    record.approval_status = 'Cancelled'
            else:
                rec = self.env['multi.approval.type'].sudo().search(
                    [('model_id', '=', 'hr.expense.sheet'), ('state', '=', 'confirm')], limit=1)
                if rec:
                        record.approval_status = 'To Submit for Approval'
                else:
                        record.approval_status = 'Not Applicable'

    def action_approve(self):
        for rec in self:
            rec.write({'state':'approve',
                               'user_id': rec.user_id.id or rec.env.user.id,
                                'approval_date': fields.Date.context_today(rec),
            })
            user_email = rec.user_id.email if rec.user_id else ''
            employee_email = rec.employee_id.work_email if rec.employee_id else ''
            template = self.env.ref('hr_expense_extended.email_template_expense_approval_email')
            template.write({'email_to':', '.join(filter(None, [user_email, employee_email])),
                            'subject':'Expense Approved - %s'%(rec.name)})
            template.send_mail(self.id, force_send=True)
            rec.activity_update()
            group = self.env.ref('hr_expense_extended.group_post_journal_expense')
            users = group.users
            for rec1 in users:
                # if not rec1.user_id:
                #     raise ValidationError("In-app notifications can be sent to employees who are linked to users")
                self.activity_schedule(
                    activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                    summary="Post Journal Reminder: Post Journal reminder",
                    note=f"Expenses has been approved.Kindly Post the journal for below expenses:{self.name} .",
                    user_id=rec1.id,
                    date_deadline=fields.Date.today()
                )

    def action_reject(self):
        if self.account_move_ids:  # Todo: in 17.3+, edit it to allow draft entries
            raise UserError(_("You cannot cancel an expense sheet linked to a journal entry"))
        self.write({'state':'cancel'})
        self.activity_update()

    @api.model
    def create(self, vals):
        if self.env.context.get('is_payment_approval_option'):
            vals['is_payment_approval'] = True
        return super(HrExpenseSheet, self).create(vals)

    def write(self, vals):
        if self.env.context.get('is_payment_approval_option'):
            vals['is_payment_approval'] = True
        return super(HrExpenseSheet, self).write(vals)

    @api.model
    def read(self, fields=None, load='_classic_read'):
        result = super(HrExpenseSheet, self).read(fields, load)
        for record in result:
            record['is_payment_approval'] = record.get('is_payment_approval', False)
        return result

    def _check_bank_account(self):
        no_bank_user = self.filtered(
            lambda sheet: sheet.payment_mode == 'own_account' and
                          not sheet.user_id.partner_id.bank_ids
        )
        # if no_bank_user:
        #     action = no_bank_user._get_records_action(name=_("User(s)"))
        #     raise RedirectWarning(
        #         _("The following User(s) do not have associated bank details in the res.partner table."),
        #         action,
        #         _("Go to User(s)")
        #     )

    def _do_create_moves(self):
        self = self.with_context(clean_context(self.env.context))  # remove default_*
        skip_context = {
            'skip_invoice_sync': True,
            'skip_invoice_line_sync': True,
            'skip_account_move_synchronization': True,
        }
        own_account_sheets = self.filtered(lambda sheet: sheet.payment_mode == 'own_account')
        company_account_sheets = self - own_account_sheets

        moves = self.env['account.move'].create([sheet._prepare_bills_vals() for sheet in own_account_sheets])
        # Set the main attachment on the moves directly to avoid recomputing the
        # `register_as_main_attachment` on the moves which triggers the OCR again
        for move in moves:
            move.message_main_attachment_id = move.attachment_ids[0] if move.attachment_ids else None
        for expense in self.expense_line_ids.filtered(lambda expense: expense.sale_order_id and not expense.analytic_distribution):
            if not expense.sale_order_id.analytic_account_id:
                expense.sale_order_id._create_analytic_account()
            expense.write({
                'analytic_distribution': {expense.sale_order_id.analytic_account_id.id: 100}
            })
        payments = self.env['account.payment'].with_context(**skip_context).create([
            expense._prepare_payments_vals() for expense in company_account_sheets.expense_line_ids
        ])
        moves |= payments.move_id
        # moves.action_post()
        self.activity_update()

        return moves

    def _prepare_bills_vals(self):
        self.ensure_one()
        print(self.expense_line_ids.message_main_attachment_id,'llllllllllllll')
        attachments = []
        for line in self.expense_line_ids:
            line_attachments = self.env['ir.attachment'].search([
                ('res_model', '=', line._name),
                ('res_id', '=', line.id),
            ])
            for attachment in line_attachments:
                attachments.append(
                    Command.create(attachment.copy_data({
                        'res_model': 'account.move',
                        'res_id': False,
                        'raw': attachment.raw,
                    })[0])
                )
        # stop
        return {
            **self._prepare_move_vals(),
            'invoice_date': self.accounting_date or fields.Date.context_today(self),
            'journal_id': self.journal_id.id,
            'ref': self[0].invoice_no,
            'move_type': 'in_invoice',
            'partner_id': self[0].supplier_id.id if self[0].is_payment_approval else self.employee_id.sudo().work_contact_id.id,
            'currency_id': self.currency_id.id,
            'line_ids': [Command.create(expense._prepare_move_lines_vals()) for expense in self.expense_line_ids],
            'partner_bank_id': self.employee_id.sudo().bank_account_id.id,
            'attachment_ids':attachments,
            'expense_invoice_no': self[0].invoice_no,
            'expense_type': self[0].type,
            'expense_invoice_type_id': self[0].invoice_type_id.id,
            'expense_user_id': self[0].user_id.id,
            'is_payment_approval': self[0].is_payment_approval,
            # 'supplier_id': self[0].supplier_id.id,
            'expense_sequence':self[0].sequence,
        }

    def _prepare_move_vals(self):
        self.ensure_one()
        return {
            # force the name to the default value, to avoid an eventual 'default_name' in the context
            # to set it to '' which cause no number to be given to the account.move when posted.
            'name': '/',
            'date': self.accounting_date or max(self.expense_line_ids.filtered(lambda exp: exp.date).mapped('date'), default=fields.Date.context_today(self)),
            'expense_sheet_id': self.id,
        }



