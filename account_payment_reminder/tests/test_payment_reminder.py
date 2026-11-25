from datetime import timedelta

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestPaymentReminder(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company = cls.company_data["company"]
        cls.env["payment.reminder.level"].search([("company_id", "=", cls.company.id)]).unlink()
        Level = cls.env["payment.reminder.level"]
        cls.level_7 = Level.create({"name": "First", "delay": 7, "company_id": cls.company.id})
        cls.level_15 = Level.create({"name": "Second", "delay": 15, "company_id": cls.company.id,
                                     "note": "Second notice"})
        cls.level_30 = Level.create({"name": "Final", "delay": 30, "company_id": cls.company.id})
        cls.customer = cls.env["res.partner"].create({
            "name": "Hotel Mar Blau",
            "email": "accounts@marblau.example.com",
        })
        today = fields.Date.context_today(cls.env["account.move"])
        cls.today = today
        cls.inv_10 = cls._invoice(today - timedelta(days=10), 100)
        cls.inv_40 = cls._invoice(today - timedelta(days=40), 250)
        cls.inv_not_due = cls._invoice(today, 300)

    @classmethod
    def _invoice(cls, due_date, amount, partner=None):
        invoice = cls.init_invoice(
            "out_invoice", partner=partner or cls.customer, invoice_date=due_date,
            amounts=[amount],
        )
        invoice.write({"invoice_payment_term_id": False, "invoice_date_due": due_date})
        invoice.action_post()
        return invoice

    def _reminder_mails(self):
        return self.env["mail.mail"].search([("subject", "ilike", "overdue invoices")])

    def _send(self):
        return self.env["account.move"]._send_payment_reminders(self.company)

    def test_days_overdue(self):
        self.assertEqual(self.inv_10.days_overdue, 10)
        self.assertEqual(self.inv_40.days_overdue, 40)
        self.assertEqual(self.inv_not_due.days_overdue, 0)

    def test_due_level(self):
        levels = self.level_7 | self.level_15 | self.level_30
        self.assertEqual(self.inv_10._get_due_reminder_level(levels), self.level_7)
        # Installed late: jumps straight to the highest level reached.
        self.assertEqual(self.inv_40._get_due_reminder_level(levels), self.level_30)
        self.assertIsNone(self.inv_not_due._get_due_reminder_level(levels))

    def test_one_email_per_customer_and_level(self):
        before = self._reminder_mails()
        self._send()
        mails = self._reminder_mails() - before
        # Two levels reached (7 and 30) -> two emails, each listing both overdue invoices.
        self.assertEqual(len(mails), 2)
        for mail in mails:
            self.assertIn(self.customer, mail.recipient_ids)
            self.assertIn(self.inv_10.name, mail.body_html)
            self.assertIn(self.inv_40.name, mail.body_html)
            self.assertNotIn(self.inv_not_due.name, mail.body_html)
        self.assertEqual(self.inv_10.payment_reminder_level_id, self.level_7)
        self.assertEqual(self.inv_40.payment_reminder_level_id, self.level_30)
        self.assertEqual(self.inv_10.payment_reminder_date, self.today)
        self.assertFalse(self.inv_not_due.payment_reminder_level_id)

    def test_not_sent_twice(self):
        self._send()
        before = self._reminder_mails()
        self.assertEqual(self._send(), 0)
        self.assertEqual(self._reminder_mails(), before)

    def test_next_level_when_more_days_pass(self):
        self._send()
        self.inv_10.payment_reminder_level_id = self.level_7
        # 8 more days: the invoice is now 18 days overdue -> level 15.
        self.inv_10.invoice_date_due = self.today - timedelta(days=18)
        before = self._reminder_mails()
        self.assertEqual(self._send(), 1)
        mail = self._reminder_mails() - before
        self.assertIn("Second notice", mail.body_html)
        self.assertEqual(self.inv_10.payment_reminder_level_id, self.level_15)

    def test_paid_invoice_is_skipped(self):
        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=self.inv_10.ids
        ).create({})._create_payments()
        self.assertIn(self.inv_10.payment_state, ("paid", "in_payment"))
        self._send()
        self.assertFalse(self.inv_10.payment_reminder_level_id)
        self.assertEqual(self.inv_40.payment_reminder_level_id, self.level_30)

    def test_partner_opt_out(self):
        self.customer.no_payment_reminder = True
        self.assertEqual(self._send(), 0)
        self.assertFalse(self.inv_40.payment_reminder_level_id)

    def test_customer_without_email(self):
        other = self.env["res.partner"].create({"name": "No Email SL"})
        invoice = self._invoice(self.today - timedelta(days=20), 50, partner=other)
        self._send()
        self.assertFalse(invoice.payment_reminder_level_id,
                         "not marked as sent when the email could not be sent")

    def test_chatter_message_and_reset(self):
        self._send()
        self.assertTrue(any("Payment reminder" in (m.body or "")
                            for m in self.inv_40.message_ids))
        self.inv_40.action_reset_payment_reminder()
        self.assertFalse(self.inv_40.payment_reminder_level_id)

    def test_cron_runs_for_companies_with_levels(self):
        self.env["account.move"]._cron_send_payment_reminders()
        self.assertEqual(self.inv_40.payment_reminder_level_id, self.level_30)
