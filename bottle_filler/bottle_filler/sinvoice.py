import frappe
from frappe import _
from frappe import utils

def setup(sales_invoice, method):
    """
    Setup function to filter sales invoice items and create stock entries for items with empty bottles.
    
    Args:
        sales_invoice: The Sales Invoice document object.
        method: The method triggering this function.
    
    Returns:
        The initial Sales Invoice document object.
    """
    try:
        # Lists to hold filtered items
        all_items = sales_invoice.items[:]
        invoice_items = []
        posinv_items = []

        # Filter items based on conditions
        for detail in sales_invoice.items:
            if detail.empty_bottle_item_code:
                if not detail.allow_in_pos:
                    invoice_items.append(detail)
            elif detail.allow_in_pos:
                if sales_invoice.is_pos:
                    posinv_items.append(detail)

        # Update sales invoice items based on the filters
        if invoice_items:
            sales_invoice.items = invoice_items
            make_stock_entry(sales_invoice)
    
        if posinv_items:
            sales_invoice.items = posinv_items
            make_pos_entry(sales_invoice)

        # Restore original items
        sales_invoice.items = all_items

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Error in setup function"))
        frappe.throw(_("An error occurred during setup: {0}").format(str(e)))

    # Return the initial sales invoice object
    return sales_invoice

def make_stock_entry(sales_invoice):
    """
    Creates stock entries for the items in the sales invoice with empty bottles.
    
    Args:
        sales_invoice: The Sales Invoice document object.
    """
    frappe.flags.ignore_permissions = True
    try:
        if sales_invoice.docstatus == 1:         
            if frappe.db.exists('Stock Entry', {'salesinvoiceno': sales_invoice.name}):
                frappe.throw("Stock Entry for Invoice {} already exists.".format(sales_invoice.name))

            items = []
            for detail in sales_invoice.items:
                if detail.empty_bottle_item_code:
                    if not sales_invoice.is_return and detail.empty_bottle_qty < 0:
                        frappe.throw("Empty bottle quantity must be positive number.")

                    qty = detail.empty_bottle_qty * (-1 if sales_invoice.is_return else 1)
                    # Construct the item dictionary
                    item_data = {
                        'item_code': detail.empty_bottle_item_code,
                        'qty': qty,
                        'transfer_qty': qty,
                        'uom': detail.uom,
                        'stock_uom': detail.stock_uom,
                        'conversion_factor': detail.conversion_factor,
                        'basic_rate': float(detail.empty_bottle_rate),
                        'project': detail.project,
                        'cost_center': detail.cost_center,
                        't_warehouse' if not sales_invoice.is_return else 's_warehouse': detail.warehouse,
                    }

                    # Append the item to the list
                    items.append(item_data)
            
            if not items:
                frappe.throw("No valid empty bottle items found to create Stock Entry.")

            # Create the stock entry
            se = frappe.get_doc({
                'doctype': 'Stock Entry',
                'stock_entry_type': 'Material Receipt' if not sales_invoice.is_return else 'Material Issue',
                'purpose': 'Material Receipt' if not sales_invoice.is_return else 'Material Issue',
                'posting_date': sales_invoice.posting_date,
                'posting_time': sales_invoice.posting_time,
                'set_posting_time': 1,
                'company': sales_invoice.company,
                'items': items,
                'remarks': 'Being Sales Return Empty Entry' if sales_invoice.is_return else 'Being Sales Empty Entry',
                'project': sales_invoice.project,
                'salesinvoiceno': sales_invoice.name
                })

            se.insert()
            se.submit()

            for detail in sales_invoice.items:            
                try:
                    # Create a new Empty Bottle Entry document
                    btl = frappe.get_doc({
                        'doctype': 'Empty Bottle Entry',
                        'item_code': detail.item_code,
                        'item_name': detail.item_name,
                        'warehouse': detail.warehouse,
                        'posting_date': sales_invoice.posting_date,
                        'posting_time': sales_invoice.posting_time,
                        'empty_item_code': detail.empty_bottle_item_code,
                        'empty_item_name': detail.empty_bottle_item_name,
                        'voucher_type': 'Sales Invoice',
                        'voucher_no': sales_invoice.name,
                        'stock_entry_no': se.name,
                        'actual_qty': detail.qty,
                        'in_empty_qty': detail.qty,
                        'price': float(detail.rate),
                        'amount': float(detail.amount),
                        'customer': sales_invoice.customer,
                        'empty_qty': detail.empty_bottle_qty if not sales_invoice.is_return else (detail.empty_bottle_qty * -1),
                        'empty_price': float(detail.empty_bottle_rate),
                        'empty_amount': float(detail.empty_bottle_amount),
                        'difference_in_qty': detail.qty - (detail.empty_bottle_qty),
                        'company': sales_invoice.company,
                        'status': 'Submitted',
                        'cost_center': detail.cost_center,
                        'territory': sales_invoice.territory
                    })
                    # Insert the document into the database
                    btl.insert()
                except Exception as e:
                    frappe.log_error(frappe.get_traceback(), f"Failed to create Empty Bottle Entry for Sales Invoice {sales_invoice.name}")
                    frappe.throw(_("Failed to create Empty Bottle Entry for item {0}: {1}").format(detail.item_code, str(e)))

        elif sales_invoice.docstatus == 2:
            cancel_empty_bottle_entries(sales_invoice.name)
    finally:
        frappe.flags.ignore_permissions = False

def make_pos_entry(sales_invoice):
    """
    Creates pos empty bottle entries for the items in the sales invoice with allow empty bottles.
    
    Args:
        sales_invoice: The Sales Invoice document object.
    """
    frappe.flags.ignore_permissions = True
    try:
        if sales_invoice.docstatus == 1:         

            items = []
            for detail in sales_invoice.items:
                if detail.allow_in_pos:
                    items.append({
                        's_warehouse': detail.warehouse,
                        'item_code': detail.item_code,
                        'qty': detail.qty,
                        'transfer_qty': detail.qty,
                        'uom': detail.uom,
                        'stock_uom': detail.stock_uom,
                        'conversion_factor': detail.conversion_factor,
                        'basic_rate': float(detail.rate),
                        'project': detail.project,
                        'cost_center': detail.cost_center
                    })
            
            if not items:
                frappe.throw("No valid empty bottle items found to create Stock Entry.")

            # Create the stock entry
            se = frappe.get_doc({
                'doctype': 'Stock Entry',
                'stock_entry_type': 'Material Issue',
                'purpose': 'Material Issue',
                'with_purchase': 0,
                'posting_date': sales_invoice.posting_date,
                'posting_time': sales_invoice.posting_time,
                'set_posting_time': 1,
                'company': sales_invoice.company,
                'items': items,
                'remarks': 'Being POS Empty Entry',
                'project': sales_invoice.project,
                'salesinvoiceno': sales_invoice.name
            })

            se.insert()
            se.submit()

            for detail in sales_invoice.items:            
                try:
                    # Create a new Empty Bottle Entry document
                    btl = frappe.get_doc({
                        'doctype': 'Empty Bottle Entry',
                        'item_code': detail.item_code,
                        'item_name': detail.item_name,
                        'warehouse': detail.warehouse,
                        'posting_date': sales_invoice.posting_date,
                        'posting_time': sales_invoice.posting_time,
                        'empty_item_code': detail.item_code,
                        'empty_item_name': detail.item_name,
                        'voucher_type': 'Sales Invoice',
                        'voucher_no': sales_invoice.name,
                        'stock_entry_no': se.name,
                        'actual_qty': detail.qty,
                        'out_empty_qty': detail.qty,
                        'price': float(detail.rate),
                        'amount': float(detail.amount),
                        'customer': sales_invoice.customer,
                        'empty_qty': detail.qty,
                        'empty_price': float(detail.rate),
                        'empty_amount': float(detail.amount),
                        'difference_in_qty': detail.qty - detail.qty,
                        'company': sales_invoice.company,
                        'status': 'Submitted',
                        'cost_center': detail.cost_center,
                        'territory': sales_invoice.territory
                    })
                    # Insert the document into the database
                    btl.insert()
                except Exception as e:
                    frappe.log_error(frappe.get_traceback(), f"Failed to create Empty Bottle Entry for Sales Invoice {sales_invoice.name}")
                    frappe.throw(_("Failed to create Empty Bottle Entry for item {0}: {1}").format(detail.item_code, str(e)))

        elif sales_invoice.docstatus == 2:
            cancel_empty_bottle_entries(sales_invoice.name)
    finally:
        frappe.flags.ignore_permissions = False

def cancel_empty_bottle_entries(voucher_no):
    entries = frappe.get_all("Empty Bottle Entry", filters={"voucher_type": 'Sales Invoice', "voucher_no": voucher_no}, fields=["name"])
    for entry in entries:
        btl = frappe.get_doc('Empty Bottle Entry', entry.name)
        btl.db_set('status', 'Cancelled')
        btl.db_set('is_cancelled', 1)


def validate(sales_invoice, method):
    """
    Auto-fill empty_bottle_qty and enforce expense_account for POS Sales Invoices.
    Uses flags to prevent recursion.
    """
    if not sales_invoice.flags.before_save_processed and sales_invoice.is_pos:
        sales_invoice.flags.before_save_processed = True  # Anti-recursion flag
        
        default_expense_account = frappe.get_cached_value(
            "Company", 
            sales_invoice.company, 
            "default_expense_account"
        )

        for item in sales_invoice.items:
            # Case 1: Non-POS item with empty bottle - auto-fill qty
            if not item.allow_in_pos and item.empty_bottle_item_code:
                item.empty_bottle_qty = item.qty
            
            # Case 2: POS item without empty bottle - enforce expense account
            elif item.allow_in_pos and not item.empty_bottle_item_code:
                if not default_expense_account:
                    frappe.throw(
                        _("Default Expense Account not set for Company {}").format(sales_invoice.company),
                        title=_("Missing Account")
                    )
                item.expense_account = default_expense_account  # Force-set even if exists