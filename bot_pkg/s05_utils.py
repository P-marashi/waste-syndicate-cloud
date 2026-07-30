"""
Bootstrap Utility Registry.

این فایل تمام توابع کمکی پروژه را داخل `registry` ثبت می‌کند.

پس از import کردن این فایل، توابع زیر در دسترس خواهند بود:

Text
----
- build_meta_bold
- bidi
- fmt_num
- display_name
- xp_bar

Date & Time
-----------
- now
- iso
- fromiso
- today_key
- fmt_cd
- fmt_dt

Validation
----------
- safe_int
- clean_name

Resources
---------
- res_key
- amount_of
- add_amount
- pay_cost
- has_resources

Resource Formatting
-------------------
- fmt_res_amount
- fmt_res_dict
- fmt_res_lines
- fmt_res_loss
- fmt_res_shortage

Players
-------
- effective_sender_id
- is_admin
- is_group_admin
- is_banned
- ban_reason

Logging
-------
- log_action
- admin_audit

Usage
-----
from bot_pkg.utils.bootstrap import *
"""

from bot_pkg.utils.bootstrap import *
