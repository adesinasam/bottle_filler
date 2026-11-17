# Copyright (c) 2024, Glistercp and contributors
# For license information, please see license.txt
"""Sales Invoice hooks for empty bottle / jar tracking."""

from bottle_filler.bottle_filler import empties


def validate(sales_invoice, method=None):
	"""Compute expected empties, keep the qty actually dropped, set accounts."""
	empties.set_empties_on_items(sales_invoice)
	empties.set_sold_empties_expense_account(sales_invoice)


def on_submit(sales_invoice, method=None):
	empties.post_invoice_empties(sales_invoice)
	empties.post_pos_sold_empties(sales_invoice)


def on_cancel(sales_invoice, method=None):
	empties.cancel_invoice_empties(sales_invoice)


def setup(sales_invoice, method=None):
	"""Backward-compatible entry point (old hooks pointed submit and cancel here)."""
	if sales_invoice.docstatus == 1:
		on_submit(sales_invoice, method)
	elif sales_invoice.docstatus == 2:
		on_cancel(sales_invoice, method)
	return sales_invoice
