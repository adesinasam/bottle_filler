import frappe
from frappe import _
from frappe import utils

def setup(pos_empty, method):
    """
    Setup function to filter POS Empty Bottle Entry and create stock entries for with empty bottles.
    
    Args:
        pos_empty: The POS Empty Bottle Entry document object.
        method: The method triggering this function.
    """
    make_stock_entry(pos_empty)

def make_stock_entry(pos_empty):
    """
    Creates stock entries for the POS Empty Bottle Entry with empty bottles.
    
    Args:
        pos_empty: The POS Empty Bottle Entry document object.
    """
    if pos_empty.status == "Approved":         
        stock_uom = frappe.db.get_value('Item', pos_empty.empty_item_code, 'stock_uom')   
   
        items = []

        items.append({
            't_warehouse': pos_empty.warehouse,
            'item_code': pos_empty.empty_item_code,
            'qty': pos_empty.empty_qty,
            'transfer_qty': pos_empty.empty_qty,
            'uom': stock_uom,
            'stock_uom': stock_uom,
            'conversion_factor': 1,
            'basic_rate': float(pos_empty.empty_price),
            'cost_center': pos_empty.cost_center
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
            'posting_date': pos_empty.posting_date,
            'posting_time': pos_empty.posting_time,
            'set_posting_time': 1,
            'company': pos_empty.company,
            'items': items,
            'remarks': 'Being Empty Entry',
            'salesinvoiceno': pos_empty.voucher_no
        })

        se.insert()
        se.submit()

        try:
            # Create a new Empty Bottle Entry document
            btl = frappe.get_doc({
                'doctype': 'Empty Bottle Entry',
                'item_code': pos_empty.item_code,
                'item_name': pos_empty.item_name,
                'warehouse': pos_empty.warehouse,
                'posting_date': pos_empty.posting_date,
                'posting_time': pos_empty.posting_time,
                'empty_item_code': pos_empty.empty_item_code,
                'empty_item_name': pos_empty.empty_item_name,
                'voucher_type': 'Sales Invoice',
                'voucher_no': pos_empty.voucher_no,
                'stock_entry_no': se.name,
                'pos_empty_entry_no': pos_empty.name,
                'actual_qty': pos_empty.actual_qty,
                'in_empty_qty': pos_empty.actual_qty,
                'price': float(pos_empty.price),
                'amount': float(pos_empty.amount),
                'customer': pos_empty.customer,
                'empty_qty': pos_empty.empty_qty,
                'empty_price': float(pos_empty.empty_price),
                'empty_amount': float(pos_empty.empty_amount),
                'difference_in_qty': pos_empty.actual_qty - pos_empty.empty_qty,
                'company': pos_empty.company,
                'status': 'Submitted',
                'cost_center': pos_empty.cost_center,
                'territory': pos_empty.territory
            })
            # Insert the document into the database
            btl.insert()
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"Failed to create Empty Bottle Entry for Sales Invoice {pos_empty.voucher_no}")
            frappe.throw(_("Failed to create Empty Bottle Entry for item {}").format(pos_empty.item_name))

    elif pos_empty.docstatus == 2:
        # Fetch all Empty Bottle Entry names matching the criteria
        pr_names = frappe.get_all("Empty Bottle Entry", 
            filters={"voucher_type": 'Sales Invoice', "pos_empty_entry_no": pos_empty.name}, 
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

