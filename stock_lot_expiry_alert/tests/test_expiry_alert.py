from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestExpiryAlert(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.expiry_warning_days = 30
        cls.stock_location = cls.env.ref("stock.stock_location_stock")
        cls.product = cls.env["product.product"].create({
            "name": "Yogurt",
            "type": "product",
            "tracking": "lot",
            "use_expiration_date": True,
            "standard_price": 2.5,
        })
        now = fields.Datetime.now()
        cls.lot_expired = cls._create_lot("LOT-EXP", now - timedelta(days=2), 10)
        cls.lot_soon = cls._create_lot("LOT-SOON", now + timedelta(days=10), 4)
        cls.lot_ok = cls._create_lot("LOT-OK", now + timedelta(days=90), 20)
        cls.lot_empty = cls._create_lot("LOT-EMPTY", now + timedelta(days=5), 0)

    @classmethod
    def _create_lot(cls, name, expiration_date, qty):
        lot = cls.env["stock.lot"].create({
            "name": name,
            "product_id": cls.product.id,
            "company_id": cls.company.id,
            "expiration_date": expiration_date,
        })
        if qty:
            cls.env["stock.quant"]._update_available_quantity(
                cls.product, cls.stock_location, qty, lot_id=lot
            )
        return lot

    def test_expiry_state(self):
        self.assertEqual(self.lot_expired.expiry_state, "expired")
        self.assertEqual(self.lot_soon.expiry_state, "soon")
        self.assertEqual(self.lot_ok.expiry_state, "ok")
        self.assertEqual(self.lot_soon.days_to_expiry, 10)
        self.assertEqual(self.lot_expired.days_to_expiry, -2)

    def test_warning_days_change(self):
        self.company.expiry_warning_days = 120
        self.lot_ok.invalidate_recordset(["expiry_state"])
        self.assertEqual(self.lot_ok.expiry_state, "soon")

    def test_search_expiry_state(self):
        lots = self.lot_expired | self.lot_soon | self.lot_ok | self.lot_empty
        domain = [("id", "in", lots.ids)]
        Lot = self.env["stock.lot"]
        self.assertEqual(
            Lot.search(domain + [("expiry_state", "=", "soon")]),
            self.lot_soon | self.lot_empty,
        )
        self.assertEqual(
            Lot.search(domain + [("expiry_state", "in", ["soon", "expired"])]),
            self.lot_expired | self.lot_soon | self.lot_empty,
        )
        self.assertEqual(Lot.search(domain + [("expiry_state", "!=", "ok")]), lots - self.lot_ok)

    def test_expiry_value(self):
        self.assertAlmostEqual(self.lot_soon.expiry_value, 10.0)

    def test_expiring_lots_ignore_empty_stock(self):
        lots = self.env["stock.lot"]._get_expiring_lots(self.company)
        self.assertIn(self.lot_expired, lots)
        self.assertIn(self.lot_soon, lots)
        self.assertNotIn(self.lot_ok, lots)
        self.assertNotIn(self.lot_empty, lots)

    def test_cron_sends_digest(self):
        responsible = self.env["res.users"].create({
            "name": "Warehouse Manager",
            "login": "wh_manager_expiry",
            "email": "wh.manager@example.com",
        })
        self.company.expiry_responsible_id = responsible
        Mail = self.env["mail.mail"]
        mails_before = Mail.search([])

        self.env["stock.lot"]._cron_send_expiry_digest()

        new_mail = Mail.search([]) - mails_before
        new_mail = new_mail.filtered(lambda m: "expiring" in (m.subject or ""))
        self.assertEqual(len(new_mail), 1)
        self.assertIn(responsible.partner_id, new_mail.recipient_ids)
        self.assertIn("LOT-SOON", new_mail.body_html)
        self.assertIn("LOT-EXP", new_mail.body_html)
        self.assertNotIn("LOT-OK", new_mail.body_html)

    def test_cron_without_responsible(self):
        self.company.expiry_responsible_id = False
        mails_before = self.env["mail.mail"].search_count([])
        self.env["stock.lot"]._cron_send_expiry_digest()
        self.assertEqual(self.env["mail.mail"].search_count([]), mails_before)
