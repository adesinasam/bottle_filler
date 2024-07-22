from __future__ import unicode_literals
import frappe


def after_install():
    set_custom_scripts()

def set_custom_scripts():
    test_script = frappe.get_value("Client Script", "Sales Invoice-Form")
    if test_script is None:
        CS = frappe.new_doc("Client Script")
        CS.set("name", "Sales Invoice-Form")
    else:
        CS = frappe.get_doc("Client Script", test_script)

    CS.set("enabled", 1)
    CS.set("view", "Form")
    CS.set("dt", "Sales Invoice")
    CS.set("script", """
frappe.ui.form.on('Sales Invoice', {
    refresh(frm) {
        //refresh
	}
});

// bottle_filler/api/sinvoice.js
frappe.ui.form.on("Sales Invoice Item", {
    empty_bottle_qty: function(frm, cdt, cdn) {
        var d = locals[cdt][cdn];

        // Validation: Check if empty_bottle_qty is not 0 and less than actual_qty if empty_bottle_item is not null
        if (d.empty_bottle_item && (d.empty_bottle_qty === 0 || d.actual_qty > 0 || d.allow_in_pos === 0)) {
            frappe.msgprint(__('Quantity(Empty) must be greater than 0 for RGB if Empty Bottle Item is specified.'));
            frappe.model.set_value(cdt, cdn, 'empty_bottle_qty', 0);
            return;
        }

        // Fetch item price and calculate empty bottle amount
        frappe.call({
            method: "bottle_filler.bottle_filler.api.sinvoice.get_item_price",
            args: {
                item_code: d.empty_bottle_item_code,
                price_list: "Standard Buying"
            },
            callback: function(r) {
                if (r.message) {
                    d.empty_bottle_rate = r.message.price_list_rate;
                    d.empty_bottle_amount = r.message.price_list_rate * d.empty_bottle_qty;
                    refresh_field("empty_bottle_rate", d.name);
                    refresh_field("empty_bottle_amount", d.name);
                }
            }
        });
    }
});"""
           )
    CS.insert() if test_script is None else CS.save()
