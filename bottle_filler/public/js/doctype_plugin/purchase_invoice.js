// Empties (returnable bottles / jars) on Purchase Invoice Item.
// Expected empties = |qty x conversion factor| x Item.empties_per_stock_uom,
// in the empty item's stock UOM. The user may change "Qty (Empty Bottle)"
// when the party exchanges more or fewer empties; the server keeps that value
// and sets the rate from the empty item's valuation rate.

function bottle_filler_set_expected_empties(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row.item_code) return;

	frappe.call({
		method: "bottle_filler.bottle_filler.api.get_empties_settings",
		args: { item_code: row.item_code },
		callback(r) {
			const s = r.message || {};
			if (!s.has_empty_bottle || !s.empty_bottle_item) return;
			const ratio = flt(s.empties_per_stock_uom) || 1;
			const stock_qty = Math.abs(flt(row.qty) * (flt(row.conversion_factor) || 1));
			const expected = flt(stock_qty * ratio, precision("expected_empty_qty", row));
			frappe.model.set_value(cdt, cdn, "expected_empty_qty", expected);
			frappe.model.set_value(cdt, cdn, "empty_bottle_qty", expected);
		},
	});
}

frappe.ui.form.on("Purchase Invoice Item", {
	item_code: bottle_filler_set_expected_empties,
	qty: bottle_filler_set_expected_empties,
	uom: bottle_filler_set_expected_empties,
	conversion_factor: bottle_filler_set_expected_empties,
	empty_bottle_qty(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (flt(row.empty_bottle_qty) < 0) {
			frappe.model.set_value(cdt, cdn, "empty_bottle_qty", Math.abs(flt(row.empty_bottle_qty)));
			return;
		}
		frappe.model.set_value(
			cdt,
			cdn,
			"empty_bottle_amount",
			flt(row.empty_bottle_rate) * flt(row.empty_bottle_qty)
		);
	},
});
