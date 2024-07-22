# -*- coding: utf-8 -*-
# Copyright (c) 2024, Adesina Akinyemi and contributors
# For license information, please see license.txt


from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, add_days


@frappe.whitelist()
def get_item_price(item_code, price_list):
    price = frappe.db.get_value("Item Price", {"item_code": item_code, "price_list": price_list}, "price_list_rate")
    return {"price_list_rate": price}