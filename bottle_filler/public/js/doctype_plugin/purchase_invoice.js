frappe.ui.form.on('Purchase Invoice', {
    refresh(frm) {
        //refresh
    }
})

frappe.ui.form.on("Purchase Invoice Item", {
    empty_bottle_qty: function(frm, cdt, cdn) {
        var d = locals[cdt][cdn];

        // Fetch item price and calculate empty bottle amount
        frappe.call({
            method: "bottle_filler.bottle_filler.api.get_item_price",
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
})