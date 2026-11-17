# Copyright (c) 2024, Glistercp and contributors
# For license information, please see license.txt
"""Pure calculation helpers for empty bottle / jar movements.

Nothing in this module touches the database, so it can be unit-tested
without a Frappe site.

Conventions
-----------
* All empties quantities are in the **empty item's stock UOM**.
* ``empties_per_stock_uom`` is set on the *filled* item: how many units of the
  empty item (in its stock UOM) go with one stock UOM of the filled item.
  Example: filled item stocked per crate, empty item stocked per crate -> 1.
  Filled item stocked per bottle, empty item stocked per crate of 24 -> 1/24.
* Quantities sent to Stock Entry are always positive; direction is expressed
  by Material Receipt (inward) / Material Issue (outward).
"""

RECEIPT = "Material Receipt"
ISSUE = "Material Issue"

# True = empties come INTO our warehouse on a normal (non-return) voucher.
_INWARD_ON_NORMAL = {
	"Sales Invoice": True,  # customer drops empties when buying
	"POS Empty Bottle Entry": True,  # customer drops empties at POS
	"Purchase Invoice": False,  # we hand empties to the supplier
}


def _flt(value, precision=9):
	try:
		return round(float(value or 0), precision)
	except (TypeError, ValueError):
		return 0.0


def expected_empty_qty(stock_qty, empties_per_stock_uom=1, precision=6):
	"""Empties expected for a filled row, in the empty item's stock UOM.

	``stock_qty`` may be negative (return invoices); the result is always >= 0.
	A missing or zero ratio is treated as 1.
	"""
	ratio = _flt(empties_per_stock_uom) or 1.0
	return round(abs(_flt(stock_qty)) * ratio, precision)


def is_inward(voucher_type, is_return=False):
	"""Do empties come into stock for this voucher?"""
	if voucher_type not in _INWARD_ON_NORMAL:
		raise ValueError(f"Unsupported voucher type for empties: {voucher_type}")
	inward = _INWARD_ON_NORMAL[voucher_type]
	return (not inward) if is_return else inward


def stock_entry_purpose(voucher_type, is_return=False):
	return RECEIPT if is_inward(voucher_type, is_return) else ISSUE


def warehouse_key(voucher_type, is_return=False):
	"""Stock Entry Detail field that should carry the warehouse."""
	return "t_warehouse" if is_inward(voucher_type, is_return) else "s_warehouse"


def ledger_quantities(expected_qty, dropped_qty, inward, traded_qty=0):
	"""Values for an Empty Bottle Entry ledger row.

	* ``actual_qty``        expected empties (from the filled qty)
	* ``empty_qty``         empties actually exchanged (always positive)
	* ``in_empty_qty``      empties received into stock
	* ``out_empty_qty``     empties issued from stock
	* ``traded_empty_qty``  empties sold to / bought from the party on the same
	                        voucher to cover a shortfall
	* ``difference_in_qty`` expected - exchanged - traded (positive = shortfall,
	                        negative = party gave/received more than expected)
	"""
	expected = abs(_flt(expected_qty))
	dropped = abs(_flt(dropped_qty))
	traded = abs(_flt(traded_qty))
	return {
		"actual_qty": expected,
		"empty_qty": dropped,
		"in_empty_qty": dropped if inward else 0.0,
		"out_empty_qty": 0.0 if inward else dropped,
		"traded_empty_qty": traded,
		"difference_in_qty": round(expected - dropped - traded, 9),
	}


def allocate_traded_qty(shortfalls, traded_qty):
	"""Spread empties sold/bought on a voucher over the rows that are short.

	``shortfalls``: list of (expected - exchanged) per filled row, in row order,
	all for the same empty item. Each row gets at most its shortfall; rows that
	are not short get 0. Whatever is left over (the party bought more empties
	than it was short) is an ordinary sale/purchase and is not allocated.
	"""
	pool = abs(_flt(traded_qty))
	allocation = []
	for shortfall in shortfalls:
		take = min(max(_flt(shortfall), 0.0), pool)
		allocation.append(round(take, 9))
		pool = round(pool - take, 9)
	return allocation


def resolve_dropped_qty(entered_qty, expected_qty):
	"""Qty the party actually exchanged.

	``None`` means the user/POS never set the field -> default to expected.
	Any value the user entered (including 0) is kept; sign is ignored.
	"""
	if entered_qty is None:
		return abs(_flt(expected_qty))
	return abs(_flt(entered_qty))
