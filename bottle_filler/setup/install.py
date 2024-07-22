from __future__ import unicode_literals
import frappe


def after_install():
    set_custom_scripts()
    set_custom_pur_scripts()

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
    },
    item_code: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if (row.has_empty_bottle && !row.allow_in_pos) {
        frappe.model.set_value(cdt, cdn, 'empty_bottle_qty', 1);
        refresh_field("empty_bottle_qty", row.name);
        }
    },
    qty: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if (row.has_empty_bottle && !row.allow_in_pos) {
        frappe.model.set_value(cdt, cdn, 'empty_bottle_qty', row.qty);
        refresh_field("empty_bottle_qty", row.name);
        }
    }
});"""
           )
    if test_script is None:
        CS.insert()
    else:
        CS.save()

def set_custom_pur_scripts():
    test_script = frappe.get_value("Client Script", "Purchase Invoice-Form")
    if test_script is None:
        CS = frappe.new_doc("Client Script")
        CS.set("name", "Purchase Invoice-Form")
    else:
        CS = frappe.get_doc("Client Script", test_script)

    CS.set("enabled", 1)
    CS.set("view", "Form")
    CS.set("dt", "Purchase Invoice")
    CS.set("script", """
frappe.ui.form.on('Purchase Invoice', {
    refresh(frm) {
        //refresh
    }
});

// bottle_filler/api/sinvoice.js
frappe.ui.form.on("Purchase Invoice Item", {
    empty_bottle_qty: function(frm, cdt, cdn) {
        var d = locals[cdt][cdn];

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
    },
    item_code: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if (row.has_empty_bottle && !row.allow_in_pos) {
        frappe.model.set_value(cdt, cdn, 'empty_bottle_qty', 1);
        refresh_field("empty_bottle_qty", row.name);
        }
    },
    qty: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if (row.has_empty_bottle && !row.allow_in_pos) {
        frappe.model.set_value(cdt, cdn, 'empty_bottle_qty', row.qty);
        refresh_field("empty_bottle_qty", row.name);
        }
    }
});"""
           )
    if test_script is None:
        CS.insert()
    else:
        CS.save()
