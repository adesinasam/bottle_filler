import frappe


def execute():
	"""Back-fill fields added by the empties posting fix.

	* empties_per_stock_uom = 1 for filled items (keeps the old 1:1 behaviour)
	* is_empty_bottle = 1 for every item used as an empty bottle/jar
	"""
	# Fixtures (custom fields) are synced after post_model_sync patches, so make
	# sure the new columns exist before back-filling them.
	from frappe.utils.fixtures import sync_fixtures

	sync_fixtures("bottle_filler")
	frappe.clear_cache(doctype="Item")

	frappe.db.sql(
		"""
		update `tabItem`
		set empties_per_stock_uom = 1
		where has_empty_bottle = 1 and ifnull(empties_per_stock_uom, 0) = 0
		"""
	)

	empty_items = frappe.get_all(
		"Item",
		filters={"has_empty_bottle": 1, "empty_bottle_item": ["is", "set"]},
		pluck="empty_bottle_item",
		distinct=True,
	)
	if empty_items:
		frappe.db.set_value("Item", {"name": ["in", empty_items]}, "is_empty_bottle", 1, update_modified=False)
