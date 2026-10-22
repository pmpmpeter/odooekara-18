from odoo import models, fields, api, _
from odoo.exceptions import UserError
from markupsafe import Markup
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class BillApprovalStepLog(models.Model):
    _name = 'bill.approval.step.log'
    _description = 'Bill Approval Step Log'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id'

    bill_id = fields.Many2one('bill.approval', ondelete='cascade', required=True)
    step_name = fields.Char(string='Step')
    action = fields.Selection([
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('bill_created', 'Bill Created'),
        ('payment_created', 'Payment Created'),
    ])
    user_id = fields.Many2one('res.users', string='By', default=lambda s: s.env.uid)
    date = fields.Datetime(default=fields.Datetime.now)
    note = fields.Text(string='Note')
    account_move_id = fields.Many2one('account.move', string='Bill / JE')
    payment_id = fields.Many2one('account.payment', string='Payment')


class BillApproval(models.Model):
    _name = 'bill.approval'
    _description = 'Bill Approval'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    # ── Reference ─────────────────────────────────────────────────────────────
    name = fields.Char(
        string='Reference', default='New', readonly=True, copy=False,
    )

    # ── Supplier ───────────────────────────────────────────────────────────────
    timestamp = fields.Datetime(string='Timestamp', default=fields.Datetime.now)
    supplier_name = fields.Many2one(
        'res.partner', string='Supplier Name', required=True, tracking=True,domain=[('state','=','approve')]
    )
    email = fields.Char(
        string='Email Address', related='create_uid.email', readonly=True,
    )

    # ── Classification ─────────────────────────────────────────────────────────
    capex_opex = fields.Selection([
        ('capex', 'Capex'),
        ('opex', 'Opex'),
    ], string='Capex/Opex', tracking=True)

    expense_head_capex = fields.Many2one(
        'account.account',
        string='Expense/GL Head',
        domain="[('account_type', '!=', 'expense')]"
    )

    expense_head_opex = fields.Many2one(
        'account.account',
        string='Expense/GL Head',
        domain="[('account_type','=','expense')]"
    )

    expense_head = fields.Many2one(
        'account.account',
        string='Expense/GL Head',
        compute='_compute_expense_head',
        store=True
    )

    @api.depends('expense_head_capex', 'expense_head_opex', 'capex_opex')
    def _compute_expense_head(self):
        for rec in self:

            if rec.capex_opex == 'capex':
                rec.expense_head = rec.expense_head_capex

            elif rec.capex_opex == 'opex':
                rec.expense_head = rec.expense_head_opex

            else:
                rec.expense_head = False

    invoice_no = fields.Char(string='Document No')
    # invoice_type = fields.Selection([
    #     ('tax', 'Tax Invoice'),
    #     ('proforma', 'Proforma Invoice'),
    # ], string='Type of Document', tracking=True)
    document_type = fields.Many2one('bill.approval.document',string='Document Type',tracking=True)
    invoice_date = fields.Date(string='Document Date')

    # ── Amounts ────────────────────────────────────────────────────────────────
    taxable_value = fields.Float(string='Taxable Value',required=True)
    gst = fields.Float(string='GST')
    total_value = fields.Float(
        string='Total Invoice Value', tracking=True,
        compute='_compute_total_value', store=True,
    )

    # GST treatment: forward charge (GST paid to the vendor, who remits it)
    # vs reverse charge/RCM (buyer pays GST directly to the government, so
    # it never forms part of the cash paid to the vendor). This can vary
    # bill to bill, so it's a per-record flag rather than a global setting.
    is_reverse_charge = fields.Boolean(
        string='GST Reverse Charge (RCM)', default=False, tracking=True,
        help="Tick this if GST on this bill is payable directly to the "
             "government under reverse charge, rather than to the vendor."
    )

    # TDS is usually only known precisely once the actual vendor bill is
    # created and the TDS smart button is used (see account.py, which reads
    # the real posted withholding entries). This field lets an estimated
    # TDS amount be captured already at the approval stage, so approvers
    # can see a realistic "Total Payable" before any bill even exists. The
    # actual payment cap enforced in account.py reconciles against the real
    # TDS on the linked bill(s) once they exist, not just this estimate.
    tds_amount = fields.Float(
        string='TDS Deducted (Estimated) - not used', tracking=True,
        help="Estimated TDS to be withheld from this vendor, entered at "
             "approval time. The real payment limit is later enforced "
             "against the actual TDS posted on the linked bill(s)."
    )

    total_payable = fields.Float(
        string='Total Payable', tracking=True,
        compute='_compute_total_payable', store=True,
        help="Estimated net cash payable to the vendor: Taxable Value "
             "(+ GST, only if not reverse charge) minus estimated TDS."
    )

    tds_deducted_actual = fields.Float(
        string='TDS Deducted', tracking=True,
        compute='_compute_total_payable', store=True,
        help="Actual TDS withheld so far, from all five places it can be "
             "entered: (1) tax line on the bill's invoice lines, (2) TDS "
             "smart button on the bill, (3) TDS smart button on the payment, "
             "(4) TDS line in the payment's Other Charges tab, (5) TDS tax "
             "line on a Journal or Credit Card Expense entry linked to this "
             "approval. TDS is part of the Taxable amount and counts as paid "
             "(it is paid to the Government on the vendor's behalf)."
    )
    # Where the TDS came from (they add up to TDS Deducted), so a TDS entered
    # twice for the same amount is easy to spot.
    tds_bill_lines = fields.Float(
        string='TDS: Bill Lines', compute='_compute_total_payable', store=True,
        help="TDS entered as a tax line on the bill's invoice lines.")
    tds_bill_button = fields.Float(
        string='TDS: Bill Button', compute='_compute_total_payable', store=True,
        help="TDS entered with the TDS smart button on the bill (also includes "
             "TDS on advance payments mapped to the bill).")
    tds_payment_button = fields.Float(
        string='TDS: Payment Button', compute='_compute_total_payable', store=True,
        help="TDS entered with the TDS smart button on the payment.")
    tds_payment_charges = fields.Float(
        string='TDS: Payment Other Charges', compute='_compute_total_payable', store=True,
        help="TDS entered as a line in the payment's Other Charges tab. "
             "The payment Amount is already net of it.")
    tds_journal_entries = fields.Float(
        string='TDS: Journal/Credit Card Entries', compute='_compute_total_payable', store=True,
        help="TDS entered as a tax line on a Journal or Credit Card Expense "
             "entry linked to this approval (move_type 'entry', no payment_id).")

    remaining_taxable_value = fields.Float(
        string='Remaining Payable (Bill)', tracking=True,
        compute='_compute_remaining_taxable_value', store=True,
        help="Approved Taxable Value minus the taxable value already "
             "billed under this approval. Used to default new bill lines "
             "so a second/partial bill doesn't re-claim the full approved "
             "amount."
    )

    @api.constrains('tds_amount', 'taxable_value')
    def _check_tds_amount(self):
        for record in self:
            if record.tds_amount < 0:
                raise ValidationError(_("TDS Deducted cannot be negative."))
            if record.tds_amount > record.taxable_value:
                raise ValidationError(_(
                    "TDS Deducted (%s) cannot exceed the Taxable Value (%s)."
                ) % (record.tds_amount, record.taxable_value))

    @api.model
    def _is_tds_charge_line(self, line):
        """A line in a payment's Other Charges tab that is TDS: a deduction
        (negative amount) on a TDS tax. Other charges that are not TDS are
        not counted."""
        # ANY-TDS-TAX: whatever the tax is called or whichever account it uses, a deduction
        # (negative amount) taken from the vendor payment counts as TDS. Positive charges do not.
        tax = line.tax_id
        if not tax or line.other_charge >= 0:
            return False
        return True

    def _get_payment_charges_tds(self, payments, billed_moves):
        """TDS entered in the Other Charges tab of the given posted payments.
        Payments mapped to a bill as an advance (advance_payment_ids) are left
        out: the bill's own withholding total already includes their TDS, so
        counting them here as well would count the same TDS twice."""
        if 'other_charges_lines' not in payments._fields:
            return 0.0
        if 'advance_payment_ids' in billed_moves._fields:
            payments = payments - billed_moves.mapped('advance_payment_ids')
        total = 0.0
        for pay in payments:
            if 'other_charge_applicable' in pay._fields and not pay.other_charge_applicable:
                continue
            for line in pay.other_charges_lines:
                if self._is_tds_charge_line(line):
                    total += -line.other_charge
        return total

    @api.depends('taxable_value', 'gst', 'is_reverse_charge', 'tds_amount',
                 'account_move_ids.amount_total', 'account_move_ids.amount_untaxed',
                 'account_move_ids.move_type', 'account_move_ids.state',
                 'account_move_ids.origin_payment_id',
                 'account_move_ids.line_ids.tax_line_id',
                 'account_move_ids.line_ids.balance',
                 'account_move_ids.l10n_in_total_withholding_amount',
                 'payment_ids.move_id.l10n_in_total_withholding_amount',
                 # No 'payment_ids.other_charges_lines...' path here on purpose:
                 # that field lives in accounts_extended, which is not a declared
                 # dependency and may not be loaded yet when this module is set
                 # up (Odoo then refuses to load the registry). Other Charges are
                 # locked once a payment leaves draft, and posting changes
                 # payment_ids.state, so this still recomputes at the right time.
                 'payment_ids.state')
    def _compute_total_payable(self):
        for rec in self:
            # Only POSTED bills count -- a draft bill must not reduce
            # Total Payable/Remaining figures before it's confirmed.
            billed_moves = rec.sudo().account_move_ids.filtered(
                lambda m: m.move_type != 'entry' and m.state == 'posted'
            )
            bill_side_tds = sum(billed_moves.mapped('l10n_in_total_withholding_amount'))

            # TDS can ALSO be applied via the smart button directly on a
            # PAYMENT's own journal entry -- a third mechanism, separate
            # from both bill tax-lines and bill-side smart-button TDS.
            # Confirmed via a real case: a payment's own move had its own
            # TDS smart-button entry (l10n_in_withhold_move_ids), which
            # was completely invisible to this compute until now, making
            # the reported TDS Deducted understate the true total.
            # search() against the stored column, NOT filtered() on .state:
            # this database has payments in a state ('to approve') that the
            # state field cannot convert while it is being recomputed (see
            # _compute_gst_taxable_paid), and filtered() crashes the upgrade.
            posted_payments = self.env['account.payment'].sudo().search([
                ('id', 'in', rec.sudo().payment_ids.ids),
                ('state', '=', 'posted'),
            ])
            payment_side_tds = sum(posted_payments.mapped('move_id.l10n_in_total_withholding_amount'))

            # Fourth place: TDS typed into the payment's own Other Charges
            # tab. The payment Amount is already NET of it (amount = base +
            # charges), which is why the cheque prints the right figure.
            payment_charges_tds = rec._get_payment_charges_tds(posted_payments, billed_moves)

            # JOURNAL-ENTRY-TDS: TDS entered as a tax line on a Journal or
            # Credit Card Expense entry linked to this approval (move_type
            # 'entry', no payment_id -- a real account.payment's own move
            # is also move_type 'entry' but already counted above via
            # payment_side_tds, so it's excluded here the same way
            # _payment_position()'s own journal-entry handling excludes
            # it). Same TDS tax-line convention used everywhere else in
            # this module.
            entry_moves_for_tds = rec.sudo().account_move_ids.filtered(
                lambda m: m.move_type == 'entry' and m.state == 'posted' and not m.origin_payment_id
            )
            is_tds_tax = lambda t: t and ('tds' in (t.name or '').lower()
                                           or (t.amount_type == 'percent' and t.amount < 0))
            entry_tds_lines = entry_moves_for_tds.line_ids.filtered(lambda l: is_tds_tax(l.tax_line_id))
            entry_tds = abs(sum(entry_tds_lines.mapped('balance')))
            rec.tds_journal_entries = entry_tds

            smart_button_tds = bill_side_tds + payment_side_tds + payment_charges_tds + entry_tds
            rec.tds_bill_button = bill_side_tds
            rec.tds_payment_button = payment_side_tds
            rec.tds_payment_charges = payment_charges_tds

            if billed_moves:
                # IMPORTANT: the entitlement figure used here must be
                # based on what's actually BILLED so far -- NOT the
                # approval's full original taxable_value+gst. Using the
                # full approved amount here was a bug: for a PARTIALLY
                # billed approval (this bill covers only part of what
                # was approved), it wrongly treated the entire unbilled
                # remainder as if it were "TDS deducted", massively
                # inflating this figure. Using the bill's own real
                # taxable+GST instead scales correctly with partial
                # billing and isolates only the genuine TDS portion.
                billed_taxable = sum(billed_moves.mapped('amount_untaxed'))
                gst_lines = billed_moves.line_ids.filtered(
                    lambda l: l.tax_line_id and 'gst' in (l.tax_line_id.name or '').lower()
                )
                billed_gst = abs(sum(gst_lines.mapped('balance')))
                billed_gross_entitlement = billed_taxable if rec.is_reverse_charge else billed_taxable + billed_gst

                # amount_total already nets out any tax-line TDS; smart-
                # button TDS is separate and not yet reflected in it.
                real_net_payable = sum(billed_moves.mapped('amount_total')) - smart_button_tds
                rec.total_payable = real_net_payable
                rec.tds_deducted_actual = billed_gross_entitlement - real_net_payable
                rec.tds_bill_lines = max(billed_gross_entitlement - sum(billed_moves.mapped('amount_total')), 0.0)
            else:
                # No bill yet (advance-payment phase) -- nothing real to
                # go on, so fall back to the approval-time estimate.
                vendor_entitlement = rec.taxable_value if rec.is_reverse_charge else rec.taxable_value + rec.gst
                # TDS deducted through the payment smart button before any
                # bill exists is real TDS, so report it (was always 0 here).
                rec.tds_bill_lines = 0.0
                rec.tds_deducted_actual = payment_side_tds + payment_charges_tds + entry_tds
                rec.total_payable = vendor_entitlement - payment_side_tds - payment_charges_tds - entry_tds

    remaining_gst_value = fields.Float(
        string='Remaining GST', tracking=True,
        compute='_compute_remaining_taxable_value', store=True,
        help="Approved GST minus GST actually consumed so far across "
             "posted bills under this approval, tracked as its own "
             "bucket -- separate from Taxable Value and never affected "
             "by TDS (TDS is a distinct tax line and is excluded from "
             "this GST figure entirely, whether entered as a tax line "
             "on the bill or via the TDS smart button)."
    )

    @api.depends('taxable_value', 'gst',
                 'account_move_ids.amount_untaxed',
                 'account_move_ids.move_type',
                 'account_move_ids.state',
                 'account_move_ids.line_ids.tax_line_id',
                 'account_move_ids.line_ids.balance')
    def _compute_remaining_taxable_value(self):
        for rec in self:
            # Only POSTED bills reduce what's still available to bill --
            # a DRAFT bill is not yet committed and must not shrink this
            # figure prematurely (confirmed: it was doing so before this
            # fix, reducing Remaining Payable the moment a bill was
            # created, even before it was ever posted/confirmed).
            billed_moves = rec.sudo().account_move_ids.filtered(
                lambda m: m.move_type != 'entry' and m.state == 'posted'
            )
            already_billed = sum(billed_moves.mapped('amount_untaxed'))
            rec.remaining_taxable_value = rec.taxable_value - already_billed

            # GST is isolated by looking at the actual tax lines on each
            # bill and matching by tax name -- this correctly excludes
            # TDS lines (whether TDS was entered as a tax line on the
            # bill, or later via the smart button, neither ever has "GST"
            # in its tax name), so TDS never bleeds into this bucket.
            gst_lines = billed_moves.line_ids.filtered(
                lambda l: l.tax_line_id and 'gst' in (l.tax_line_id.name or '').lower()
            )
            already_billed_gst = abs(sum(gst_lines.mapped('balance')))
            rec.remaining_gst_value = rec.gst - already_billed_gst

    # ── Vendor payment ceiling ───────────────────────────────────────────────
    # The ceiling on cash paid to the vendor: approved taxable (+ GST unless
    # RCM) minus ALL TDS known so far, whichever of the three places it was
    # entered (invoice-line tax, bill smart button, payment smart button).
    # TDS can arrive before or after a payment, so besides blocking a payment
    # that would exceed this (account.payment._check_payment_limit), the
    # figures below make an excess visible if TDS is entered later.
    def _get_payment_cap(self):
        self.ensure_one()
        entitlement = self.taxable_value if self.is_reverse_charge else self.taxable_value + self.gst
        # Only TDS that has actually been entered counts (invoice-line tax,
        # bill smart button, payment smart button). There is no estimate:
        # until TDS is entered the ceiling is the full approved amount.
        return entitlement - self.tds_deducted_actual

    # Every stored figure derived from payments / TDS. When one of them is
    # refreshed by hand (add_to_compute) the ORM does NOT automatically
    # refresh the fields that depend on it, which left Remaining / Balance /
    # Excess showing values from before the latest TDS. So refresh them all.
    _BALANCE_FIELDS = (
        'total_payable', 'tds_deducted_actual', 'total_paid_amount',
        'tds_bill_lines', 'tds_bill_button', 'tds_payment_button', 'tds_payment_charges',
        'total_taxable_paid', 'total_gst_paid', 'taxable_settled',
        'remaining_taxable_to_pay', 'remaining_gst_to_pay',
        'vendor_balance_payable', 'excess_paid',
    )

    def _mark_balances_for_recompute(self):
        moves = self.account_move_ids | self.payment_ids.move_id
        # The TDS total on a bill / payment entry is a NON-stored computed
        # field, so its cached value can be stale: drop it first.
        if 'l10n_in_total_withholding_amount' in moves._fields:
            moves.invalidate_recordset(['l10n_in_total_withholding_amount'])
        for fname in self._BALANCE_FIELDS:
            self.env.add_to_compute(self._fields[fname], self)

    def _check_billed_not_below_paid(self, exclude_bill_ids=None):

        # REVERT-TO-APPROVED-ONLY: disabled at the user's request. Bills and payments
        # are checked against the APPROVED taxable/GST amounts only, as originally
        # designed. To re-enable this cross-check later, remove this early return.
        return

        """BILLED-VS-PAID-CANCEL: the other half of the billed-vs-paid rule in
        account.py. Cancelling a bill (exclude_bill_ids) is refused if doing so would
        drop this approval's billed taxable, or billed GST, below what non-advance
        payments have already settled -- because those payments would then be
        settling taxable or GST that no longer has a bill behind it. Advance
        payments are exempt, exactly as in the payment-side check."""
        self.ensure_one()
        Move = self.env['account.move']
        billed_taxable, billed_gst = Move._billed_position(self, exclude_ids=exclude_bill_ids)
        posted = self.env['account.payment'].search([
            ('approval_id', '=', self.id), ('state', '=', 'posted'),
            ('advance_payment', '=', False),
        ])
        # CANCEL-TDS-ATTRIBUTION-FIX: self.tds_deducted_actual is the approval's TOTAL
        # TDS from all four sources, including any TDS an ADVANCE payment carries on its
        # own smart button or Other Charges. That TDS is not "settled by non-advance
        # payments" and must not count here, or a bill with no non-advance payment
        # against it yet could be wrongly refused a cancel. Only TDS actually tied to a
        # BILL (its own tax line, or its own TDS button) belongs on the bill side; TDS
        # from a payment only counts if that specific payment is non-advance.
        bill_tds = self.tds_bill_lines + self.tds_bill_button
        payment_tds = 0.0
        for pay in posted:
            payment_tds += -sum(l.other_charge for l in pay.other_charges_lines if l.other_charge < 0)
            payment_tds += pay.move_id.l10n_in_total_withholding_amount or 0.0
        settled_taxable = sum(posted.mapped('taxable_paid_amount')) + bill_tds + payment_tds
        settled_gst = sum(posted.mapped('gst_paid_amount'))
        fmt = lambda v: '{:,.2f}'.format(v)
        if float_compare(settled_taxable, billed_taxable, precision_rounding=0.01) > 0:
            raise UserError(_(
                "Cannot cancel this bill: non-advance payments already settle more taxable "
                "than would remain billed.\n"
                "Approval: %(ref)s\n"
                "Billed taxable after cancelling: %(billed)s\n"
                "Already settled (paid + TDS, non-advance): %(settled)s\n\n"
                "Reverse or reclassify the relevant payment(s) as an advance first, or do "
                "not cancel this bill.",
                ref=self.name, billed=fmt(billed_taxable), settled=fmt(settled_taxable)))
        if not self.is_reverse_charge and float_compare(settled_gst, billed_gst, precision_rounding=0.01) > 0:
            raise UserError(_(
                "Cannot cancel this bill: non-advance payments already settle more GST than "
                "would remain billed.\n"
                "Approval: %(ref)s\n"
                "Billed GST after cancelling: %(billed)s\n"
                "Already settled GST (non-advance): %(settled)s\n\n"
                "Reverse or reclassify the relevant payment(s) as an advance first, or do "
                "not cancel this bill.",
                ref=self.name, billed=fmt(billed_gst), settled=fmt(settled_gst)))

    def _payment_position(self):
        """Fresh payment position, per bucket. TDS is part of the TAXABLE
        bucket, so:
          taxable_excess = taxable paid + TDS deducted - approved taxable
          gst_excess     = GST paid - approved GST   (not applicable to RCM)
          total_excess   = cash paid - (approved amount - TDS)
        """
        self.ensure_one()
        self._mark_balances_for_recompute()
        # Counting state == 'posted' only left a window: a payment that has
        # cleared all approval levels but not yet been Confirmed sits at
        # 'approved', invisible to this query, so a second payment for the
        # same bill could pass the limit check and clear approval too, only
        # failing later at Confirm against an already-reconciled journal
        # entry (see BA-00090). Count anything that isn't a throwaway draft
        # or cancelled -- any payment already submitted is a real commitment
        # against this approval's balance, posted or not.
        posted = self.env['account.payment'].search([
            ('approval_id', '=', self.id),
            ('state', 'not in', ('draft', 'cancel')),
        ])
        paid = sum(posted.mapped('amount'))
        paid_taxable = sum(posted.mapped('taxable_paid_amount'))
        paid_gst = sum(posted.mapped('gst_paid_amount'))

        # tds_deducted_actual is posted-only by design (see
        # _compute_total_payable -- it's the accounting-truth figure used
        # in reports). That leaves the exact same window open here on the
        # TDS leg that 'posted' used to leave open on the cash leg above: a
        # payment that hasn't posted yet can already carry its own TDS (a
        # smart-button withholding entry, or an Other Charges TDS line),
        # invisible to tds_deducted_actual and therefore to this cap check,
        # until it does post. Add that committed-but-unposted TDS back in
        # here, to both the taxable-bucket figure and the cash cap, so a
        # second in-flight payment's TDS claim cannot slip past the way a
        # second payment's cash already could before this fix.
        pending = self.env['account.payment'].search([
            ('approval_id', '=', self.id),
            ('state', 'not in', ('draft', 'cancel', 'posted')),
        ])
        billed_moves = self.account_move_ids.filtered(
            lambda m: m.move_type != 'entry' and m.state == 'posted'
        )
        pending_tds = sum(pending.mapped('move_id.l10n_in_total_withholding_amount'))
        pending_tds += self._get_payment_charges_tds(pending, billed_moves)

        # JOURNAL-ENTRY CEILING: Create Bill's "Journal Entry" option
        # makes a bare account.move (move_type == 'entry') with no
        # invoice lines -- hand-typed debit/credit lines after that have
        # no tax structure to split into taxable/GST the way a bill has.
        # Rather than leave it completely unchecked, fold its real cash
        # impact into the one universal, always-applicable guard: the
        # overall cap (cannot leave the vendor paid more than payable
        # after TDS). payment_id == False excludes a payment's OWN
        # auto-generated journal entry -- that is also move_type=='entry'
        # and also carries approval_id directly, and is already counted
        # a few lines above via account.payment.amount; without this
        # exclusion every normal payment would be double-counted here.
        entry_moves = self.env['account.move'].search([
            ('approval_id', '=', self.id),
            ('move_type', '=', 'entry'),
            ('state', '=', 'posted'),
            ('origin_payment_id', '=', False),
        ])
        entry_paid = 0.0
        entry_gst = 0.0
        for m in entry_moves:
            vendor_lines = m.line_ids.filtered(lambda l: l.partner_id == m.partner_id)
            # SIGN FIX: crediting the vendor's payable account is what
            # reduces what's owed to them (confirmed live) -- the previous
            # debit - credit direction computed a NEGATIVE number for
            # exactly that case, floored to 0.0 by max(), so an unlimited
            # Journal-entry overpayment posted with no error at all.
            entry_paid += max(
                sum(vendor_lines.mapped('credit')) - sum(vendor_lines.mapped('debit')),
                0.0,
            )
            # GST-ON-JOURNAL-ENTRY: confirmed live that a GST tax line can
            # also be entered on these entries -- previously invisible to
            # paid_gst entirely (that figure only ever summed
            # account.payment records). Same tax-line convention used
            # everywhere else in this module.
            gst_lines = m.line_ids.filtered(
                lambda l: l.tax_line_id and 'gst' in (l.tax_line_id.name or '').lower()
            )
            entry_gst += abs(sum(gst_lines.mapped('balance')))
        paid += entry_paid
        paid_gst += entry_gst

        tds = self.tds_deducted_actual + pending_tds
        cap = self._get_payment_cap() - pending_tds
        return {
            'paid': paid, 'paid_taxable': paid_taxable, 'paid_gst': paid_gst,
            'tds': tds, 'cap': cap,
            'total_excess': max(paid - cap, 0.0),
            'taxable_excess': max(paid_taxable + tds - self.taxable_value, 0.0),
            'gst_excess': 0.0 if self.is_reverse_charge else max(paid_gst - self.gst, 0.0),
            'tds_excess': max(tds - self.tds_frozen_amount, 0.0) if self.tds_frozen else 0.0,
        }

    vendor_balance_payable = fields.Float(
        string='Balance Payable to Vendor',
        compute='_compute_vendor_balance', store=True,
        help="Still payable to the vendor: Remaining Taxable (to Pay) plus "
             "Remaining GST (to Pay), each counted only if positive.",
    )
    excess_paid = fields.Float(
        string='Excess Paid to Vendor',
        compute='_compute_vendor_balance', store=True,
        help="Paid beyond what was approved, in any bucket: taxable paid + "
             "TDS over approved taxable, GST paid over approved GST, or total "
             "cash over approved amount minus TDS. Should always be 0.",
    )

    @api.depends('taxable_value', 'gst', 'is_reverse_charge',
                 'tds_deducted_actual', 'total_paid_amount',
                 'remaining_taxable_to_pay', 'remaining_gst_to_pay')
    def _compute_vendor_balance(self):
        for rec in self:
            rem_t = rec.remaining_taxable_to_pay
            rem_g = rec.remaining_gst_to_pay
            rec.vendor_balance_payable = round(max(rem_t, 0.0) + max(rem_g, 0.0), 2)
            total_excess = max(rec.total_paid_amount - rec._get_payment_cap(), 0.0)
            bucket_excess = max(-rem_t, 0.0) + max(-rem_g, 0.0)
            excess = round(max(total_excess, bucket_excess), 2)
            rec.excess_paid = excess if excess > 0.01 else 0.0

    # ── Payment-side balances (Approved Bills list) ──────────────────────────
    # Bucket rule: TDS belongs to the TAXABLE bucket only and counts as paid.
    #   Taxable settled  = cash taxable paid + TDS deducted
    #   Remaining taxable = approved taxable - taxable settled
    #   Remaining GST     = approved GST - GST paid (0 under RCM, because
    #                       RCM GST is never paid to the vendor)
    # The existing remaining_taxable_value / remaining_gst_value fields keep
    # their meaning (what is still left to BILL); these are what is left to PAY.
    taxable_settled = fields.Float(
        string='Taxable Settled (Paid + TDS)',
        compute='_compute_settlement_balances', store=True,
        help="Taxable Paid (cash) + TDS Deducted. TDS is settled to the "
             "Government on the vendor's behalf, so it is part of the "
             "taxable amount that has been paid.",
    )
    remaining_taxable_to_pay = fields.Float(
        string='Remaining Taxable (to Pay)',
        compute='_compute_settlement_balances', store=True,
        help="Approved Taxable Value - (Taxable Paid + TDS Deducted).",
    )
    remaining_gst_to_pay = fields.Float(
        string='Remaining GST (to Pay)',
        compute='_compute_settlement_balances', store=True,
        help="Approved GST - GST Paid. Always 0 for reverse-charge (RCM) "
             "approvals, where GST is not paid to the vendor.",
    )

    @api.depends('taxable_value', 'gst', 'is_reverse_charge',
                 'total_taxable_paid', 'total_gst_paid', 'tds_deducted_actual')
    def _compute_settlement_balances(self):
        for rec in self:
            settled = rec.total_taxable_paid + rec.tds_deducted_actual
            rec.taxable_settled = settled
            rec.remaining_taxable_to_pay = rec.taxable_value - settled
            rec.remaining_gst_to_pay = 0.0 if rec.is_reverse_charge else rec.gst - rec.total_gst_paid

    total_gst_paid = fields.Float(
        string='GST Paid', tracking=True,
        compute='_compute_gst_taxable_paid', store=True,
        help="Sum of GST Paid across all POSTED payments linked to this "
             "approval (see account.payment.gst_paid_amount). This is "
             "the reportable 'GST actually paid' figure -- unlike "
             "Remaining GST above, which tracks billing, not payment."
    )
    total_paid_amount = fields.Float(
        string='Total Paid to Vendor', tracking=True,
        compute='_compute_gst_taxable_paid', store=True,
        help="Sum of the Amount of all POSTED payments on this approval "
             "(cash actually paid to the vendor; TDS is not included).",
    )
    total_taxable_paid = fields.Float(
        string='Taxable Paid', tracking=True,
        compute='_compute_gst_taxable_paid', store=True,
        help="Sum of Taxable Paid across all POSTED payments linked to "
             "this approval (see account.payment.taxable_paid_amount)."
    )

    @api.depends('payment_ids.gst_paid_amount', 'payment_ids.taxable_paid_amount',
                 'payment_ids.amount', 'payment_ids.state')
    def _compute_gst_taxable_paid(self):
        for rec in self:
            # Deliberately using search() with a domain here, rather than
            # rec.payment_ids.filtered(lambda p: p.state == 'posted').
            # filtered() accesses .state via Python attribute reads across
            # the whole recordset, which forces Odoo to compute/validate
            # that field for every record -- and this database has at
            # least one pre-existing account.payment record with a stale
            # stored state value ('to approve') that the current state
            # field's selection no longer recognizes, causing a crash
            # unrelated to anything here. search() filters at the SQL
            # level against the raw stored column instead, sidestepping
            # that validation entirely.
            posted = self.env['account.payment'].sudo().search([
                ('id', 'in', rec.sudo().payment_ids.ids),
                ('state', '=', 'posted'),
            ])
            rec.total_gst_paid = sum(posted.mapped('gst_paid_amount'))
            rec.total_taxable_paid = sum(posted.mapped('taxable_paid_amount'))
            rec.total_paid_amount = sum(posted.mapped('amount'))

    latest_bill_due_amount = fields.Float(
        string='Latest Bill Due Amount', tracking=True,
        compute='_compute_latest_bill_due_amount', store=True,
        help="Actual amount still outstanding on the most recently created "
             "posted bill under this approval (its real amount_residual -- "
             "already net of any TDS applied as a tax line, and net of "
             "any payments already reconciled against it). 0 if no bill "
             "has been posted yet. Used to default the payment amount "
             "instead of the original approval-level Total Payable, since "
             "what was actually billed can differ from what was approved."
    )

    @api.depends('account_move_ids', 'account_move_ids.amount_residual',
                 'account_move_ids.state', 'account_move_ids.move_type',
                 'account_move_ids.create_date')
    def _compute_latest_bill_due_amount(self):
        for rec in self:
            bills = rec.sudo().account_move_ids.filtered(
                lambda m: m.move_type != 'entry' and m.state == 'posted'
            )
            if bills:
                latest = bills.sorted(
                    key=lambda m: (m.create_date, m.id), reverse=True
                )[0]
                rec.latest_bill_due_amount = latest.amount_residual
            else:
                rec.latest_bill_due_amount = 0.0

    def _force_recompute_balances(self, warn=True):
        """Refresh every stored TDS / paid / remaining / excess figure. Used
        when something they depend on changes without triggering the ORM
        (e.g. a TDS smart-button entry posted on a bill or payment).
        If this reveals a NEW excess payment to the vendor, warn in chatter."""
        before = {rec.id: rec.excess_paid for rec in self}
        for rec in self:
            rec._mark_balances_for_recompute()
        if warn:
            for rec in self:
                if rec.excess_paid - before.get(rec.id, 0.0) > 0.01:
                    rec.message_post(body=Markup(_(
                        '⚠️ <b>Excess paid to vendor:</b> %(excess)s. Paid amounts '
                        'plus TDS now go beyond what was approved. Recover or '
                        'adjust the excess.',
                        excess='{:,.2f}'.format(rec.excess_paid),
                    )))

    @api.constrains('gst')
    def _check_gst_amount(self):
        for record in self:
            if record.gst < 0:
                raise ValidationError(_("GST cannot be negative."))

    @api.constrains('taxable_value', 'gst')
    def _check_amounts_not_below_booked(self):
        """Approved Taxable / GST can never be set below what bills have
        already booked against this approval (cancelled bills ignored)."""
        for rec in self:
            moves = rec.account_move_ids.filtered(
                lambda m: m.move_type != 'entry' and m.state != 'cancel'
            )
            if not moves:
                continue
            booked_taxable, booked_gst = moves._get_taxable_gst_amounts()
            if float_compare(booked_taxable, rec.taxable_value, precision_rounding=0.01) > 0:
                raise ValidationError(_(
                    "Approved Taxable (%s) cannot be lower than the taxable "
                    "already booked in bills (%s)."
                ) % (rec.taxable_value, booked_taxable))
            if float_compare(booked_gst, rec.gst, precision_rounding=0.01) > 0:
                raise ValidationError(_(
                    "Approved GST (%s) cannot be lower than the GST already "
                    "booked in bills (%s)."
                ) % (rec.gst, booked_gst))

    def write(self, vals):
        # The approved Taxable / GST are the ceiling every bill is checked
        # against, so once fully approved they are frozen. To change them:
        # Reset to Draft, edit, and take it through approval again.
        if 'taxable_value' in vals or 'gst' in vals:
            for rec in self.filtered(lambda r: r.approver_status in ('approved', 'done')):
                t_changed = 'taxable_value' in vals and float_compare(
                    vals['taxable_value'], rec.taxable_value, precision_rounding=0.01) != 0
                g_changed = 'gst' in vals and float_compare(
                    vals['gst'], rec.gst, precision_rounding=0.01) != 0
                if t_changed or g_changed:
                    raise UserError(_(
                        "Approved Taxable / GST amounts are locked after "
                        "final approval (%s). Reset to Draft and re-approve "
                        "to change them."
                    ) % rec.name)
        return super().write(vals)

    @api.constrains('taxable_value')
    def _check_taxable_value(self):
        for record in self:
            if record.taxable_value <= 0.0:
                raise ValidationError(_("The Amount field must be greater than zero."))

    @api.depends('taxable_value', 'gst')
    def _compute_total_value(self):
        for rec in self:
            rec.total_value = rec.taxable_value + rec.gst

    # ── Others ─────────────────────────────────────────────────────────────────
    description = fields.Text(string='Description')
    attachment_link = fields.Char(string='Attachment Link')
    reviewer_comment = fields.Text(string='Reviewer Comment')
    # payment_status = fields.Char(string='Payment Status', tracking=True)
    # payment_date = fields.Date(string='Payment Date')

    # ═══════════════════════════════════════════════════════════════════════════
    # 3-LEVEL STATIC GROUP APPROVAL
    # L1 → group_bill_approver_l1
    # L2 → group_bill_approver_l2
    # L3 → group_bill_approver_l3
    # ═══════════════════════════════════════════════════════════════════════════

    approver_status = fields.Selection([
        ('draft',      'Draft'),
        ('waiting_l1', 'Waiting L1'),
        ('waiting_l2', 'Waiting L2'),
        ('waiting_l3', 'Waiting L3'),
        ('approved',   'Approved'),
        ('rejected',   'Rejected'),
    ], default='draft', string='Status', tracking=True, copy=False)

    # L1
    l1_status = fields.Selection([
        ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], default='pending', string='L1 Status', tracking=True, copy=False)
    l1_user_id  = fields.Many2one('res.users', string='L1 By', readonly=True, copy=False)
    l1_date     = fields.Datetime(string='L1 Date', readonly=True, copy=False)
    l1_comment  = fields.Text(string='L1 Comment', copy=False)

    # L2
    l2_status = fields.Selection([
        ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], default='pending', string='L2 Status', tracking=True, copy=False)
    l2_user_id  = fields.Many2one('res.users', string='L2 By', readonly=True, copy=False)
    l2_date     = fields.Datetime(string='L2 Date', readonly=True, copy=False)
    l2_comment  = fields.Text(string='L2 Comment', copy=False)

    # L3
    l3_status = fields.Selection([
        ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], default='pending', string='L3 Status', tracking=True, copy=False)
    l3_user_id  = fields.Many2one('res.users', string='L3 By', readonly=True, copy=False)
    l3_date     = fields.Datetime(string='L3 Date', readonly=True, copy=False)
    l3_comment  = fields.Text(string='L3 Comment', copy=False)

    # ── Linked accounting records ───────────────────────────────────────────────
    step_log_ids = fields.One2many(
        'bill.approval.step.log', 'bill_id', string='History',
    )
    account_move_ids = fields.One2many(
        'account.move', 'approval_id',
        string='Bills / Journal Entries',domain=[('journal_id.type','not in',['bank','cash'])]
    )
    payment_ids = fields.One2many(
        'account.payment','approval_id',
        string='Payments',
    )
    move_count    = fields.Integer(compute='_compute_counts')
    payment_count = fields.Integer(compute='_compute_counts')
    attachment_count = fields.Integer(compute='_compute_attachment_count')

    @api.depends('account_move_ids', 'payment_ids')
    def _compute_counts(self):
        for rec in self:
            rec.move_count    = len(rec.account_move_ids)
            rec.payment_count = len(rec.payment_ids)

    def _compute_attachment_count(self):
        # Not stored/depends-based on purpose: attachments are plain
        # ir.attachment records linked by res_model/res_id, not a
        # relational field on this model, so there's nothing for
        # @api.depends to track -- this just counts on read, same
        # pattern Odoo's own chatter attachment counter uses.
        for rec in self:
            rec.attachment_count = self.env['ir.attachment'].search_count([
                ('res_model', '=', 'bill.approval'),
                ('res_id', '=', rec.id),
            ])

    def action_view_attachments(self):
        self.ensure_one()
        kanban_view = self.env.ref(
            'bill_approval_flow_2.bill_approval_attachment_preview_kanban', raise_if_not_found=False
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Attachments'),
            'res_model': 'ir.attachment',
            'view_mode': 'kanban',
            'views': [(kanban_view.id if kanban_view else False, 'kanban')],
            'target': 'new',
            'domain': [('res_model', '=', 'bill.approval'), ('res_id', '=', self.id)],
            'context': {'default_res_model': 'bill.approval', 'default_res_id': self.id},
        }

    # ── Button visibility (computed per user/group) ─────────────────────────────
    can_approve_l1    = fields.Boolean(compute='_compute_visibility')
    can_approve_l2    = fields.Boolean(compute='_compute_visibility')
    can_approve_l3    = fields.Boolean(compute='_compute_visibility')
    can_reject        = fields.Boolean(compute='_compute_visibility')
    can_create_bill   = fields.Boolean(compute='_compute_visibility')
    can_create_payment = fields.Boolean(compute='_compute_visibility')
    move_status = fields.Char(
        compute="_compute_latest_status",
        store=True,
        string="Bill Status"
    )

    payment_status_display = fields.Char(
        compute="_compute_latest_status",
        store=True,
        string="Payment Status"
    )

    payment_status_refresh = fields.Char(
        compute="_compute_latest_status",
        store=False,
        string="Refresh Trigger"
    )

    is_history_dup = fields.Boolean(
        compute='_compute_is_history',
        store=False
    )

    is_history = fields.Boolean(
        store=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    def move_to_history(self):
        for rec in self:
            rec.is_history = True

    @api.depends(
        'account_move_ids',
        'payment_ids'
    )
    @api.onchange('account_move_ids',
        'payment_ids')
    def _compute_latest_status(self):
        Move = self.env['account.move'].sudo()
        Payment = self.env['account.payment'].sudo()

        for rec in self:
            move = Move.search(
                [('approval_id', '=', rec.id),('journal_id.type','not in',['bank','cash'])],
                order='create_date desc, id desc',
                limit=1
            )

            payment = Payment.search(
                [('approval_id', '=', rec.id)],
                order='create_date desc, id desc',
                limit=1
            )
            move_state = move.state if move else False
            pay_state = payment.state if payment else False
            rec.move_status = move_state
            rec.payment_status_display = pay_state

            # Dummy value just to force execution
            rec.payment_status_refresh = str(fields.Datetime.now())

    @api.depends('move_status', 'payment_status_display')
    def _compute_is_history(self):
        for rec in self:
            value = (
                    rec.move_status == 'posted'
                    and (
                            not rec.payment_status_display
                            or rec.payment_status_display in ('paid', 'reconciled')
                    )
            )
            rec.is_history_dup = value

    @api.depends('approver_status')
    def _compute_visibility(self):
        uid = self.env.user

        def in_group(xml):
            try:
                return uid in self.env.ref(xml).users
            except Exception:
                return False

        l1 = in_group('bill_approval_flow_2.group_bill_approver_l1')
        l2 = in_group('bill_approval_flow_2.group_bill_approver_l2')
        l3 = in_group('bill_approval_flow_2.group_bill_approver_l3')

        for rec in self:
            s = rec.approver_status
            rec.can_approve_l1     = s == 'waiting_l1' and l1
            rec.can_approve_l2     = s == 'waiting_l2' and l2
            rec.can_approve_l3     = s == 'waiting_l3' and l3
            rec.can_reject         = s in ('waiting_l1', 'waiting_l2', 'waiting_l3') \
                                     and (l1 or l2 or l3)
            rec.can_create_bill    = s in ('approved', 'done')
            rec.can_create_payment = s in ('approved', 'done')

    # ── Sequence ─────────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('bill.approval') or 'BA-0001'
                )
        return super().create(vals_list)



    # ─────────────────────────────────────────────────────────────────────────────
    # Activity Helpers
    # ─────────────────────────────────────────────────────────────────────────────

    def _create_approval_activity(self, group_xmlid, note):
        self.ensure_one()

        activity_type = self.env.ref(
            'bill_approval_flow_2.mail_activity_type_bill_approval'
        )

        group = self.env.ref(group_xmlid)

        for user in group.users:

            existing = self.activity_ids.filtered(
                lambda a:
                a.user_id.id == user.id and
                a.activity_type_id.id == activity_type.id
            )

            if not existing:
                self.activity_schedule(
                    activity_type_id=activity_type.id,
                    user_id=user.id,
                    note=note,
                )

    def _mark_current_activity_done(self, feedback=None):
        self.ensure_one()

        activity_type = self.env.ref(
            'bill_approval_flow_2.mail_activity_type_bill_approval'
        )

        activities = self.activity_ids.filtered(
            lambda a:
            a.user_id.id == self.env.user.id and
            a.activity_type_id.id == activity_type.id
        )

        activities.action_feedback(
            feedback=feedback or 'Done'
        )

    def action_submit(self):
        self.ensure_one()

        if self.approver_status != 'draft':
            raise UserError(_('Only Draft records can be submitted.'))

        self.write({
            'approver_status': 'waiting_l1',
            'l1_status': 'pending',
            'l2_status': 'pending',
            'l3_status': 'pending',
        })

        # Create L1 Activity
        self._create_approval_activity(
            'bill_approval_flow_2.group_bill_approver_l1',
            'Level 1 approval required.'
        )

        self.message_post(
            body=Markup(
                _('🚀 <b>Submitted for Approval</b> — Awaiting <b>Level 1</b>.')
            )
        )

        self._notify_group(
            'bill_approval_flow_2.group_bill_approver_l1',
            'Level 1'
        )

    # ── L1 ───────────────────────────────────────────────────────────────────────

    def action_approve_l1(self):
        self.ensure_one()

        self._check_group(
            'bill_approval_flow_2.group_bill_approver_l1',
            'Level 1'
        )

        return self._open_wizard(
            'approve_l1',
            'Level 1 Approval — Add Comment'
        )

    # -- TDS freeze (Level 1 only, locked once Level 1 approves) ---------------
    tds_rate_percent = fields.Float(
        string='TDS Rate (%)', tracking=True,
        help="TDS rate to withhold from this vendor. Set by the Level 1 "
             "(finance) approver only, while this approval is Waiting L1. "
             "Locked the moment Level 1 approves -- no bill or payment may "
             "then deduct TDS beyond the amount this rate produces, the same "
             "way GST is locked to the approved GST amount.")

    tds_not_applicable = fields.Boolean(
        string='No TDS Applicable', tracking=True,
        help="Tick this to confirm, on purpose, that no TDS applies to this "
             "vendor/transaction. Required to approve Level 1 with a 0%% "
             "rate -- otherwise a 0%% rate that was simply never set would "
             "be indistinguishable from a deliberate zero, and could freeze "
             "a ceiling nobody actually decided on.")
    tds_frozen_amount = fields.Float(
        string='TDS Frozen Amount', tracking=True,
        compute='_compute_tds_frozen_amount', store=True,
        help="Taxable Value x TDS Rate (%), fixed the moment Level 1 "
             "approves. No bill or payment may deduct TDS beyond this once "
             "frozen.")
    tds_frozen = fields.Boolean(
        string='TDS Frozen', default=False, tracking=True,
        help="True once Level 1 has approved: TDS Rate (%) and TDS Frozen "
             "Amount are then locked, and no bill or payment may deduct TDS "
             "beyond TDS Frozen Amount.")
    is_l1_approver = fields.Boolean(
        string='Is L1 Approver', compute='_compute_is_l1_approver',
        help="Technical field driving TDS Rate (%)'s editability in the "
             "form view: true only for the current user if they are in the "
             "Level 1 approver group.")

    @api.depends('taxable_value', 'tds_rate_percent', 'tds_frozen')
    def _compute_tds_frozen_amount(self):
        for rec in self:
            if rec.tds_frozen:
                if self.env.context.get('tds_revision_approved'):
                    # A TDS Rate Revision has just been approved and
                    # legitimately changed tds_rate_percent -- recompute the
                    # frozen ceiling from the new rate instead of preserving
                    # the old one, so the enforced ceiling actually tracks
                    # the revision.
                    rec.tds_frozen_amount = rec.taxable_value * rec.tds_rate_percent / 100.0
                else:
                    # Already fixed at Level 1 approval -- re-assign the record's
                    # own stored value so this can never silently drift even if
                    # taxable_value or tds_rate_percent changed afterwards (the
                    # latter is blocked outright by _check_tds_rate_locked below).
                    rec.tds_frozen_amount = rec.tds_frozen_amount
            else:
                rec.tds_frozen_amount = rec.taxable_value * rec.tds_rate_percent / 100.0

    def _compute_is_l1_approver(self):
        is_l1 = self.env.user.has_group('bill_approval_flow_2.group_bill_approver_l1')
        for rec in self:
            rec.is_l1_approver = is_l1

    @api.constrains('tds_deducted_actual')
    def _check_tds_frozen_ceiling(self):
        # Backstop for every mechanism that can move tds_deducted_actual --
        # bill tax line, bill smart button, payment smart button, payment
        # Other Charges -- regardless of which code path wrote it, since
        # this fires whenever the stored field itself changes, not when a
        # particular posting method runs.
        for rec in self:
            # Plain rounding comparison rather than float_compare, so this
            # doesn't depend on that helper being imported in this file.
            if rec.tds_frozen and round(rec.tds_deducted_actual - rec.tds_frozen_amount, 2) > 0:
                raise UserError(_(
                    "TDS limit exceeded!\n"
                    "Approval: %(ref)s\n"
                    "TDS frozen at Level 1 approval: %(frozen)s\n"
                    "TDS now recorded (bills + payments, any source): %(tds)s\n\n"
                    "No bill or payment may deduct TDS beyond what Level 1 approved.",
                    ref=rec.name,
                    frozen='{:,.2f}'.format(rec.tds_frozen_amount),
                    tds='{:,.2f}'.format(rec.tds_deducted_actual),
                ))

    @api.constrains('tds_rate_percent')
    def _check_tds_rate_locked(self):
        # Only fires when tds_rate_percent is itself part of this write/create
        # -- the write that sets tds_frozen=True at Level 1 approval does not
        # touch tds_rate_percent, so this never blocks that legitimate freeze.
        # TDS-REVISION-BYPASS: an approved bill.approval.tds.revision writes
        # through with this context flag set -- its own change to the rate
        # is already maker-checker-enforced in action_approve() itself, so
        # it is not blocked by the same freeze that stops everyone else from
        # hand-editing it.
        if self.env.context.get('tds_revision_approved'):
            return
        for rec in self:
            if rec.tds_frozen:
                raise UserError(_(
                    "TDS Rate (%%) is frozen for %(ref)s -- Level 1 has "
                    "already approved it, and it cannot be changed anymore, "
                    "the same way the GST amount is locked once approved.",
                    ref=rec.name,
                ))

    def _do_approve_l1(self, comment):
        if self.tds_rate_percent < 0:
            raise UserError(_(
                "TDS Rate (%%) cannot be negative."
            ))
        if self.tds_rate_percent == 0 and not self.tds_not_applicable:
            raise UserError(_(
                "Set a TDS Rate (%%), or tick 'No TDS Applicable' if none "
                "applies, before approving Level 1 -- it locks immediately "
                "on approval and cannot be changed afterwards."
            ))

        self._mark_current_activity_done('L1 Approved')

        self.write({
            'l1_status': 'approved',
            'l1_user_id': self.env.uid,
            'l1_date': fields.Datetime.now(),
            'l1_comment': comment,
            'approver_status': 'waiting_l2',
            'tds_frozen': True,
        })

        # Create L2 Activity
        self._create_approval_activity(
            'bill_approval_flow_2.group_bill_approver_l2',
            'Level 2 approval required.'
        )

        self._log('Level 1 Approval', 'approved', comment)

        body = _(
            '✅ <b>L1 Approved</b> by <b>%s</b> — Awaiting <b>Level 2</b>.'
        ) % self.env.user.name

        if comment:
            body += '<br/><i>%s</i>' % comment

        self.message_post(body=Markup(body))

        self._notify_group(
            'bill_approval_flow_2.group_bill_approver_l2',
            'Level 2'
        )

    # ── L2 ───────────────────────────────────────────────────────────────────────

    def action_approve_l2(self):
        self.ensure_one()

        self._check_group(
            'bill_approval_flow_2.group_bill_approver_l2',
            'Level 2'
        )

        return self._open_wizard(
            'approve_l2',
            'Level 2 Approval — Add Comment'
        )

    def _do_approve_l2(self, comment):

        self._mark_current_activity_done('L2 Approved')

        self.write({
            'l2_status': 'approved',
            'l2_user_id': self.env.uid,
            'l2_date': fields.Datetime.now(),
            'l2_comment': comment,
            'approver_status': 'waiting_l3',
        })

        # Create L3 Activity
        self._create_approval_activity(
            'bill_approval_flow_2.group_bill_approver_l3',
            'Final approval required.'
        )

        self._log('Level 2 Approval', 'approved', comment)

        body = _(
            '✅ <b>L2 Approved</b> by <b>%s</b> — Awaiting <b>Level 3</b>.'
        ) % self.env.user.name

        if comment:
            body += '<br/><i>%s</i>' % comment

        self.message_post(body=Markup(body))

        self._notify_group(
            'bill_approval_flow_2.group_bill_approver_l3',
            'Level 3'
        )

    # ── L3 (Final) ───────────────────────────────────────────────────────────────

    def action_approve_l3(self):
        self.ensure_one()

        self._check_group(
            'bill_approval_flow_2.group_bill_approver_l3',
            'Level 3'
        )

        return self._open_wizard(
            'approve_l3',
            'Level 3 — Final Approval'
        )

    def _do_approve_l3(self, comment):

        self._mark_current_activity_done('Final Approved')

        self.write({
            'l3_status': 'approved',
            'l3_user_id': self.env.uid,
            'l3_date': fields.Datetime.now(),
            'l3_comment': comment,
            'approver_status': 'approved',
        })

        self._log('Level 3 Approval', 'approved', comment)

        body = _(
            '✅ <b>L3 Approved</b> by <b>%s</b><br/>'
            '🎉 <b>Fully Approved!</b> Bill and Payment can now be created.'
        ) % self.env.user.name

        if comment:
            body += '<br/><i>%s</i>' % comment

        self.message_post(body=Markup(body))

    # ── Reject ───────────────────────────────────────────────────────────────────

    def action_reject(self):
        self.ensure_one()

        return self._open_wizard(
            'reject',
            'Reject — Provide Reason'
        )

    def _do_reject(self, reason):

        self._mark_current_activity_done('Rejected')

        level_label = {
            'waiting_l1': 'Level 1',
            'waiting_l2': 'Level 2',
            'waiting_l3': 'Level 3',
        }.get(self.approver_status, '')

        self.write({
            'approver_status': 'rejected',
            'reviewer_comment': reason,
        })

        self._log(
            f'{level_label} Rejection',
            'rejected',
            reason
        )

        body = _(
            '❌ <b>Rejected</b> at <b>%s</b> by <b>%s</b>'
        ) % (
                   level_label,
                   self.env.user.name
               )

        if reason:
            body += '<br/><b>Reason:</b> %s' % reason

        self.message_post(body=Markup(body))

    def action_view_bills(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Bills & Journals',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'views': [(self.env.ref('bill_approval_flow_2.view_bill_approval_bills_journals_list').id, 'list'),
                      (False, 'form')],  # TDS-COLUMN
            'domain': [('approval_id', '=', self.id)],
            'context': {
                'default_approval_id': self.id,
                'default_move_type': 'in_invoice',
            },
        }
    def action_view_payment(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Payments',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('approval_id', '=', self.id)],
            'context': {
                'default_approval_id': self.id,
            },
        }

    def action_open_bill(self):
        self.ensure_one()
        # Only the taxable bucket decides whether there is anything left to
        # bill. GST is NOT tested here: an approval with zero GST (or GST
        # already fully used) must still allow a bill for the remaining
        # taxable, and the hard GST ceiling is enforced on the bill itself
        # (account.move._check_bill_limit).
        if float_compare(self.remaining_taxable_value, 0.0, precision_rounding=0.01) <= 0:
            raise UserError(_(
                'This approval is already fully billed (Taxable Value '
                'already fully consumed). No further bill '
                'entries can be created against it.'
            ))
        # self.hide_bill_creation = True
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bills',
            'res_model': 'account.move',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_type': 'in_invoice',
                'default_approval_id': self.id,
                'default_ref':self.invoice_no,
                'default_partner_id': self.supplier_name.id,
                'default_narration': self.description,
            'default_invoice_date': self.invoice_date}
        }

    def action_open_invoice(self):
        self.ensure_one()
        # self.hide_bill_creation = True
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'res_model': 'account.move',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_type': 'out_invoice',
                'default_approval_id': self.id,
                'default_partner_id': self.supplier_name.id,
            'default_narration': self.description,
            'default_invoice_date': self.invoice_date}
        }

    def action_open_credit_notes(self):
        self.ensure_one()
        # self.hide_bill_creation = True
        return {
            'type': 'ir.actions.act_window',
            'name': 'Credit Notes',
            'res_model': 'account.move',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_type': 'out_refund',
                'default_approval_id': self.id,
                'default_partner_id': self.supplier_name.id,
            'default_narration': self.description}
        }

    def action_open_debit_notes(self):
        self.ensure_one()
        # self.hide_bill_creation = True
        return {
            'type': 'ir.actions.act_window',
            'name': 'Debit Notes',
            'res_model': 'account.move',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_type': 'in_refund',
                'default_approval_id': self.id,
                'default_partner_id': self.supplier_name.id,
            'default_narration': self.description}
        }

    def action_open_journal(self):
        self.ensure_one()
        # self.hide_bill_creation = True
        return {
            'type': 'ir.actions.act_window',
            'name': 'Journals',
            'res_model': 'account.move',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_type': 'entry',
                'default_approval_id': self.id,  # ✅ only this
                'default_narration': self.description
            }
        }
    def action_open_credit_expense(self):
        self.ensure_one()
        # self.hide_bill_creation = True
        return {
            'type': 'ir.actions.act_window',
            'name': 'Credit Card Expense',
            'res_model': 'account.move',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_move_type':'entry','default_is_payment_approval':True,'default_approval_id': self.id,'default_narration': self.description}
        }
    def action_open_credit_card_payment(self):
        self.ensure_one()
        # self.hide_bill_creation = True
        return {
            'type': 'ir.actions.act_window',
            'name': 'Credit Card Payment',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_is_credit_payment': True,'is_internal_transfer': True,'default_payment_type':'outbound','default_approval_id': self.id,}
        }
    def action_open_payment(self):
        self.ensure_one()
        # self.hide_bill_creation = True
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payments',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'target': 'new',
            'context':
            {'default_payment_type': 'outbound', 'default_partner_type': 'supplier','default_partner_id':self.supplier_name.id, 'default_amount': 0.0,
             'search_default_outbound_filter': 1, 'default_move_journal_types': ('bank', 'cash'),
             'display_account_trust': True, 'default_is_manual_payment': True,'default_approval_id': self.id,}
        }
    def action_open_receipt(self):
        self.ensure_one()
        # self.hide_bill_creation = True
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payments',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'target': 'new',
            'context':
            { 'default_payment_type': 'inbound',  'default_partner_type': 'customer','default_partner_id':self.supplier_name.id, 'default_amount': self.total_value,
              'search_default_inbound_filter': 1,
              'default_move_journal_types': ('bank', 'cash'),
              'display_account_trust': True,       'default_approval_id': self.id,     }
        }



    # ── Create Bill ─────────────────────────────────────────────────────────────
    def action_create_bill(self):
        self.ensure_one()
        if self.approver_status not in ('approved', 'done'):
            raise UserError(_('Bill can only be created after full approval.'))
        # Only the taxable bucket decides whether there is anything left to
        # bill. GST is NOT tested here: an approval with zero GST (or GST
        # already fully used) must still allow a bill for the remaining
        # taxable, and the hard GST ceiling is enforced on the bill itself
        # (account.move._check_bill_limit).
        if float_compare(self.remaining_taxable_value, 0.0, precision_rounding=0.01) <= 0:
            raise UserError(_(
                'This approval is already fully billed (Taxable Value '
                'already fully consumed). No further bill '
                'entries can be created against it.'
            ))
        return self._open_wizard('bill', 'Create Bill / Journal Entry')

    def _do_create_bill(self, journal_type, partner_id, account_id, note):
        self.ensure_one()
        journal = self.env['account.journal'].search(
            [('type', '=', journal_type),
             ('company_id', '=', self.env.company.id)],
            limit=1,
        )
        if not journal:
            raise UserError(_('No %s journal found.', journal_type))

        move_type = {
            'purchase': 'in_invoice',
            'sale':     'out_invoice',
            'general':  'entry',
        }.get(journal_type, 'in_invoice')

        move_vals = {
            'move_type':    move_type,
            'journal_id':   journal.id,
            'invoice_date': self.invoice_date or fields.Date.today(),
            'ref':          self.invoice_no or self.name,
            'narration':    note or self.description,
            'partner_id':   partner_id or self.supplier_name.id,
        }
        aid = account_id or (self.expense_head.id if self.expense_head else False)
        if move_type != 'entry' and aid:
            move_vals['invoice_line_ids'] = [(0, 0, {
                'name':        self.description or self.expense_head.name or 'Bill Line',
                'quantity':    1,
                'price_unit':  self.remaining_taxable_value,
                'account_id':  aid,
                'tax_ids':     [],
            })]

        move = self.env['account.move'].create(move_vals)
        self.account_move_ids = [(4, move.id)]
        self._log('Bill Created', 'bill_created', note, move_id=move.id)
        self.message_post(body=_(
            '🧾 <b>Bill Created:</b> <a href="/web#model=account.move&id=%s">%s</a>'
            ' by <b>%s</b>',
            move.id, move.name, self.env.user.name,
        ))
        return move

    # ── Register Payment ────────────────────────────────────────────────────────
    def action_create_payment(self):
        self.ensure_one()
        if self.approver_status not in ('approved', 'done'):
            raise UserError(_('Payment can only be registered after full approval.'))
        return self._open_wizard('payment', 'Register Payment')

    def _do_create_payment(self, journal_id, amount, note):
        self.ensure_one()
        journal = (
            self.env['account.journal'].browse(journal_id)
            if journal_id
            else self.env['account.journal'].search(
                [('type', 'in', ['bank', 'cash']),
                 ('company_id', '=', self.env.company.id)],
                limit=1,
            )
        )
        if not journal:
            raise UserError(_('No payment journal found.'))

        payment = self.env['account.payment'].create({
            'payment_type':  'outbound',
            'partner_type':  'supplier',
            'partner_id':    self.supplier_name.id,
            'journal_id':    journal.id,
            'amount':        amount or self.total_payable,
            # 'date':          payment_date or fields.Date.today(),
            'ref':           self.invoice_no or self.name,
            'memo':          note or self.description,
        })
        self.write({
            'payment_ids':    [(4, payment.id)],
            # 'payment_date':   payment_date or fields.Date.today(),
            # 'payment_status': 'Payment Created',
            'approver_status': 'done',
        })
        self._log('Payment Registered', 'payment_created', note, pay_id=payment.id)
        self.message_post(body=_(
            '💳 <b>Payment Registered:</b> %s %s via <b>%s</b> by <b>%s</b>',
            self.env.company.currency_id.symbol,
            amount, journal.name, self.env.user.name,
        ))
        return payment

    # ── Reset ───────────────────────────────────────────────────────────────────
    def action_reset_to_draft(self):
        self.write({
            'approver_status': 'draft',
            'l1_status': 'pending', 'l1_user_id': False,
            'l1_date': False,       'l1_comment': False,
            'l2_status': 'pending', 'l2_user_id': False,
            'l2_date': False,       'l2_comment': False,
            'l3_status': 'pending', 'l3_user_id': False,
            'l3_date': False,       'l3_comment': False,
        })
        self.message_post(body=_('🔄 Reset to Draft.'))

    # ── Smart button links ──────────────────────────────────────────────────────
    def action_view_moves(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bills / Journal Entries',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.account_move_ids.ids)],
        }

    def action_view_payments(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payments',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.payment_ids.ids)],
        }

    # ── Internal helpers ────────────────────────────────────────────────────────
    def _open_wizard(self, wizard_type, title):
        return {
            'type': 'ir.actions.act_window',
            'name': _(title),
            'res_model': 'bill.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_bill_id':    self.id,
                'default_wizard_type': wizard_type,
                'default_partner_id': self.supplier_name.id,
                'default_amount':     self.total_payable,
                'default_account_id': self.expense_head.id if self.expense_head else False,
            },
        }

    def _check_group(self, xmlid, label):
        try:
            grp = self.env.ref(xmlid)
        except Exception:
            raise UserError(_('Group %s not found.', xmlid))
        if self.env.user not in grp.users:
            raise UserError(_('Only %s users can perform this action.', label))

    def _notify_group(self, xmlid, label):
        try:
            grp = self.env.ref(xmlid)
            pids = grp.users.mapped('partner_id').ids
            if pids:
                self.message_post(
                    body=_('👤 <b>Action Required — %s:</b> Please review and approve.', label),
                    partner_ids=pids,
                )
        except Exception:
            pass

    def _log(self, step_name, action, note, move_id=None, pay_id=None):
        vals = {
            'bill_id':   self.id,
            'step_name': step_name,
            'action':    action,
            'user_id':   self.env.uid,
            'note':      note,
        }
        if move_id:
            vals['account_move_id'] = move_id
        if pay_id:
            vals['payment_id'] = pay_id
        self.env['bill.approval.step.log'].create(vals)

    tds_revision_reminder_sent = fields.Boolean(
        default=False,
        help="Internal flag -- true once the TDS Revision reminder has "
             "been sent for this approval, so it is sent only once "
             "rather than on every subsequent bill/payment."
    )

    def _check_tds_revision_reminder(self):
        """Proactively nudge whoever has TDS Revision access once this
        approval's cash paid crosses a configurable threshold of its
        approved payable amount (default 90%%). A revision made after the
        approval is fully settled can no longer have any effect, so this
        is the window to catch a wrong rate before it closes."""
        for rec in self:
            if rec.tds_revision_reminder_sent or not rec.total_payable:
                continue
            pos = rec._payment_position()
            consumption_pct = (pos['paid'] / rec.total_payable) * 100.0
            threshold = float(self.env['ir.config_parameter'].sudo().get_param(
                'bill_approval_flow_2.tds_revision_threshold_pct', '90'
            ))
            if consumption_pct >= threshold:
                fmt = lambda v: '{:,.2f}'.format(v)
                rec._notify_group(
                    'bill_approval_flow_2.group_tds_revision',
                    'TDS Revision Check',
                )
                rec.message_post(body=_(
                    "\u26a0\ufe0f Approval %(ref)s has reached %(pct)s%% of its approved "
                    "payable amount (%(paid)s of %(total)s paid so far). If the "
                    "TDS rate needs correction, raise a TDS Revision now -- once "
                    "the approval is fully settled, a revision can no longer "
                    "have any effect.",
                    ref=rec.name, pct='{:.0f}'.format(consumption_pct),
                    paid=fmt(pos['paid']), total=fmt(rec.total_payable),
                ))
                rec.sudo().write({'tds_revision_reminder_sent': True})


class approvalDocument(models.Model):
    _name = 'bill.approval.document'

    name = fields.Char(required=True)


class BillApprovalTdsRevision(models.Model):
    _name = 'bill.approval.tds.revision'
    _description = 'TDS Rate Revision Request'
    _order = 'id desc'

    approval_id = fields.Many2one(
        'bill.approval', string='Bill Approval', required=True, ondelete='cascade')
    old_rate = fields.Float(string='Old TDS Rate (%)', readonly=True)
    new_rate = fields.Float(string='New TDS Rate (%)', required=True)
    old_tds_not_applicable = fields.Boolean(string='Old: No TDS Applicable', readonly=True)
    new_tds_not_applicable = fields.Boolean(string='New: No TDS Applicable')
    reason = fields.Text(string='Reason for Revision', required=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='pending', tracking=True, readonly=True)
    requested_by = fields.Many2one(
        'res.users', string='Requested By',
        default=lambda self: self.env.user, readonly=True)
    requested_date = fields.Datetime(
        string='Requested On', default=fields.Datetime.now, readonly=True)
    decided_by = fields.Many2one('res.users', string='Decided By', readonly=True)
    decided_date = fields.Datetime(string='Decided On', readonly=True)
    decision_comment = fields.Text(string='Decision Comment')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('approval_id') and 'old_rate' not in vals:
                approval = self.env['bill.approval'].browse(vals['approval_id'])
                vals['old_rate'] = approval.tds_rate_percent
                vals['old_tds_not_applicable'] = approval.tds_not_applicable
        return super().create(vals_list)

    def action_approve(self):
        for rec in self:
            rec.approval_id._check_group(
                'bill_approval_flow_2.group_tds_revision', 'TDS Revision')
            if rec.state != 'pending':
                raise UserError(_('Only a pending revision can be approved.'))
            if rec.requested_by == self.env.user:
                raise UserError(_(
                    'A TDS Revision cannot be approved by the same user who '
                    'requested it. A different TDS Revision user must approve it.'
                ))
            approval = rec.approval_id
            if rec.new_rate < 0:
                raise UserError(_('New TDS Rate (%%) cannot be negative.'))
            if rec.new_rate == 0 and not rec.new_tds_not_applicable:
                raise UserError(_(
                    "Set a positive New TDS Rate (%%), or tick 'New: No TDS "
                    "Applicable' if none applies."
                ))
            new_frozen_amount = 0.0 if rec.new_tds_not_applicable else (
                approval.taxable_value * rec.new_rate / 100.0
            )
            if new_frozen_amount < approval.tds_deducted_actual - 0.01:
                fmt = lambda v: '{:,.2f}'.format(v)
                raise UserError(_(
                    "Cannot approve: the new rate would set the TDS ceiling to "
                    "%(new)s, which is BELOW the %(actual)s already genuinely "
                    "deducted across posted bills/payments under this approval. "
                    "Choose a rate that covers what has already been deducted.",
                    new=fmt(new_frozen_amount), actual=fmt(approval.tds_deducted_actual),
                ))

            old_frozen_amount = approval.tds_frozen_amount
            if new_frozen_amount > old_frozen_amount + 0.01:
                # INCREASE: the only place extra TDS can still be genuinely
                # collected is on whatever taxable value is still unbilled.
                # If what's recoverable at the new rate falls short of the
                # full size of the increase, the shortfall can NEVER be
                # collected once the remaining value is billed -- that gap
                # is cash that already left (or will leave) the vendor
                # without the correct TDS ever withheld against it, which is
                # functionally an excess payment. Block it.
                max_recoverable = approval.remaining_taxable_value * rec.new_rate / 100.0
                required_increase = new_frozen_amount - old_frozen_amount
                if max_recoverable < required_increase - 0.01:
                    fmt = lambda v: '{:,.2f}'.format(v)
                    raise UserError(_(
                        "Cannot approve: this increases the TDS ceiling by "
                        "%(required)s (from %(old)s to %(new)s), but only "
                        "%(remaining)s of taxable value is still unbilled under "
                        "this approval -- at the new rate, at most %(max)s of "
                        "additional TDS can still genuinely be collected. The "
                        "remaining %(shortfall)s could never be withheld once "
                        "this approval is fully billed, which would leave the "
                        "vendor having effectively received that amount in "
                        "excess. A TDS rate increase can only be approved when "
                        "enough unbilled value remains to absorb it.",
                        required=fmt(required_increase), old=fmt(old_frozen_amount),
                        new=fmt(new_frozen_amount), remaining=fmt(approval.remaining_taxable_value),
                        max=fmt(max_recoverable),
                        shortfall=fmt(required_increase - max_recoverable),
                    ))
            approval.with_context(tds_revision_approved=True).write({
                'tds_rate_percent': rec.new_rate,
                'tds_not_applicable': rec.new_tds_not_applicable,
            })
            rec.write({
                'state': 'approved',
                'decided_by': self.env.user.id,
                'decided_date': fields.Datetime.now(),
            })
            approval.message_post(body=_(
                '\U0001f501 <b>TDS Rate Revised:</b> %(old)s%% to %(new)s%% '
                '(requested by %(req)s, approved by %(app)s)<br/><b>Reason:</b> %(reason)s',
                old=rec.old_rate, new=rec.new_rate,
                req=rec.requested_by.name, app=self.env.user.name, reason=rec.reason,
            ))
            approval._force_recompute_balances(warn=True)

    def action_reject(self):
        for rec in self:
            rec.approval_id._check_group(
                'bill_approval_flow_2.group_tds_revision', 'TDS Revision')
            if rec.state != 'pending':
                raise UserError(_('Only a pending revision can be rejected.'))
            if not rec.decision_comment:
                raise UserError(_('Please provide a reason for rejecting this revision.'))
            rec.write({
                'state': 'rejected',
                'decided_by': self.env.user.id,
                'decided_date': fields.Datetime.now(),
            })
            rec.approval_id.message_post(body=_(
                "\u274c <b>TDS Rate Revision Rejected:</b> %(old)s%% to %(new)s%% "
                "was requested by %(req)s, rejected by %(dec)s.<br/>"
                "<b>Requested reason:</b> %(reason)s<br/>"
                "<b>Rejection reason:</b> %(decision)s",
                old=rec.old_rate, new=rec.new_rate,
                req=rec.requested_by.name, dec=self.env.user.name,
                reason=rec.reason, decision=rec.decision_comment,
            ))
