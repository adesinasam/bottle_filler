# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "bottle_filler"
app_title = "Bottle Filler"
app_publisher = "Glistercp"
app_description = "Bottle Filler App"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "support@glistercp.com.ng"
app_license = "MIT"
required_apps = ["erpnext"]

# Includes in <head>
# ------------------

fixtures = [
	{"dt": "Workflow", "filters": [["name", "=", "POS Empty Bottle Entry"]]},
	{
		"dt": "Workflow State",
		"filters": [["name", "in", ["Pending", "Approved", "Rejected", "Draft", "Cancelled"]]],
	},
	{
		"dt": "Custom Field",
		"filters": [
			[
				"name",
				"in",
				[
					"Item-allow_in_pos",
					"Item-empties_per_stock_uom",
					"Item-empty_bottle_item",
					"Item-empty_bottle_item_name",
					"Item-has_empty_bottle",
					"Item-is_empty_bottle",
					"Purchase Invoice Item-allow_in_pos",
					"Purchase Invoice Item-empty_bottle_amount",
					"Purchase Invoice Item-empty_bottle_item_code",
					"Purchase Invoice Item-empty_bottle_item_name",
					"Purchase Invoice Item-empty_bottle_qty",
					"Purchase Invoice Item-empty_bottle_rate",
					"Purchase Invoice Item-expected_empty_qty",
					"Purchase Invoice Item-has_empty_bottle",
					"Sales Invoice Item-allow_in_pos",
					"Sales Invoice Item-empty_bottle_amount",
					"Sales Invoice Item-empty_bottle_item_code",
					"Sales Invoice Item-empty_bottle_item_name",
					"Sales Invoice Item-empty_bottle_qty",
					"Sales Invoice Item-empty_bottle_rate",
					"Sales Invoice Item-expected_empty_qty",
					"Sales Invoice Item-has_empty_bottle",
					"Stock Entry-purchase_invoice_no",
					"Stock Entry-remarks_attachment",
					"Stock Entry-salesinvoiceno",
					"Stock Entry-with_purchase",
					"Stock Entry-with_sales",
				],
			]
		],
	},
]


# include js, css files in header of desk.html
# app_include_css = "/assets/bottle_filler/css/bottle_filler.css"
# app_include_js = "/assets/bottle_filler/js/bottle_filler.js"

# include js, css files in header of web template
# web_include_css = "/assets/bottle_filler/css/bottle_filler.css"
# web_include_js = "/assets/bottle_filler/js/bottle_filler.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Sales Invoice": "public/js/doctype_plugin/sales_invoice.js",
    "Purchase Invoice": "public/js/doctype_plugin/purchase_invoice.js",
    }
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "bottle_filler.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "bottle_filler.install.before_install"
# after_migrate = "bottle_filler.setup.install.after_install"
# after_install = "bottle_filler.setup.install.after_install"
after_uninstall = "bottle_filler.setup.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "bottle_filler.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Sales Invoice": {
		"validate": "bottle_filler.bottle_filler.sinvoice.validate",
		"on_submit": "bottle_filler.bottle_filler.sinvoice.on_submit",
		"on_cancel": "bottle_filler.bottle_filler.sinvoice.on_cancel",
	},
	"Purchase Invoice": {
		"validate": "bottle_filler.bottle_filler.pinvoice.validate",
		"on_submit": "bottle_filler.bottle_filler.pinvoice.on_submit",
		"on_cancel": "bottle_filler.bottle_filler.pinvoice.on_cancel",
	},
	"Delivery Note": {
		"validate": "bottle_filler.bottle_filler.empties.validate_sold_empties",
	},
	"POS Invoice": {
		"validate": "bottle_filler.bottle_filler.empties.validate_sold_empties",
	},
	"POS Empty Bottle Entry": {
		"on_submit": "bottle_filler.bottle_filler.posempty.on_submit",
		"on_cancel": "bottle_filler.bottle_filler.posempty.on_cancel",
	},
}


# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"bottle_filler.tasks.all"
# 	],
# 	"daily": [
# 		"bottle_filler.tasks.daily"
# 	],
# 	"hourly": [
# 		"bottle_filler.tasks.hourly"
# 	],
# 	"weekly": [
# 		"bottle_filler.tasks.weekly"
# 	]
# 	"monthly": [
# 		"bottle_filler.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "bottle_filler.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "bottle_filler.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "bottle_filler.task.get_dashboard_data"
# }

