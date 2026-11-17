# Copyright (c) 2024, Glistercp and contributors
# For license information, please see license.txt
"""Shared server logic for posting empty bottle / jar movements.

Used by Sales Invoice, Purchase Invoice and POS Empty Bottle Entry hooks.
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate, nowtime

from bottle_filler.bottle_filler import empties_calc

# Remark used on Stock Entries created from POS Empty Bottle Entry before this
# fix. Those entries also carry ``salesinvoiceno`` so they must not be
# cancelled when the Sales Invoice itself is cancelled.
LEGACY_POS_ENTRY_REMARK = "Being Empty Entry"


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------


def get_item_empties_settings(item_code):
	"""has_empty_bottle / empty_bottle_item / ratio / is_empty_bottle for an item."""
	values = frappe.get_cached_value(
		"Item",
		item_code,
		["has_empty_bottle", "empty_bottle_item", "empties_per_stock_uom", "is_empty_bottle", "allow_in_pos"],
		as_dict=True,
	)
	return values or frappe._dict()


def get_empty_expense_account(empty_item_code, company):
	"""Account charged for an empties movement.

	Resolution: the empty item's *Default Expense Account* (Item Defaults for the
	company) -> its Item Group's default expense account -> the company's
	Stock Adjustment Account.
	"""
	from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
	from erpnext.stock.doctype.item.item import get_item_defaults

	account = (get_item_defaults(empty_item_code, company) or {}).get("expense_account")
	if not account:
		account = (get_item_group_defaults(empty_item_code, company) or {}).get("expense_account")
	if not account:
		account = frappe.get_cached_value("Company", company, "stock_adjustment_account")
	if not account:
		frappe.throw(
			_("Set a Default Expense Account on Item {0} or a Stock Adjustment Account on Company {1}").format(
				frappe.bold(empty_item_code), frappe.bold(company)
			),
			title=_("Empties Account Missing"),
		)
	return account


def get_company_cogs_account(company):
	account = frappe.get_cached_value("Company", company, "default_expense_account")
	if not account:
		frappe.throw(
			_("Set Default Cost of Goods Sold Account on Company {0}").format(frappe.bold(company)),
			title=_("Missing Account"),
		)
	return account


def get_empty_warehouse(row, doc, empty_item_code):
	from erpnext.stock.doctype.item.item import get_item_defaults

	warehouse = (
		row.get("warehouse")
		or doc.get("set_warehouse")
		or (get_item_defaults(empty_item_code, doc.company) or {}).get("default_warehouse")
	)
	if not warehouse:
		frappe.throw(
			_("Row #{0}: set a Warehouse to receive/issue empties for {1}").format(
				row.idx, frappe.bold(empty_item_code)
			)
		)
	return warehouse


def get_empty_valuation_rate(empty_item_code, warehouse, company):
	"""Current valuation rate of the empty item; 0 if none is known yet."""
	if not (empty_item_code and warehouse):
		return 0.0
	from erpnext.stock.stock_ledger import get_valuation_rate

	try:
		return flt(
			get_valuation_rate(
				empty_item_code,
				warehouse,
				None,
				None,
				allow_zero_rate=True,
				company=company,
				raise_error_if_no_rate=False,
			)
		)
	except Exception:
		return 0.0


# ---------------------------------------------------------------------------
# validate: fill empties fields on invoice rows
# ---------------------------------------------------------------------------


def set_empties_on_items(doc):
	"""Compute expected empties per row and keep what the user entered.

	* ``expected_empty_qty`` is (re)computed from the row's stock qty.
	* ``empty_bottle_qty`` is only defaulted when it was never set, so a
	  customer/supplier dropping more or less than expected is preserved.
	* Rate/amount are the empty item's valuation rate (server side, not a
	  price list).
	"""
	for row in doc.get("items", []):
		if not row.item_code:
			continue
		settings = get_item_empties_settings(row.item_code)
		if not (settings.has_empty_bottle and settings.empty_bottle_item):
			continue

		row.has_empty_bottle = 1
		row.empty_bottle_item_code = settings.empty_bottle_item
		row.empty_bottle_item_name = frappe.get_cached_value("Item", settings.empty_bottle_item, "item_name")

		stock_qty = row.get("stock_qty")
		if not stock_qty:
			stock_qty = flt(row.qty) * (flt(row.conversion_factor) or 1)

		expected = empties_calc.expected_empty_qty(stock_qty, settings.empties_per_stock_uom)
		row.expected_empty_qty = expected
		row.empty_bottle_qty = empties_calc.resolve_dropped_qty(row.get("empty_bottle_qty"), expected)

		warehouse = row.get("warehouse") or doc.get("set_warehouse")
		row.empty_bottle_rate = get_empty_valuation_rate(row.empty_bottle_item_code, warehouse, doc.company)
		row.empty_bottle_amount = flt(row.empty_bottle_rate) * flt(row.empty_bottle_qty)


def is_sold_empty(row):
	"""Row sells the empty bottle/jar itself (not a filled item)."""
	if not row.item_code:
		return False
	settings = get_item_empties_settings(row.item_code)
	return bool((settings.is_empty_bottle or settings.allow_in_pos) and not settings.has_empty_bottle)


def set_sold_empties_expense_account(doc):
	"""Sales of empties are charged to the company's default COGS account."""
	rows = [row for row in doc.get("items", []) if is_sold_empty(row)]
	if not rows:
		return
	cogs = get_company_cogs_account(doc.company)
	for row in rows:
		row.expense_account = cogs


def get_traded_empties(doc):
	"""Empties sold to / bought from the party on this voucher, per empty item.

	These are rows whose item *is* the empty (e.g. a customer short of empties
	buying empty crates, or empty jars bought from a supplier). Qty is in the
	empty item's stock UOM.
	"""
	traded = {}
	for row in doc.get("items", []):
		if row.item_code and is_sold_empty(row):
			qty = abs(flt(row.get("stock_qty") or flt(row.qty) * (flt(row.conversion_factor) or 1)))
			traded[row.item_code] = traded.get(row.item_code, 0) + qty
	return traded


def validate_sold_empties(doc, method=None):
	"""validate hook for Delivery Note / POS Invoice: empties sold go to COGS."""
	set_sold_empties_expense_account(doc)


# ---------------------------------------------------------------------------
# Stock Entry + ledger
# ---------------------------------------------------------------------------


def make_stock_entry(doc, purpose, lines, link_fields, remarks):
	"""Create and submit one Stock Entry.

	``lines``: dicts with item_code, qty (stock UOM, > 0), warehouse,
	expense_account, cost_center, project.
	"""
	warehouse_field = "t_warehouse" if purpose == empties_calc.RECEIPT else "s_warehouse"
	se = frappe.new_doc("Stock Entry")
	se.update(
		{
			"stock_entry_type": purpose,
			"purpose": purpose,
			"company": doc.company,
			"posting_date": doc.get("posting_date") or nowdate(),
			"posting_time": doc.get("posting_time") or nowtime(),
			"set_posting_time": 1,
			"remarks": remarks,
			"project": doc.get("project"),
			**link_fields,
		}
	)
	for line in lines:
		stock_uom = frappe.get_cached_value("Item", line["item_code"], "stock_uom")
		se.append(
			"items",
			{
				"item_code": line["item_code"],
				"qty": abs(flt(line["qty"])),
				"uom": stock_uom,
				"stock_uom": stock_uom,
				"conversion_factor": 1,
				warehouse_field: line["warehouse"],
				"expense_account": line["expense_account"],
				"cost_center": line.get("cost_center"),
				"project": line.get("project"),
			},
		)
	se.flags.ignore_permissions = True
	se.insert()
	se.submit()
	return se


def make_ledger_entry(**values):
	values.setdefault("status", "Submitted")
	entry = frappe.get_doc({"doctype": "Empty Bottle Entry", **values})
	entry.flags.ignore_permissions = True
	entry.insert()
	return entry


def cancel_stock_entries(names):
	for name in names:
		if frappe.db.get_value("Stock Entry", name, "docstatus") != 1:
			continue
		se = frappe.get_doc("Stock Entry", name)
		se.flags.ignore_permissions = True
		se.cancel()


def cancel_ledger_entries(filters):
	for name in frappe.get_all("Empty Bottle Entry", filters=filters, pluck="name"):
		frappe.db.set_value("Empty Bottle Entry", name, {"status": "Cancelled", "is_cancelled": 1})


# ---------------------------------------------------------------------------
# Invoices (Sales Invoice / Purchase Invoice)
# ---------------------------------------------------------------------------


def _invoice_link_fields(doc):
	if doc.doctype == "Sales Invoice":
		return {"with_sales": 1, "salesinvoiceno": doc.name}
	return {"with_purchase": 1, "purchase_invoice_no": doc.name}


def _party_fields(doc):
	if doc.doctype == "Sales Invoice":
		return {"customer": doc.customer, "territory": doc.get("territory")}
	return {"supplier": doc.supplier}


def get_invoice_stock_entries(doc):
	if doc.doctype == "Sales Invoice":
		filters = {"salesinvoiceno": doc.name, "docstatus": 1, "remarks": ["!=", LEGACY_POS_ENTRY_REMARK]}
	else:
		filters = {"purchase_invoice_no": doc.name, "docstatus": 1}
	return frappe.get_all("Stock Entry", filters=filters, pluck="name")


def post_invoice_empties(doc):
	"""on_submit: move empties for filled rows and write the party ledger."""
	rows = [row for row in doc.get("items", []) if row.get("empty_bottle_item_code")]
	if not rows:
		return None

	if get_invoice_stock_entries(doc):
		frappe.throw(_("Empties Stock Entry for {0} {1} already exists.").format(doc.doctype, doc.name))

	is_return = bool(doc.get("is_return"))
	inward = empties_calc.is_inward(doc.doctype, is_return)
	purpose = empties_calc.stock_entry_purpose(doc.doctype, is_return)

	lines, ledger = [], []
	for row in rows:
		empty_item = row.empty_bottle_item_code
		warehouse = get_empty_warehouse(row, doc, empty_item)
		expected = row.get("expected_empty_qty")
		if expected is None:
			expected = empties_calc.expected_empty_qty(row.get("stock_qty") or row.qty)
		dropped = abs(flt(row.empty_bottle_qty))
		if dropped:
			lines.append(
				{
					"item_code": empty_item,
					"qty": dropped,
					"warehouse": warehouse,
					"expense_account": get_empty_expense_account(empty_item, doc.company),
					"cost_center": row.get("cost_center"),
					"project": row.get("project") or doc.get("project"),
				}
			)
		ledger.append([row, warehouse, abs(flt(expected)), dropped])

	traded = get_traded_empties(doc)
	allocated = {}
	for empty_item in {entry[0].empty_bottle_item_code for entry in ledger}:
		entries = [entry for entry in ledger if entry[0].empty_bottle_item_code == empty_item]
		shares = empties_calc.allocate_traded_qty(
			[expected - dropped for _row, _wh, expected, dropped in entries], traded.get(empty_item, 0)
		)
		for entry, share in zip(entries, shares):
			allocated[entry[0].name] = share
	ledger = [
		(row, warehouse, empties_calc.ledger_quantities(expected, dropped, inward, allocated.get(row.name, 0)))
		for row, warehouse, expected, dropped in ledger
	]

	se = None
	if lines:
		label = "Return " if is_return else ""
		kind = "Sales" if doc.doctype == "Sales Invoice" else "Purchase"
		se = make_stock_entry(
			doc, purpose, lines, _invoice_link_fields(doc), f"Being {kind} {label}Empty Entry"
		)

	for row, warehouse, qtys in ledger:
		make_ledger_entry(
			item_code=row.item_code,
			item_name=row.item_name,
			warehouse=warehouse,
			posting_date=doc.posting_date,
			posting_time=doc.posting_time,
			empty_item_code=row.empty_bottle_item_code,
			empty_item_name=row.get("empty_bottle_item_name"),
			voucher_type=doc.doctype,
			voucher_no=doc.name,
			stock_entry_no=se.name if se else None,
			price=flt(row.rate),
			amount=flt(row.amount),
			empty_price=flt(row.get("empty_bottle_rate")),
			empty_amount=flt(row.get("empty_bottle_rate")) * qtys["empty_qty"],
			company=doc.company,
			cost_center=row.get("cost_center"),
			**qtys,
			**_party_fields(doc),
		)
	return se


def post_pos_sold_empties(doc):
	"""POS Sales Invoice selling empties without updating stock.

	When the invoice has *Update Stock* ticked ERPNext already issues the
	empties (and the row's expense account is the company COGS), so nothing
	extra must be posted, otherwise stock would be deducted twice.
	"""
	if doc.doctype != "Sales Invoice" or not doc.get("is_pos") or doc.get("update_stock"):
		return None
	rows = [row for row in doc.get("items", []) if is_sold_empty(row) and flt(row.get("stock_qty") or row.qty)]
	if not rows:
		return None

	is_return = bool(doc.get("is_return"))
	# selling empties is the opposite direction to receiving them
	purpose = empties_calc.RECEIPT if is_return else empties_calc.ISSUE
	cogs = get_company_cogs_account(doc.company)

	lines = []
	for row in rows:
		lines.append(
			{
				"item_code": row.item_code,
				"qty": abs(flt(row.get("stock_qty") or row.qty)),
				"warehouse": get_empty_warehouse(row, doc, row.item_code),
				"expense_account": cogs,
				"cost_center": row.get("cost_center"),
				"project": row.get("project") or doc.get("project"),
			}
		)
	# Selling empties is a sale, not an exchange: it is not written to the
	# Empty Bottle Entry ledger. Where it covers a customer's shortfall on the
	# same invoice it is shown as traded_empty_qty on the filled row instead.
	return make_stock_entry(doc, purpose, lines, _invoice_link_fields(doc), "Being POS Empty Entry")


def cancel_invoice_empties(doc):
	"""on_cancel: cancel the empties Stock Entries and mark ledger rows cancelled."""
	cancel_stock_entries(get_invoice_stock_entries(doc))
	cancel_ledger_entries(
		{"voucher_type": doc.doctype, "voucher_no": doc.name, "pos_empty_entry_no": ["is", "not set"]}
	)
