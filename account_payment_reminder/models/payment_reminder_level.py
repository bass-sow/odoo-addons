from odoo import fields, models


class PaymentReminderLevel(models.Model):
    _name = "payment.reminder.level"
    _description = "Payment Reminder Level"
    _order = "company_id, delay"

    name = fields.Char(required=True, translate=True)
    delay = fields.Integer(
        string="Days Overdue",
        required=True,
        help="The reminder is sent when an invoice is at least this many days past its due date.",
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, ondelete="cascade"
    )
    mail_template_id = fields.Many2one(
        "mail.template",
        string="Email Template",
        domain=[("model", "=", "res.partner")],
        default=lambda self: self.env.ref(
            "account_payment_reminder.mail_template_payment_reminder", raise_if_not_found=False
        ),
        help="Template rendered on the customer. Leave empty to use the default one.",
    )
    note = fields.Text(
        string="Message",
        translate=True,
        help="Text added to the email for this level, e.g. a firmer tone at 30 days.",
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("delay_positive", "CHECK(delay > 0)", "Days overdue must be greater than zero."),
        ("delay_company_uniq", "UNIQUE(company_id, delay)",
         "There is already a reminder level with these days overdue in this company."),
    ]
