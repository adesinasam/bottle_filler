# Copyright (c) 2024, Glistercp and contributors
# For license information, please see license.txt
"""POS Empty Bottle Entry hooks: empties dropped at the POS."""

import frappe
from frappe.utils import flt

from bottle_filler.bottle_filler import empties, empties_calc


def on_submit(pos_empty, method=None):
	if pos_empty.status != "Approved":
		return
	qty = abs(flt(pos_empty.empty_qty))
	if not qty:
		return

	warehouse = pos_empty.warehouse or empties.get_empty_warehouse(pos_empty, pos_empty, pos_empty.empty_item_code)
	se = empties.make_stock_entry(
		pos_empty,
		empties_calc.RECEIPT,
		[
			{
				"item_code": pos_empty.empty_item_code,
				"qty": qty,
				"warehouse": warehouse,
				"expense_account": empties.get_empty_expense_account(pos_empty.empty_item_code, pos_empty.company),
				"cost_center": pos_empty.cost_center,
			}
		],
		# Linked through stock_entry_no on this document, not salesinvoiceno, so that
		# cancelling the Sales Invoice does not cancel this entry's stock movement.
		{},
		empties.LEGACY_POS_ENTRY_REMARK,
	)
	pos_empty.db_set("stock_entry_no", se.name)

	rate = empties.get_empty_valuation_rate(pos_empty.empty_item_code, warehouse, pos_empty.company)
	empties.make_ledger_entry(
		item_code=pos_empty.item_code,
		item_name=pos_empty.item_name,
		warehouse=warehouse,
		posting_date=pos_empty.posting_date,
		posting_time=pos_empty.posting_time,
		empty_item_code=pos_empty.empty_item_code,
		empty_item_name=pos_empty.empty_item_name,
		voucher_type=pos_empty.voucher_type or "Sales Invoice",
		voucher_no=pos_empty.voucher_no,
		stock_entry_no=se.name,
		pos_empty_entry_no=pos_empty.name,
		price=flt(pos_empty.price),
		amount=flt(pos_empty.amount),
		customer=pos_empty.customer,
		empty_price=rate,
		empty_amount=rate * qty,
		company=pos_empty.company,
		cost_center=pos_empty.cost_center,
		territory=pos_empty.territory,
		**empties_calc.ledger_quantities(pos_empty.actual_qty, qty, inward=True),
	)


def on_cancel(pos_empty, method=None):
	names = set(
		frappe.get_all(
			"Empty Bottle Entry",
			filters={"pos_empty_entry_no": pos_empty.name, "stock_entry_no": ["is", "set"]},
			pluck="stock_entry_no",
		)
	)
	if pos_empty.stock_entry_no:
		names.add(pos_empty.stock_entry_no)
	empties.cancel_stock_entries(sorted(names))
	empties.cancel_ledger_entries({"pos_empty_entry_no": pos_empty.name})


def setup(pos_empty, method=None):
	"""Backward-compatible entry point (old hooks pointed submit and cancel here)."""
	if pos_empty.docstatus == 1:
		on_submit(pos_empty, method)
	elif pos_empty.docstatus == 2:
		on_cancel(pos_empty, method)
