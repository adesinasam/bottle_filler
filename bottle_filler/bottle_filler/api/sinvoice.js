// Copyright (c) 2024 Adesina Akinyemi and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sales Invoice Item", "empty_bottle_qty", function(frm, cdt, cdn) {
    var d = locals[cdt][cdn];
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
});
