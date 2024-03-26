# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from frappe import _


def get_data():
    return [
        {
            "module_name": "Bottle Filler",
            "category": "Modules",
            "label": _("Bottle Filler"),
            "color": "blue",
            "icon": "octicon octicon-home",
            "type": "module",
            "onboard_present": 1
        }
    ]
