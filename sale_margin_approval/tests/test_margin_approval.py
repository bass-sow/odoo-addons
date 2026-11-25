from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestMarginApproval(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.sale_min_margin = 25.0
        cls.salesman = new_test_user(
            cls.env, login="margin_salesman", groups="sales_team.group_sale_salesman"
        )
        cls.manager = new_test_user(
            cls.env, login="margin_manager", groups="sales_team.group_sale_manager"
        )
        cls.company.sale_margin_approver_id = cls.manager
        cls.partner = cls.env["res.partner"].create({"name": "Restaurante La Plaça"})
        # Cost 80, price 100: 20 % margin, below the 25 % minimum.
        cls.product = cls.env["product.product"].create({
            "name": "Olive Oil 5L",
            "type": "consu",
            "list_price": 100.0,
            "standard_price": 80.0,
        })

    def _order(self, user, price=100.0):
        order = self.env["sale.order"].with_user(user).create({
            "partner_id": self.partner.id,
            "order_line": [(0, 0, {
                "product_id": self.product.id,
                "product_uom_qty": 10,
                "price_unit": price,
            })],
        })
        return order

    def test_margin_above_minimum_confirms(self):
        order = self._order(self.salesman, price=120.0)  # 33 % margin
        self.assertEqual(order.margin_approval_state, "not_needed")
        order.action_confirm()
        self.assertEqual(order.state, "sale")

    def test_salesman_cannot_confirm_low_margin(self):
        order = self._order(self.salesman)
        self.assertEqual(order.margin_approval_state, "to_approve")
        with self.assertRaises(UserError):
            order.action_confirm()
        self.assertEqual(order.state, "draft")

    def test_salesman_cannot_approve(self):
        order = self._order(self.salesman)
        with self.assertRaises(AccessError):
            order.action_approve_margin()

    def test_request_creates_activity_for_approver(self):
        order = self._order(self.salesman)
        order.action_request_margin_approval()
        self.assertTrue(order.margin_approval_requested)
        activity = order.sudo().activity_ids
        self.assertEqual(len(activity), 1)
        self.assertEqual(activity.user_id, self.manager)

    def test_approval_flow(self):
        order = self._order(self.salesman)
        order.action_request_margin_approval()

        order.with_user(self.manager).action_approve_margin()
        self.assertEqual(order.margin_approval_state, "approved")
        self.assertEqual(order.margin_approved_by_id, self.manager)
        self.assertAlmostEqual(order.margin_approved_percent, 0.2)
        self.assertFalse(order.sudo().activity_ids, "the approval activity is marked as done")

        order.action_confirm()
        self.assertEqual(order.state, "sale")
        self.assertEqual(order.margin_approval_state, "not_needed")

    def test_lower_margin_after_approval_needs_new_approval(self):
        order = self._order(self.salesman)
        order.with_user(self.manager).action_approve_margin()
        order.order_line.discount = 5.0  # margin drops from 20 % to ~15.8 %
        self.assertEqual(order.margin_approval_state, "to_approve")
        with self.assertRaises(UserError):
            order.action_confirm()

    def test_higher_margin_after_approval_keeps_approval(self):
        order = self._order(self.salesman)
        order.with_user(self.manager).action_approve_margin()
        order.order_line.price_unit = 104.0
        self.assertEqual(order.margin_approval_state, "approved")

    def test_manager_confirm_records_approval(self):
        order = self._order(self.manager)
        order.action_confirm()
        self.assertEqual(order.state, "sale")
        self.assertEqual(order.margin_approved_by_id, self.manager)

    def test_disabled_when_minimum_is_zero(self):
        self.company.sale_min_margin = 0
        order = self._order(self.salesman)
        self.assertEqual(order.margin_approval_state, "not_needed")
        order.action_confirm()
        self.assertEqual(order.state, "sale")

    def test_minimum_change_recomputes_open_quotations(self):
        order = self._order(self.salesman)
        self.assertEqual(order.margin_approval_state, "to_approve")
        self.company.sale_min_margin = 15.0
        self.assertEqual(order.margin_approval_state, "not_needed")

    def test_copy_drops_approval(self):
        order = self._order(self.salesman)
        order.with_user(self.manager).action_approve_margin()
        copy = order.copy()
        self.assertFalse(copy.margin_approved_by_id)
        self.assertEqual(copy.margin_approval_state, "to_approve")
