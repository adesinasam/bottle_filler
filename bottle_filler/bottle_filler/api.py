# Copyright (c) 2024, Adesina Akinyemi and contributors
# For license information, please see license.txt

import frappe


@frappe.whitelist()
def get_item_price(item_code, price_list):
	"""Kept for backward compatibility; the forms no longer call it."""
	frappe.has_permission("Item Price", "read", throw=True)
	price = frappe.db.get_value(
		"Item Price", {"item_code": item_code, "price_list": price_list}, "price_list_rate"
	)
	return {"price_list_rate": price}


@frappe.whitelist()
def get_empties_settings(item_code):
	"""Empties ratio for the filled item, used by the invoice forms."""
	frappe.has_permission("Item", "read", throw=True)
	values = frappe.db.get_value(
		"Item", item_code, ["has_empty_bottle", "empty_bottle_item", "empties_per_stock_uom"], as_dict=True
	)
	return values or {}
