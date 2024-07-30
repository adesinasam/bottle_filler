import frappe
from frappe import _
from frappe import utils

def setup(purchase_invoice, method):
    """
    Setup function to filter purchase invoice items and create stock entries for items with empty bottles.
    
    Args:
        purchase_invoice: The Purchase Invoice document object.
        method: The method triggering this function.
    
    Returns:
        The initial Purchase Invoice document object.
    """
    try:
        # Lists to hold filtered items
        all_items = purchase_invoice.items[:]
        invoice_items = []

        # Filter items based on conditions
        for detail in purchase_invoice.items:
            if detail.empty_bottle_item_code:
                if detail.empty_bottle_qty > 0:
                    invoice_items.append(detail)

        # Update purchase invoice items based on the filters
        if invoice_items:
            purchase_invoice.items = invoice_items
            make_stock_entry(purchase_invoice)
    
        # Restore original items
        purchase_invoice.items = all_items

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Error in setup function"))
        frappe.throw(_("An error occurred during setup: {0}").format(str(e)))

    # Return the initial purchase invoice object
    return purchase_invoice

def make_stock_entry(purchase_invoice):
    """
    Creates stock entries for the items in the purchase invoice with empty bottles.
    
    Args:
        purchase_invoice: The Purchase Invoice document object.
    """
    if purchase_invoice.docstatus == 1:         
        if frappe.db.exists({'doctype': 'Stock Entry', 'purchase_invoice_no': purchase_invoice.name}):
            frappe.throw(
                title="Error",
                msg="Stock Entry for Invoice {} already exists.".format(purchase_invoice.name)
            )

        items = []
        for detail in purchase_invoice.items:
            if detail.empty_bottle_item_code:
                items.append({
                    's_warehouse': detail.warehouse,
                    'item_code': detail.empty_bottle_item_code,
                    'qty': detail.empty_bottle_qty,
                    'transfer_qty': detail.empty_bottle_qty,
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
            'stock_entry_type': 'Material Issue',
            'purpose': 'Material Issue',
            'posting_date': purchase_invoice.posting_date,
            'posting_time': purchase_invoice.posting_time,
            'set_posting_time': 1,
            'company': purchase_invoice.company,
            'items': items,
            'remarks': 'Being Empty Entry',
            'project': purchase_invoice.project,
            'purchase_invoice_no': purchase_invoice.name
        })

        se.insert()
        se.submit()

        for detail in purchase_invoice.items:            
            if detail.empty_bottle_item_code:
                try:
                    # Create a new Empty Bottle Entry document
                    btl = frappe.get_doc({
                        'doctype': 'Empty Bottle Entry',
                        'item_code': detail.item_code,
                        'item_name': detail.item_name,
                        'warehouse': detail.warehouse,
                        'posting_date': purchase_invoice.posting_date,
                        'posting_time': purchase_invoice.posting_time,
                        'empty_item_code': detail.empty_bottle_item_code,
                        'empty_item_name': detail.empty_bottle_item_name,
                        'voucher_type': 'Purchase Invoice',
                        'voucher_no': purchase_invoice.name,
                        'stock_entry_no': se.name,
                        'actual_qty': detail.qty,
                        'out_empty_qty': detail.qty,
                        'price': float(detail.rate),
                        'amount': float(detail.amount),
                        'supplier': purchase_invoice.supplier,
                        'empty_qty': detail.empty_bottle_qty,
                        'empty_price': float(detail.empty_bottle_rate),
                        'empty_amount': float(detail.empty_bottle_amount),
                        'difference_in_qty': detail.qty - detail.empty_bottle_qty,
                        'company': purchase_invoice.company,
                        'status': 'Submitted',
                        'cost_center': detail.cost_center
                    })
                    # Insert the document into the database
                    btl.insert()
                except Exception as e:
                    frappe.log_error(frappe.get_traceback(), f"Failed to create Empty Bottle Entry for Purchase Invoice {purchase_invoice.name}")
                    frappe.throw(_("Failed to create Empty Bottle Entry for item {0}: {1}").format(detail.item_code, str(e)))

    elif purchase_invoice.docstatus == 2:
        # Fetch all Empty Bottle Entry names matching the criteria
        pr_names = frappe.get_all("Empty Bottle Entry", 
            filters={"voucher_type": 'Purchase Invoice', "voucher_no": purchase_invoice.name}, 
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
