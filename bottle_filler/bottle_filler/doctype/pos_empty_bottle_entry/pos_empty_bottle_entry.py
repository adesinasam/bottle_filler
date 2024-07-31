# Copyright (c) 2024, Glistercp and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

class POSEmptyBottleEntry(Document):
    def on_cancel(self):
        self.status = "Cancelled"
        self.is_cancelled = 1

        self.db_set('status', 'Cancelled')
        self.db_set('is_cancelled', 1)
