# Copyright (c) 2026, Glistercp and Contributors
# See license.txt
"""Unit tests for the pure empties calculations (no database needed)."""

import unittest

from bottle_filler.bottle_filler import empties_calc as calc


class TestExpectedEmptyQty(unittest.TestCase):
	def test_one_to_one(self):
		self.assertEqual(calc.expected_empty_qty(10, 1), 10)

	def test_missing_ratio_defaults_to_one(self):
		self.assertEqual(calc.expected_empty_qty(10, None), 10)
		self.assertEqual(calc.expected_empty_qty(10, 0), 10)

	def test_ratio_converts_to_empty_stock_uom(self):
		# 2 crates sold, filled item stocked in bottles (48), empty stocked per crate of 24
		self.assertAlmostEqual(calc.expected_empty_qty(48, 1 / 24), 2)
		# filled stocked per crate, empty stocked per bottle
		self.assertEqual(calc.expected_empty_qty(10, 24), 240)

	def test_return_qty_is_positive(self):
		self.assertEqual(calc.expected_empty_qty(-20, 1), 20)


class TestDirection(unittest.TestCase):
	def test_sales_receive_empties(self):
		self.assertTrue(calc.is_inward("Sales Invoice"))
		self.assertEqual(calc.stock_entry_purpose("Sales Invoice"), calc.RECEIPT)
		self.assertEqual(calc.warehouse_key("Sales Invoice"), "t_warehouse")

	def test_sales_return_issues_empties(self):
		self.assertFalse(calc.is_inward("Sales Invoice", is_return=True))
		self.assertEqual(calc.stock_entry_purpose("Sales Invoice", True), calc.ISSUE)
		self.assertEqual(calc.warehouse_key("Sales Invoice", True), "s_warehouse")

	def test_purchase_issues_empties(self):
		self.assertEqual(calc.stock_entry_purpose("Purchase Invoice"), calc.ISSUE)

	def test_purchase_return_receives_empties(self):
		self.assertEqual(calc.stock_entry_purpose("Purchase Invoice", True), calc.RECEIPT)

	def test_pos_entry_receives_empties(self):
		self.assertEqual(calc.stock_entry_purpose("POS Empty Bottle Entry"), calc.RECEIPT)

	def test_unknown_voucher(self):
		with self.assertRaises(ValueError):
			calc.is_inward("Journal Entry")


class TestDroppedQty(unittest.TestCase):
	def test_unset_defaults_to_expected(self):
		self.assertEqual(calc.resolve_dropped_qty(None, 10), 10)

	def test_user_value_kept_less(self):
		self.assertEqual(calc.resolve_dropped_qty(7, 10), 7)

	def test_user_value_kept_more(self):
		self.assertEqual(calc.resolve_dropped_qty(12, 10), 12)

	def test_zero_is_kept(self):
		self.assertEqual(calc.resolve_dropped_qty(0, 10), 0)

	def test_negative_made_positive(self):
		self.assertEqual(calc.resolve_dropped_qty(-5, 10), 5)


class TestLedgerQuantities(unittest.TestCase):
	def test_exact_drop(self):
		q = calc.ledger_quantities(10, 10, inward=True)
		self.assertEqual(q["actual_qty"], 10)
		self.assertEqual(q["empty_qty"], 10)
		self.assertEqual(q["in_empty_qty"], 10)
		self.assertEqual(q["out_empty_qty"], 0)
		self.assertEqual(q["difference_in_qty"], 0)

	def test_short_drop_is_positive_difference(self):
		self.assertEqual(calc.ledger_quantities(10, 7, True)["difference_in_qty"], 3)

	def test_over_drop_is_negative_difference(self):
		self.assertEqual(calc.ledger_quantities(10, 12, True)["difference_in_qty"], -2)

	def test_outward(self):
		q = calc.ledger_quantities(20, 20, inward=False)
		self.assertEqual(q["in_empty_qty"], 0)
		self.assertEqual(q["out_empty_qty"], 20)

	def test_traded_empties_reduce_shortfall(self):
		q = calc.ledger_quantities(10, 6, True, traded_qty=4)
		self.assertEqual(q["traded_empty_qty"], 4)
		self.assertEqual(q["difference_in_qty"], 0)

	def test_signs_ignored(self):
		q = calc.ledger_quantities(-20, -18, inward=False)
		self.assertEqual(q["actual_qty"], 20)
		self.assertEqual(q["empty_qty"], 18)
		self.assertEqual(q["difference_in_qty"], 2)


class TestAllocateTradedQty(unittest.TestCase):
	def test_covers_shortfall_in_row_order(self):
		self.assertEqual(calc.allocate_traded_qty([4, 3], 5), [4, 1])

	def test_rows_not_short_get_nothing(self):
		self.assertEqual(calc.allocate_traded_qty([0, -2, 3], 5), [0, 0, 3])

	def test_extra_bought_is_not_allocated(self):
		self.assertEqual(calc.allocate_traded_qty([2], 10), [2])

	def test_nothing_traded(self):
		self.assertEqual(calc.allocate_traded_qty([4, 3], 0), [0, 0])


if __name__ == "__main__":
	unittest.main()
