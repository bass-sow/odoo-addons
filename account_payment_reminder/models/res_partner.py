from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    no_payment_reminder = fields.Boolean(
        string="No Payment Reminders",
        help="Do not send automatic payment reminders to this customer "
        "(e.g. a payment plan was agreed).",
    )
