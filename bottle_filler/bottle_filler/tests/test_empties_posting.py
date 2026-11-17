# Copyright (c) 2026, Glistercp and Contributors
# See license.txt
"""Integration tests: empties posting from Sales / Purchase Invoices.

Run with:  bench --site <site> run-tests --app bottle_filler
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

import erpnext
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.controllers.sales_and_purchase_return import make_return_doc
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

test_dependencies = ["Sales Invoice", "Purchase Invoice"]

COMPANY = "_Test Company"
WAREHOUSE = "_Test Warehouse - _TC"


def get_empties_account():
	name = frappe.db.get_value("Account", {"account_name": "_Test BF Empties Expense", "company": COMPANY})
	if name:
		return name
	parent = frappe.db.get_value(
		"Account", {"company": COMPANY, "is_group": 1, "root_type": "Expense"}, "name", order_by="lft desc"
	)
	return (
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "_Test BF Empties Expense",
				"parent_account": parent,
				"company": COMPANY,
				"root_type": "Expense",
				"report_type": "Profit and Loss",
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def make_empty_item(item_code, valuation_rate, account):
	return make_item(
		item_code,
		{
			"is_stock_item": 1,
			"is_empty_bottle": 1,
			"valuation_rate": valuation_rate,
			"item_defaults": [
				{"company": COMPANY, "default_warehouse": WAREHOUSE, "expense_account": account}
			],
		},
	).name


def make_filled_item(item_code, empty_item, ratio=1, uoms=None):
	return make_item(
		item_code,
		{
			"is_stock_item": 1,
			"has_empty_bottle": 1,
			"empty_bottle_item": empty_item,
			"empties_per_stock_uom": ratio,
		},
		uoms=uoms,
	).name


class TestEmptiesPosting(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.account = get_empties_account()
		cls.empty_crate = make_empty_item("_Test BF Empty Crate", 500, cls.account)
		cls.coke_crate = make_filled_item("_Test BF Coke 50CL Crate", cls.empty_crate)
		cls.empty_jar = make_empty_item("_Test BF Empty Jar", 300, cls.account)
		cls.water_jar = make_filled_item("_Test BF CWay Jar", cls.empty_jar)
		# filled item stocked in bottles, sold in boxes of 24; empty crate holds 24 bottles
		cls.coke_bottle = make_filled_item(
			"_Test BF Coke 50CL Bottle",
			cls.empty_crate,
			ratio=1 / 24,
			uoms=[{"uom": "Box", "conversion_factor": 24}],
		)

	# helpers --------------------------------------------------------------

	def make_si(self, item_code, qty, empty_qty="unset", submit=True, **kwargs):
		si = create_sales_invoice(
			company=COMPANY,
			item_code=item_code,
			qty=qty,
			rate=1000,
			warehouse=WAREHOUSE,
			uom="Nos",
			do_not_save=1,
			**kwargs,
		)
		if empty_qty != "unset":
			si.items[0].empty_bottle_qty = empty_qty
		si.insert()
		if submit:
			si.submit()
		return si

	def get_stock_entries(self, fieldname, voucher_no, docstatus=None):
		filters = {fieldname: voucher_no}
		if docstatus is not None:
			filters["docstatus"] = docstatus
		return [
			frappe.get_doc("Stock Entry", name)
			for name in frappe.get_all("Stock Entry", filters=filters, pluck="name")
		]

	def get_ledger(self, voucher_no):
		return frappe.get_all(
			"Empty Bottle Entry",
			filters={"voucher_no": voucher_no},
			fields=[
				"empty_item_code",
				"actual_qty",
				"empty_qty",
				"in_empty_qty",
				"out_empty_qty",
				"difference_in_qty",
				"is_cancelled",
				"status",
				"stock_entry_no",
				"customer",
				"supplier",
			],
		)

	def receive_empties(self, item_code, qty, rate):
		make_stock_entry(item_code=item_code, target=WAREHOUSE, qty=qty, basic_rate=rate, company=COMPANY)

	# sales -------------------------------------------------------------------

	def test_sale_exact_drop_receives_empties_into_item_account(self):
		si = self.make_si(self.coke_crate, 10)
		self.assertEqual(flt(si.items[0].expected_empty_qty), 10)
		self.assertEqual(flt(si.items[0].empty_bottle_qty), 10)

		(se,) = self.get_stock_entries("salesinvoiceno", si.name)
		self.assertEqual(se.docstatus, 1)
		self.assertEqual(se.purpose, "Material Receipt")
		self.assertEqual(len(se.items), 1)
		row = se.items[0]
		self.assertEqual(row.item_code, self.empty_crate)
		self.assertEqual(flt(row.qty), 10)
		self.assertEqual(row.t_warehouse, WAREHOUSE)
		self.assertEqual(row.expense_account, self.account)
		self.assertEqual(flt(row.basic_rate), 500)

		if erpnext.is_perpetual_inventory_enabled(COMPANY):
			accounts = frappe.get_all(
				"GL Entry", filters={"voucher_type": "Stock Entry", "voucher_no": se.name}, pluck="account"
			)
			self.assertIn(self.account, accounts)
			stock_adjustment = frappe.get_cached_value("Company", COMPANY, "stock_adjustment_account")
			if stock_adjustment != self.account:
				self.assertNotIn(stock_adjustment, accounts)

		(ledger,) = self.get_ledger(si.name)
		self.assertEqual(ledger.empty_item_code, self.empty_crate)
		self.assertEqual(flt(ledger.actual_qty), 10)
		self.assertEqual(flt(ledger.in_empty_qty), 10)
		self.assertEqual(flt(ledger.out_empty_qty), 0)
		self.assertEqual(flt(ledger.difference_in_qty), 0)
		self.assertEqual(ledger.stock_entry_no, se.name)
		self.assertEqual(ledger.customer, si.customer)

	def test_sale_customer_drops_fewer_empties(self):
		si = self.make_si(self.water_jar, 20, empty_qty=15)
		(se,) = self.get_stock_entries("salesinvoiceno", si.name)
		self.assertEqual(flt(se.items[0].qty), 15)
		(ledger,) = self.get_ledger(si.name)
		self.assertEqual(flt(ledger.actual_qty), 20)
		self.assertEqual(flt(ledger.empty_qty), 15)
		self.assertEqual(flt(ledger.difference_in_qty), 5)

	def test_sale_customer_drops_more_empties(self):
		si = self.make_si(self.water_jar, 20, empty_qty=22)
		(se,) = self.get_stock_entries("salesinvoiceno", si.name)
		self.assertEqual(flt(se.items[0].qty), 22)
		(ledger,) = self.get_ledger(si.name)
		self.assertEqual(flt(ledger.difference_in_qty), -2)

	def test_sale_no_empties_dropped_records_ledger_without_stock_entry(self):
		si = self.make_si(self.coke_crate, 4, empty_qty=0)
		self.assertFalse(self.get_stock_entries("salesinvoiceno", si.name))
		(ledger,) = self.get_ledger(si.name)
		self.assertEqual(flt(ledger.empty_qty), 0)
		self.assertEqual(flt(ledger.difference_in_qty), 4)

	def test_entered_empties_qty_survives_resave(self):
		si = self.make_si(self.coke_crate, 10, empty_qty=6, submit=False)
		si.reload()
		si.save()
		si.reload()
		self.assertEqual(flt(si.items[0].empty_bottle_qty), 6)
		self.assertEqual(flt(si.items[0].expected_empty_qty), 10)

	def test_uom_conversion_to_empty_stock_uom(self):
		si = create_sales_invoice(
			company=COMPANY,
			item_code=self.coke_bottle,
			qty=2,
			rate=24000,
			warehouse=WAREHOUSE,
			do_not_save=1,
		)
		row = si.items[0]
		row.uom = "Box"
		row.stock_uom = "Nos"
		row.conversion_factor = 24
		si.insert()
		si.submit()

		self.assertEqual(flt(si.items[0].stock_qty), 48)
		self.assertEqual(flt(si.items[0].expected_empty_qty), 2)
		(se,) = self.get_stock_entries("salesinvoiceno", si.name)
		se_row = se.items[0]
		self.assertEqual(se_row.item_code, self.empty_crate)
		self.assertEqual(flt(se_row.qty), 2)
		self.assertEqual(se_row.uom, frappe.get_cached_value("Item", self.empty_crate, "stock_uom"))
		self.assertEqual(flt(se_row.conversion_factor), 1)

	def test_cancel_sale_cancels_empties_stock_entry(self):
		si = self.make_si(self.coke_crate, 3)
		(se,) = self.get_stock_entries("salesinvoiceno", si.name)
		si.reload()
		si.cancel()

		se.reload()
		self.assertEqual(se.docstatus, 2)
		(ledger,) = self.get_ledger(si.name)
		self.assertEqual(ledger.is_cancelled, 1)
		self.assertEqual(ledger.status, "Cancelled")

	def test_sales_return_issues_empties_with_positive_qty(self):
		si = self.make_si(self.coke_crate, 10)
		ret = make_return_doc("Sales Invoice", si.name)
		ret.insert()
		ret.submit()

		self.assertEqual(flt(ret.items[0].expected_empty_qty), 10)
		(se,) = self.get_stock_entries("salesinvoiceno", ret.name)
		self.assertEqual(se.purpose, "Material Issue")
		self.assertEqual(flt(se.items[0].qty), 10)
		self.assertEqual(se.items[0].s_warehouse, WAREHOUSE)
		self.assertEqual(se.items[0].expense_account, self.account)
		(ledger,) = self.get_ledger(ret.name)
		self.assertEqual(flt(ledger.out_empty_qty), 10)
		self.assertEqual(flt(ledger.in_empty_qty), 0)

	def test_selling_empty_item_uses_company_cogs(self):
		self.receive_empties(self.empty_crate, 5, 500)
		si = create_sales_invoice(
			company=COMPANY,
			item_code=self.empty_crate,
			qty=2,
			rate=600,
			warehouse=WAREHOUSE,
			update_stock=1,
			uom="Nos",
			do_not_save=1,
		)
		si.items[0].expense_account = self.account
		si.insert()
		si.submit()

		cogs = frappe.get_cached_value("Company", COMPANY, "default_expense_account")
		self.assertEqual(si.items[0].expense_account, cogs)
		# Update Stock already moved the empties: no extra stock entry
		self.assertFalse(self.get_stock_entries("salesinvoiceno", si.name))

	# purchases -----------------------------------------------------------------

	def make_pi(self, item_code, qty, empty_qty="unset", **kwargs):
		pi = make_purchase_invoice(
			company=COMPANY,
			item_code=item_code,
			qty=qty,
			rate=800,
			warehouse=WAREHOUSE,
			uom="Nos",
			do_not_save=1,
			**kwargs,
		)
		if empty_qty != "unset":
			pi.items[0].empty_bottle_qty = empty_qty
		pi.insert()
		pi.submit()
		return pi

	def test_purchase_issues_empties_to_supplier(self):
		self.receive_empties(self.empty_jar, 50, 300)
		pi = self.make_pi(self.water_jar, 10, empty_qty=8)

		(se,) = self.get_stock_entries("purchase_invoice_no", pi.name)
		self.assertEqual(se.purpose, "Material Issue")
		row = se.items[0]
		self.assertEqual(row.item_code, self.empty_jar)
		self.assertEqual(flt(row.qty), 8)
		self.assertEqual(row.s_warehouse, WAREHOUSE)
		self.assertEqual(row.expense_account, self.account)

		(ledger,) = self.get_ledger(pi.name)
		self.assertEqual(flt(ledger.out_empty_qty), 8)
		self.assertEqual(flt(ledger.difference_in_qty), 2)
		self.assertEqual(ledger.supplier, pi.supplier)

	def test_cancel_purchase_cancels_empties_stock_entry(self):
		self.receive_empties(self.empty_jar, 50, 300)
		pi = self.make_pi(self.water_jar, 5)
		(se,) = self.get_stock_entries("purchase_invoice_no", pi.name)
		pi.reload()
		pi.cancel()
		se.reload()
		self.assertEqual(se.docstatus, 2)
		(ledger,) = self.get_ledger(pi.name)
		self.assertEqual(ledger.is_cancelled, 1)


class TestPOSEmptyBottleEntryMeta(FrappeTestCase):
	def test_status_allows_cancelled(self):
		options = frappe.get_meta("POS Empty Bottle Entry").get_field("status").options.split("\n")
		self.assertIn("Cancelled", options)
