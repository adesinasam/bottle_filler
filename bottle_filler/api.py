import frappe
from frappe import _
from frappe import utils


def setup(sales_invoice, method):

    invoice_items = []
    
    for detail in sales_invoice.items:
        if hasattr(detail, 'has_empty_bottle') and not hasattr(detail, 'allow_is_pos'):
            invoice_items.append(detail)

    sales_invoice.items = invoice_items
    make_stock_entry(sales_invoice)

        # if hasattr(detail, 'has_empty_bottle') and hasattr(detail, 'allow_is_pos'):
        #     invoice_items.append(detail)

        #     sales_invoice.items = invoice_items
        #     make_pos_empty_entry(sales_invoice)


def make_stock_entry(sales_invoice):

    # if sales_invoice.docstatus == 1:         

        # check for duplicates
        if frappe.db.exists({'doctype': 'Stock Entry', 'salesinvoiceno': sales_invoice.name}):
            frappe.throw(
                title="Error",
                msg="Stock Entry for Invoice {} already exists.".format(sales_invoice.name)
            )


        # Preparing the SE: convert sales_invoice details into se items details

        items = []

        for detail in sales_invoice.items:            

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


        # create the stock entry
        se = frappe.get_doc({
            'title': "Auto Material Receipt",
            'doctype': 'Stock Entry',
            'stock_entry_type': 'Material Receipt',
            'posting_date': sales_invoice.posting_date,
            'posting_time': sales_invoice.posting_time,
            'set_posting_time': 1,
            'company': sales_invoice.company,
            'to_warehouse': sales_invoice.set_warehouse,
            'items': items,
            'remarks': 'Being Empty Entry',
            'project': sales_invoice.project,
            'salesinvoiceno': sales_invoice.name
        })


        se.insert()
        se.submit()

        # create the stock entry
        for detail in sales_invoice.items:            
            ebe = frappe.get_doc({
                'doctype': 'Empty Bottle Entry',
                'item_code': detail.item_code,
                'item_name': detail.item_name,
                'warehouse': detail.warehouse,
                'posting_date': sales_invoice.posting_date,
                'posting_time': sales_invoice.posting_time,
                'empty_item_code': detail.empty_item_code,
                'empty_item_name': detail.empty_item_name,
                'voucher_type': 'Sales Invoice',
                'voucher_no': sales_invoice.name,
                'actual_qty': detail.qty,
                'price': float(detail.rate),
                'amount': float(detail.amount),
                'customer': sales_invoice.set_warehouse,
                'empty_qty': detail.empty_bottle_qty,
                'empty_price': float(detail.empty_bottle_rate),
                'empty_amount': float(detail.empty_bottle_amount),
                'difference_in_qty': detail.qty - detail.empty_bottle_qty,
                'company': sales_invoice.company,
                'cost_center': detail.cost_center,
                'territory': sales_invoice.territory
            })


            ebe.insert()
    
    # elif sales_invoice.docstatus == 2:

    #     pr_name = frappe.db.get_value("Stock Entry",{"salesinvoiceno": sales_invoice.name}, "name")
        
    #     pr = frappe.get_doc("Stock Entry", pr_name)
    #     pr.cancel()

    #     for detail in sales_invoice.items:            
    #         ebe = frappe.get_doc({
    #             'doctype': 'Empty Bottle Entry',
    #             'is_cancelled': 1
    #         })


    #         ebe.save()
