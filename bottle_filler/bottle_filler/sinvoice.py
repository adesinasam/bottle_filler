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
                if not detail.empty_bottle_item_code:
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
    if sales_invoice.docstatus == 1:         
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
                    'qty': detail.empty_bottle_qty if not sales_invoice.is_pos else detail.qty,
                    'transfer_qty': detail.empty_bottle_qty if not sales_invoice.is_pos else detail.qty,
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

        # Create the stock entry
        se = frappe.get_doc({
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

        for detail in sales_invoice.items:            
            if detail.empty_bottle_item_code:
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
                        'empty_qty': detail.empty_bottle_qty if not sales_invoice.is_pos else detail.qty,
                        'empty_price': float(detail.empty_bottle_rate),
                        'empty_amount': float(detail.empty_bottle_amount),
                        'difference_in_qty': detail.qty - (detail.empty_bottle_qty if not sales_invoice.is_pos else detail.qty),
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
        # Fetch all Empty Bottle Entry names matching the criteria
        pr_names = frappe.get_all("Empty Bottle Entry", 
            filters={"voucher_type": 'Sales Invoice', "voucher_no": sales_invoice.name}, 
            fields=["name"]
        )
        # Iterate over each entry and update fields
        for entry in pr_names:
            pr_name = entry.name
            if pr_name:
                # Fetch the Empty Bottle Entry document using the retrieved name
                btl = frappe.get_doc('Empty Bottle Entry', pr_name)

                # Set the stock_entry_no field and the status to 'Cancelled'
                btl.db_set('status', 'Cancelled')  # Update the status to 'Cancelled'
                btl.db_set('is_cancelled', 1)  # Mark the document as cancelled


def make_pos_entry(sales_invoice):
    """
    Creates pos empty bottle entries for the items in the sales invoice with allow empty bottles.
    
    Args:
        sales_invoice: The Sales Invoice document object.
    """
    frappe.flags.ignore_permissions = True
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
            frappe.throw(
                title="Error",
                msg="No valid empty bottle items found to create Stock Entry."
            )

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
            if detail.allow_in_pos:
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
        # Fetch all Empty Bottle Entry names matching the criteria
        pr_names = frappe.get_all("Empty Bottle Entry", 
            filters={"voucher_type": 'Sales Invoice', "voucher_no": sales_invoice.name}, 
            fields=["name"]
        )
        # Iterate over each entry and update fields
        for entry in pr_names:
            pr_name = entry.name
            if pr_name:
                # Fetch the Empty Bottle Entry document using the retrieved name
                btl = frappe.get_doc('Empty Bottle Entry', pr_name)

                # Set the stock_entry_no field and the status to 'Cancelled'
                btl.db_set('status', 'Cancelled')  # Update the status to 'Cancelled'
                btl.db_set('is_cancelled', 1)  # Mark the document as cancelled
