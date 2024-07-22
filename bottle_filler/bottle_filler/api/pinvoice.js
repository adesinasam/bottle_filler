// Copyright (c) 2024 Adesina Akinyemi and contributors
// For license information, please see license.txt

frappe.ui.form.on("Purchase Invoice Item", "empty_bottle_item_code", function(frm, cdt, cdn) {
    var d = locals[cdt][cdn];
        frappe.db.get_value("Item Price", {"item_code": d.empty_bottle_item_code, "price_list": "Standard Buying"}, "price_list_rate", function(value) {
            d.empty_bottle_rate = value.price_list_rate;
    refresh_field("empty_bottle_rate");
            d.empty_bottle_amount = value.price_list_rate;
    refresh_field("empty_bottle_amount");

        });
});

frappe.ui.form.on('Purchase Invoice Item', {
    empty_bottle_rate: function (frm, cdt, cdn) {
        var row = locals[cdt][cdn];
            frappe.model.set_value(cdt, cdn, 'empty_bottle_amount', row.empty_bottle_rate*row.qty);
    refresh_field("empty_bottle_amount");
    }
});

frappe.ui.form.on('Purchase Invoice Item', {
    qty: function (frm, cdt, cdn) {
        var row = locals[cdt][cdn];
            frappe.model.set_value(cdt, cdn, 'empty_bottle_amount', row.empty_bottle_rate*row.qty);
    refresh_field("empty_bottle_amount");
    }
});
