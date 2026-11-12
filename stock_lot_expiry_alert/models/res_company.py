from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    expiry_warning_days = fields.Integer(
        string="Expiry Warning (days)",
        default=30,
        help="Lots expiring within this number of days are flagged as 'Expiring soon'.",
    )
    expiry_responsible_id = fields.Many2one(
        "res.users",
        string="Expiry Digest Recipient",
        help="User who receives the daily email with lots about to expire. "
        "Leave empty to disable the digest for this company.",
    )
