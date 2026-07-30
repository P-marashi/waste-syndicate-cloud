from bot_pkg.registry import registry

from .datetime import fmt_cd, fmt_dt, fromiso, iso, now, today_key
from .logger import admin_audit, log_action
from .players import (
    ban_reason,
    effective_sender_id,
    is_admin,
    is_banned,
    is_group_admin,
)
from .resources import (
    add_amount,
    amount_of,
    fmt_res_amount,
    fmt_res_dict,
    fmt_res_lines,
    fmt_res_loss,
    fmt_res_shortage,
    has_resources,
    pay_cost,
    res_key,
)
from .text import bidi, build_meta_bold, display_name, fmt_num, xp_bar
from .validation import clean_name, safe_int

registry.build_meta_bold = build_meta_bold

registry.now = now
registry.iso = iso
registry.fromiso = fromiso
registry.today_key = today_key
registry.fmt_cd = fmt_cd
registry.fmt_dt = fmt_dt

registry.bidi = bidi
registry.fmt_num = fmt_num
registry.display_name = display_name
registry.xp_bar = xp_bar

registry.safe_int = safe_int
registry.clean_name = clean_name

registry.res_key = res_key
registry.amount_of = amount_of
registry.add_amount = add_amount
registry.pay_cost = pay_cost
registry.fmt_res_amount = fmt_res_amount
registry.fmt_res_dict = fmt_res_dict
registry.fmt_res_lines = fmt_res_lines
registry.fmt_res_loss = fmt_res_loss
registry.fmt_res_shortage = fmt_res_shortage
registry.has_resources = has_resources

registry.effective_sender_id = effective_sender_id
registry.is_admin = is_admin
registry.is_group_admin = is_group_admin
registry.is_banned = is_banned
registry.ban_reason = ban_reason

registry.log_action = log_action
registry.admin_audit = admin_audit
