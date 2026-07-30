from typing import Any

from .registry import registry


def fmt_short_num(value: Any) -> str:
    """Readable dashboard numbers; keeps profile/market exact numbers unchanged."""
    try:
        n = int(value)
    except Exception:
        return str(value)
    sign = "-" if n < 0 else ""
    n = abs(n)
    units = [
        (1000000000000, "تریلیون"),
        (1000000000, "میلیارد"),
        (1000000, "میلیون"),
        (1000, "هزار"),
    ]
    for base, label in units:
        if n >= base:
            x = n / base
            s = f"{x:.1f}" if x < 10 else f"{x:.0f}"
            s = s.rstrip("0").rstrip(".")
            return f"{sign}{s} {label}"
    return f"{sign}{n:,}"


registry.fmt_short_num = fmt_short_num


def dashboard_cd_line(label: str, remaining: float) -> str:
    if remaining <= 0:
        return f"{label}: آماده ✅"
    return f"{label}: {registry.fmt_cd(remaining)} ⏳"


registry.dashboard_cd_line = dashboard_cd_line


def dashboard_hp_line(p: dict[str, Any]) -> str:
    hp = int(p.get("hp", 100))
    if hp <= 20:
        return f"❤️ نیروها: {hp}/100 🚨 بحرانی"
    if hp <= 45:
        return f"❤️ نیروها: {hp}/100 ⚠️ نیاز به درمان"
    if hp < 100:
        return f"❤️ نیروها: {hp}/100 🟡 زخمی"
    return "❤️ نیروها: 100/100 ✅ سالم"


registry.dashboard_hp_line = dashboard_hp_line


def dashboard_mission_line(chat_id: str) -> str:
    missions = registry.ensure_daily_missions(chat_id)
    if not missions:
        return "📜 مأموریت: امروز هنوز چیزی ثبت نشده"
    ready = sum(
        1
        for m in missions
        if int(m.get("progress", 0)) >= int(m.get("goal", 1)) and (not m.get("claimed"))
    )
    claimed = sum(1 for m in missions if m.get("claimed"))
    done = sum(
        1 for m in missions if int(m.get("progress", 0)) >= int(m.get("goal", 1))
    )
    total = len(missions)
    if ready:
        return f"📜 مأموریت: {ready} پاداش آماده دریافت 🎁"
    if claimed == total:
        return "📜 مأموریت: همه پاداش\u200cهای امروز دریافت شد ✅"
    return f"📜 مأموریت: {done}/{total} تکمیل شده"


registry.dashboard_mission_line = dashboard_mission_line


def dashboard_next_action(chat_id: str, p: dict[str, Any]) -> str:
    missions = registry.ensure_daily_missions(chat_id)
    ready = any(
        int(m.get("progress", 0)) >= int(m.get("goal", 1)) and (not m.get("claimed"))
        for m in missions
    )
    if ready:
        return "اول برو 📜 مأموریت\u200cها؛ پاداش آماده همان\u200cجا واریز می\u200cشود."
    if int(p.get("hp", 100)) <= 25:
        return "نیروهات زخمی\u200cاند؛ قبل از غارت، از 🎒 انبار یا 🛠️ کارگاه برای درمان کمک بگیر."
    if registry.cd_remaining(p, "scavenge") <= 0:
        return "بهترین حرکت الان: 🗺️ گشت\u200cزنی برای لوت سریع."
    if registry.cd_remaining(p, "raid") <= 0 and int(p.get("hp", 100)) >= 35:
        return "غارت آماده است؛ اگه ریسک می\u200cخوای برو ⚔️ غارت."
    return "فعلاً وقت اقتصاد و رشد است: ⚖️ بازار، 🛠️ کارگاه یا 🏗️ ساختمان\u200cها."


registry.dashboard_next_action = dashboard_next_action


def handle_main_menu(chat_id: str, sender_id: str = "") -> None:
    p = registry.get_player(chat_id)
    registry.passive_income(chat_id)
    finished = registry.finish_upgrades(p)
    registry.recalc_power(p)
    lv, xp, mx, label = registry.level_info(p)
    sc_cd = registry.cd_remaining(p, "scavenge")
    raid_cd = registry.cd_remaining(p, "raid")
    shield_left = registry.shield_remaining(p)
    shield_line = (
        f"🛡️ محافظ: فعال، {registry.fmt_cd(shield_left)} باقی مانده"
        if shield_left > 0
        else "🛡️ محافظ: خاموش ❌"
    )
    cache_count = int(p.get("loot_caches", 0))
    cache_line = (
        f"🎁 صندوق: {cache_count} آماده بازکردن"
        if cache_count > 0
        else "🎁 صندوق: فعلاً نداری"
    )
    upgrade_line = ""
    if finished:
        names = []
        for u in finished[:2]:
            bk = u.get("bldg")
            if bk in registry.BUILDINGS:
                names.append(
                    f"{registry.BUILDINGS[bk]['label']} سطح {u.get('to_level')}"
                )
        if names:
            more = " و ..." if len(finished) > 2 else ""
            upgrade_line = f"\n🏗️ تکمیل شد: {'، '.join(names)}{more}"
    status_lines = [
        registry.dashboard_cd_line("🗺️ گشت", sc_cd),
        registry.dashboard_cd_line("⚔️ غارت", raid_cd),
        registry.dashboard_hp_line(p),
        shield_line,
        cache_line,
        registry.dashboard_mission_line(chat_id),
    ]
    if registry.current_event():
        ev = registry.current_event()
        status_lines.append(f"🌪️ رویداد: {ev.get('title')}")
    text = (
        f"🏚️ پناهگاه مرکزی سندیکا\n━━━━━━━━━━━━\n👤 {registry.display_name(p.get('name', 'بی\u200cنام'))}\n🏷️ {label} — سطح {lv} | ⭐ {xp}/{mx}\n💧 خزانه: {registry.fmt_short_num(p.get('water', 0))} | 🎖️ افتخار: {int(p.get('honor', 0)):+d}\n⚔️ حمله: {registry.fmt_short_num(p.get('total_attack', 0))} | 🛡️ دفاع: {registry.fmt_short_num(p.get('total_defense', 0))}{upgrade_line}\n━━━━━━━━━━━━\n🚦 وضعیت الان\n"
        + "\n".join(f"• {line}" for line in status_lines)
        + f"\n━━━━━━━━━━━━\n🎯 پیشنهاد سیستم\n{registry.dashboard_next_action(chat_id, p)}\n━━━━━━━━━━━━\n🧭 مسیرها\n• اکشن: 🗺️ گشت\u200cزنی / ⚔️ غارت / 🗺️ نقشه شهر\n• اقتصاد: ⚖️ بازار / 🎒 انبار / 🎁 صندوق\u200cها\n• رشد: 🛠️ کارگاه / 🏗️ ساختمان\u200cها\n• رقابت: 🤝 اتحاد / 🏆 رتبه / ⏳ سیزن\n━━━━━━━━━━━━\n↩️ منوی اصلی، هر عملیات نیمه\u200cکاره را لغو می\u200cکند."
    )
    meta = registry.build_meta_bold(
        text, ["پناهگاه مرکزی سندیکا", "خزانه:", "افتخار:", "حمله:", "دفاع:"]
    )
    registry.save_game()
    registry.send(
        chat_id, text, keypad=registry.main_keypad(chat_id, sender_id), meta_data=meta
    )


registry.handle_main_menu = handle_main_menu


def handle_state(chat_id: str, text: str, sender_id: str = "") -> bool:
    st = registry.game.get("chat_states", {}).get(chat_id)
    if st and (text or "").strip() in registry.ux_global_nav_buttons():
        registry.clear_chat_state(chat_id)
        return False
    return registry._ux_prev_handle_state(chat_id, text, sender_id)


registry.handle_state = handle_state


def dispatch(
    chat_id: str, text: str, sender_name: str, button_id: str = "", sender_id: str = ""
) -> None:
    text = (text or button_id or "").strip()
    if not registry.game.get("players", {}).get(chat_id, {}).get("registered"):
        return registry._ux_prev_dispatch(
            chat_id, text, sender_name, button_id, sender_id
        )
    if text in {registry.B("main_menu"), "منو", "منوی اصلی", "لغو", "cancel", "Cancel"}:
        return registry.handle_main_menu(chat_id, sender_id)
    if (
        registry.game.get("chat_states", {}).get(chat_id)
        and text in registry.ux_global_nav_buttons()
    ):
        registry.clear_chat_state(chat_id)
    return registry._ux_prev_dispatch(chat_id, text, sender_name, button_id, sender_id)


registry.dispatch = dispatch
