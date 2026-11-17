# Copyright (c) 2024, Glistercp and contributors
# For license information, please see license.txt
"""Purchase Invoice hooks for empty bottle / jar tracking."""

from bottle_filler.bottle_filler import empties


def validate(purchase_invoice, method=None):
	empties.set_empties_on_items(purchase_invoice)


def on_submit(purchase_invoice, method=None):
	empties.post_invoice_empties(purchase_invoice)


def on_cancel(purchase_invoice, method=None):
	empties.cancel_invoice_empties(purchase_invoice)


def setup(purchase_invoice, method=None):
	"""Backward-compatible entry point (old hooks pointed submit and cancel here)."""
	if purchase_invoice.docstatus == 1:
		on_submit(purchase_invoice, method)
	elif purchase_invoice.docstatus == 2:
		on_cancel(purchase_invoice, method)
	return purchase_invoice
