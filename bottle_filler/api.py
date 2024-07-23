import frappe
from frappe import _
from frappe import utils

def setup(sales_invoice, method):
    invoice_items = []
    
    for detail in sales_invoice.items:
        if hasattr(detail, 'empty_bottle_item_code') and detail.empty_bottle_item_code and not hasattr(detail, 'allow_is_pos'):
            invoice_items.append(detail)

    sales_invoice.items = invoice_items
    if invoice_items:
        make_stock_entry(sales_invoice)

def make_stock_entry(sales_invoice):
    if frappe.db.exists({'doctype': 'Stock Entry', 'salesinvoiceno': sales_invoice.name}):
        frappe.throw(
            title="Error",
            msg="Stock Entry for Invoice {} already exists.".format(sales_invoice.name)
        )

    items = []
    for detail in sales_invoice.items:
        if detail.empty_bottle_item_code:
            items.append({
                't_warehouse': detail.warehouse,
                'item_code': detail.empty_bottle_item_code,
                'qty': detail.qty,
                'transfer_qty': detail.qty,
                'uom': detail.uom,
                'stock_uom': detail.stock_uom,
                'conversion_factor': detail.conversion_factor,
                'basic_rate': float(detail.empty_bottle_rate),
                'project': detail.project,
                'cost_center': detail.cost_center
            })
    
    if not items:
        frappe.throw(
            title="Error",
            msg="No valid empty bottle items found to create Stock Entry."
        )

    se = frappe.get_doc({
        'title': "Auto Material Receipt",
        'doctype': 'Stock Entry',
        'stock_entry_type': 'Material Receipt',
        'purpose': 'Material Receipt',
        'posting_date': sales_invoice.posting_date,
        'posting_time': sales_invoice.posting_time,
        'set_posting_time': 1,
        'company': sales_invoice.company,
        'items': items,
        'remarks': 'Being Empty Entry',
        'project': sales_invoice.project,
        'salesinvoiceno': sales_invoice.name
    })

    se.insert()
    se.submit()
