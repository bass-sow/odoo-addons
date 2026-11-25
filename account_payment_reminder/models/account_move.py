import logging
from collections import defaultdict

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    payment_reminder_level_id = fields.Many2one(
        "payment.reminder.level",
        string="Last Reminder",
        copy=False,
        readonly=True,
        tracking=True,
    )
    payment_reminder_date = fields.Date(string="Last Reminder Date", copy=False, readonly=True)
    days_overdue = fields.Integer(compute="_compute_days_overdue")

    @api.depends("invoice_date_due", "payment_state")
    def _compute_days_overdue(self):
        today = fields.Date.context_today(self)
        for move in self:
            due = move.invoice_date_due
            overdue = (today - due).days if due and move.payment_state in ("not_paid", "partial") else 0
            move.days_overdue = max(overdue, 0)

    @api.model
    def _get_reminder_domain(self, company):
        return [
            ("company_id", "=", company.id),
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "in", ("not_paid", "partial")),
            ("invoice_date_due", "<", fields.Date.context_today(self)),
            ("commercial_partner_id.no_payment_reminder", "=", False),
        ]

    def _get_due_reminder_level(self, levels):
        """Highest level reached by the invoice that has not been sent yet, or None.

        ``levels`` are the company levels sorted by delay. Levels are not sent twice,
        and an invoice that skipped some (e.g. the module was installed late) gets
        only the highest one it reached.
        """
        self.ensure_one()
        reached = levels.filtered(lambda lvl: lvl.delay <= self.days_overdue)
        if not reached:
            return None
        level = reached[-1]
        sent = self.payment_reminder_level_id
        if sent and sent.delay >= level.delay:
            return None
        return level

    @api.model
    def _cron_send_payment_reminders(self):
        # Scheduled job: runs for every company that has levels, whatever the
        # companies of the cron user are.
        moves = self.sudo()
        for company in moves.env["payment.reminder.level"].search([]).company_id:
            moves.with_company(company)._send_payment_reminders(company)

    @api.model
    def _send_payment_reminders(self, company):
        levels = self.env["payment.reminder.level"].search([("company_id", "=", company.id)])
        invoices = self.search(self._get_reminder_domain(company), order="invoice_date_due")

        # One email per customer and level, listing all its overdue invoices,
        # instead of one email per invoice.
        to_send = defaultdict(lambda: self.browse())
        for invoice in invoices:
            level = invoice._get_due_reminder_level(levels)
            if level:
                to_send[(invoice.commercial_partner_id, level)] |= invoice

        sent = 0
        default_template = self.env.ref("account_payment_reminder.mail_template_payment_reminder")
        for (partner, level), due_invoices in to_send.items():
            if not partner.email:
                _logger.warning("Payment reminder not sent: %s has no email", partner.display_name)
                continue
            overdue = invoices.filtered(lambda m, p=partner: m.commercial_partner_id == p)
            template = level.mail_template_id or default_template
            template.with_context(
                reminder_invoice_ids=overdue.ids,
                reminder_level_id=level.id,
            ).send_mail(partner.id, email_layout_xmlid="mail.mail_notification_light")
            due_invoices.write({
                "payment_reminder_level_id": level.id,
                "payment_reminder_date": fields.Date.context_today(self),
            })
            for invoice in due_invoices:
                invoice.message_post(body=_(
                    "Payment reminder '%(level)s' sent to %(email)s (%(days)s days overdue).",
                    level=level.name, email=partner.email, days=invoice.days_overdue,
                ))
            sent += 1
        _logger.info("Payment reminders for %s: %d emails sent", company.name, sent)
        return sent

    def action_reset_payment_reminder(self):
        """Start the reminder sequence again (e.g. after a payment plan fell through)."""
        self.write({"payment_reminder_level_id": False, "payment_reminder_date": False})
