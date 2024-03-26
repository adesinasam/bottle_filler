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

# Includes in <head>
# ------------------

fixtures = [{
  'dt' : 'Custom Field', 'filters':[
    [
      'name', 'in', [
        'Sales Invoice-check_in_id',
        'Sales Invoice-check_in_date',
      ]
    ]
  ]
}]

# include js, css files in header of desk.html
# app_include_css = "/assets/bottle_filler/css/bottle_filler.css"
# app_include_js = "/assets/bottle_filler/js/bottle_filler.js"

# include js, css files in header of web template
# web_include_css = "/assets/bottle_filler/css/bottle_filler.css"
# web_include_js = "/assets/bottle_filler/js/bottle_filler.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
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
# after_install = "bottle_filler.install.after_install"

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
  "Expense Entry": {
    "on_submit": "expense_journal.api.setup",
    "on_cancel": "expense_journal.apy.setup"
  },
  "Expense Entry": {
    "on_submit": "expense_journal.api.setup",
    "on_cancel": "expense_journal.apy.setup"
  }
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

