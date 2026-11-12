import logging
from datetime import timedelta

from odoo import api, fields, models
from odoo.osv import expression

_logger = logging.getLogger(__name__)

EXPIRY_STATES = [
    ("ok", "OK"),
    ("soon", "Expiring Soon"),
    ("expired", "Expired"),
]


class StockLot(models.Model):
    _inherit = "stock.lot"

    expiry_state = fields.Selection(
        EXPIRY_STATES,
        compute="_compute_expiry_state",
        search="_search_expiry_state",
    )
    days_to_expiry = fields.Integer(compute="_compute_expiry_state")
    currency_id = fields.Many2one(related="company_id.currency_id")
    expiry_value = fields.Monetary(
        string="Stock Value",
        compute="_compute_expiry_value",
        help="On hand quantity valued at the product cost.",
    )

    @api.depends("expiration_date", "company_id.expiry_warning_days")
    def _compute_expiry_state(self):
        now = fields.Datetime.now()
        for lot in self:
            if not lot.expiration_date:
                lot.expiry_state = False
                lot.days_to_expiry = 0
                continue
            delta = lot.expiration_date - now
            lot.days_to_expiry = (lot.expiration_date.date() - now.date()).days
            if lot.expiration_date <= now:
                lot.expiry_state = "expired"
            elif delta <= timedelta(days=lot.company_id.expiry_warning_days):
                lot.expiry_state = "soon"
            else:
                lot.expiry_state = "ok"

    def _search_expiry_state(self, operator, value):
        if operator not in ("=", "!=", "in", "not in"):
            raise NotImplementedError(f"Operator {operator} not supported for expiry_state")
        values = value if isinstance(value, (list, tuple)) else [value]

        # The threshold is a company setting; searching uses the current
        # company, which matches what the user sees in the list views.
        now = fields.Datetime.now()
        limit = now + timedelta(days=self.env.company.expiry_warning_days)
        domains = {
            "expired": [("expiration_date", "<=", now)],
            "soon": [("expiration_date", ">", now), ("expiration_date", "<=", limit)],
            "ok": [("expiration_date", ">", limit)],
            False: [("expiration_date", "=", False)],
        }
        domain = expression.OR([domains[v] for v in values])
        if operator in ("!=", "not in"):
            domain = ["!"] + expression.normalize_domain(domain)
        return domain

    @api.depends("product_qty", "product_id.standard_price")
    def _compute_expiry_value(self):
        for lot in self:
            lot.expiry_value = lot.product_qty * lot.product_id.standard_price

    @api.model
    def _get_expiring_lots(self, company):
        """Lots with stock in internal locations that are expired or expire
        within the company warning window."""
        limit = fields.Datetime.now() + timedelta(days=company.expiry_warning_days)
        quants = self.env["stock.quant"].search([
            ("company_id", "=", company.id),
            ("location_id.usage", "=", "internal"),
            ("quantity", ">", 0),
            ("lot_id.expiration_date", "<=", limit),
        ])
        return quants.lot_id.sorted("expiration_date")

    @api.model
    def _cron_send_expiry_digest(self):
        template = self.env.ref("stock_lot_expiry_alert.mail_template_expiry_digest")
        companies = self.env["res.company"].search([("expiry_responsible_id", "!=", False)])
        for company in companies:
            lots = self.with_company(company)._get_expiring_lots(company)
            if not lots:
                continue
            template.with_context(expiry_lot_ids=lots.ids).send_mail(company.id)
            _logger.info("Expiry digest sent for %s (%d lots)", company.name, len(lots))
