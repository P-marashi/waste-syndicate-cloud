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
        return "📜 مأموریت: همه پاداش‌های امروز دریافت شد ✅"
    return f"📜 مأموریت: {done}/{total} تکمیل شده"


registry.dashboard_mission_line = dashboard_mission_line


def dashboard_next_action(chat_id: str, p: dict[str, Any]) -> str:
    missions = registry.ensure_daily_missions(chat_id)
    ready = any(
        int(m.get("progress", 0)) >= int(m.get("goal", 1)) and (not m.get("claimed"))
        for m in missions
    )
    if ready:
        return "اول برو 📜 مأموریت‌ها؛ پاداش آماده همان‌جا واریز می‌شود."
    if int(p.get("hp", 100)) <= 25:
        return (
            "نیروهات زخمی‌اند؛ قبل از غارت، از 🎒 انبار یا 🛠️ کارگاه برای درمان کمک بگیر."
        )
    if registry.cd_remaining(p, "scavenge") <= 0:
        return "بهترین حرکت الان: 🗺️ گشت‌زنی برای لوت سریع."
    if registry.cd_remaining(p, "raid") <= 0 and int(p.get("hp", 100)) >= 35:
        return "غارت آماده است؛ اگه ریسک می‌خوای برو ⚔️ غارت."
    return "فعلاً وقت اقتصاد و رشد است: 🏪 بازار، 🛠️ کارگاه یا 🏗️ ساختمان‌ها."


registry.dashboard_next_action = dashboard_next_action


def handle_profile(chat_id: str) -> None:
    """گاراژ من / پروفایل - نمایش اطلاعات کامل بازیکن"""
    p = registry.get_player(chat_id)
    registry.passive_income(chat_id)
    finished = registry.finish_upgrades(p)
    for u in finished:
        registry.send(
            chat_id,
            registry.T(
                "buildings.finished",
                label=registry.BUILDINGS[u["bldg"]]["label"],
                level=u["to_level"],
            ),
        )
    registry.recalc_power(p)
    lv, xp, mx, label = registry.level_info(p)
    stats = p.get("stats", {})
    sh = registry.shield_remaining(p)
    shield_line = (
        registry.T("profile.shield_active", time=registry.fmt_cd(sh))
        if sh
        else registry.T("profile.shield_off")
    )
    total_sv = stats.get("scavenges", 0)
    ok_sv = stats.get("scavenge_success", 0)
    fail_sv = max(0, total_sv - ok_sv)
    rate = f"{int(ok_sv / max(1, total_sv) * 100)}%" if total_sv else "0%"
    al = p.get("alliance") or "ندارم"
    txt = registry.T(
        "profile.text",
        name=registry.display_name(p.get("name")),
        season_id=registry.game.get("season", {}).get("id", 1),
        season_left=registry.season_left_text(),
        level_label=label,
        scavenge_ready="✅" if registry.cd_remaining(p, "scavenge") == 0 else "💤",
        scavenge_cd=registry.fmt_cd(registry.cd_remaining(p, "scavenge")),
        raid_ready="✅" if registry.cd_remaining(p, "raid") == 0 else "💤",
        raid_cd=registry.fmt_cd(registry.cd_remaining(p, "raid")),
        shield_line=shield_line,
        honor=p.get("honor", 0),
        honor_title=registry.honor_title(p.get("honor", 0)),
        level=lv,
        xp=xp,
        max_xp=mx,
        xp_bar=registry.xp_bar(xp, mx),
        hp=p.get("hp", 100),
        water=p.get("water", 0),
        scrap=p["resources"].get("scrap", 0),
        plastic=p["resources"].get("plastic", 0),
        glass=p["resources"].get("glass", 0),
        battery=p["resources"].get("battery", 0),
        copper=p["resources"].get("copper", 0),
        attack=f"{p.get('total_attack', 0):,}",
        defense=f"{p.get('total_defense', 0):,}",
        power=f"{p.get('total_attack', 0) + p.get('total_defense', 0):,}",
        alliance=al,
        alliance_shared=stats.get("alliance_shared", 0),
        scavenges=total_sv,
        scavenge_success=ok_sv,
        scavenge_fail=fail_sv,
        scavenge_rate=rate,
        raids_done=stats.get("raids_done", 0),
        raids_received=stats.get("raids_received", 0),
        base_status=registry.base_status_label(p),
        upgrades=registry.profile_upgrades_text(p),
    )
    txt += "\n\n" + registry.profile_daily_missions_text(chat_id)
    meta = registry.build_meta_bold(
        txt, [(txt[:25], 25), "سطح:", "حمله:", "دفاع:", "افتخار:"]
    )
    registry.save_game()

    # Profile keypad
    kp_rows = [
        [registry.B("stats"), registry.B("achievements")],
        [registry.B("history"), registry.B("settings")],
        [registry.B("main_menu")],
    ]
    registry.send(chat_id, txt, keypad=registry.make_keypad(kp_rows), meta_data=meta)


registry.handle_profile = handle_profile


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
        status_lines.append(f"🌍 رویداد: {ev.get('title')}")
    text = (
        f"🏚️ پناهگاه مرکزی سندیکا\n━━━━━━━━━━━━\n👤 {registry.display_name(p.get('name', 'بی‌نام'))}\n🏷️ {label} — سطح {lv} | ⭐ {xp}/{mx}\n💧 خزانه: {registry.fmt_short_num(p.get('water', 0))} | 🎖️ افتخار: {int(p.get('honor', 0)):+d}\n⚔️ حمله: {registry.fmt_short_num(p.get('total_attack', 0))} | 🛡️ دفاع: {registry.fmt_short_num(p.get('total_defense', 0))}{upgrade_line}\n━━━━━━━━━━━━\n🚦 وضعیت الان\n"
        + "\n".join(f"• {line}" for line in status_lines)
        + f"\n━━━━━━━━━━━━\n🎯 پیشنهاد سیستم\n{registry.dashboard_next_action(chat_id, p)}\n━━━━━━━━━━━━\n🧭 مسیرها\n• اکشن: 🗺️ گشت‌زنی / ⚔️ غارت / 🗺️ نقشه شهر\n• اقتصاد: 🏪 بازار / 🎒 انبار / 🎁 صندوق‌ها\n• رشد: 🛠️ کارگاه / 🏗️ ساختمان‌ها\n• رقابت: 🤝 اتحاد / 📊 رتبه‌بندی / 🏆 فصل\n━━━━━━━━━━━━\n↩️ منوی اصلی، هر عملیات نیمه‌کاره را لغو می‌کند."
    )
    meta = registry.build_meta_bold(
        text, ["پناهگاه مرکزی سندیکا", "خزانه:", "افتخار:", "حمله:", "دفاع:"]
    )
    registry.save_game()
    registry.send(
        chat_id, text, keypad=registry.main_keypad(chat_id, sender_id), meta_data=meta
    )


registry.handle_main_menu = handle_main_menu


def handle_more_menu(chat_id: str) -> None:
    """منوی بیشتر - گزینه‌های اضافی"""
    rows = [
        [registry.B("daily_reward"), registry.B("help")],
        [registry.B("history"), registry.B("settings")],
        [registry.B("invite"), registry.B("enter_referral")],
        [registry.B("main_menu")],
    ]
    text = "⚙️ بیشتر...\n━━━━━━━━━━━━\nگزینه‌های اضافی:"
    registry.send(chat_id, text, keypad=registry.make_keypad(rows))


registry.handle_more_menu = handle_more_menu


# ── Settings ──


def handle_settings(chat_id: str) -> None:
    """تنظیمات - اعلان‌ها، صدا، نمایش"""
    p = registry.get_player(chat_id)
    prefs = p.setdefault("preferences", {})
    notif = prefs.get("notifications", True)
    sound = prefs.get("sound", True)
    compact = prefs.get("compact_mode", False)
    notif_status = "✅ فعال" if notif else "❌ غیرفعال"
    sound_status = "✅ فعال" if sound else "❌ غیرفعال"
    compact_status = "✅ فشرده" if compact else "❌ عادی"
    text = (
        "⚙️ تنظیمات\n"
        "━━━━━━━━━━━━\n"
        f"🔔 اعلان‌ها: {notif_status}\n"
        f"🔊 صدا: {sound_status}\n"
        f"📄 حالت نمایش: {compact_status}\n"
        "━━━━━━━━━━━━\n"
        "👇 برای تغییر هر گزینه کلیک کن:"
    )
    rows = [
        [registry.T("settings.toggle_notifications", status="🔔"), registry.T("settings.toggle_sound", status="🔊")],
        [registry.T("settings.toggle_compact", status="📄")],
        [registry.B("name_change")],
        [registry.B("main_menu")],
    ]
    registry.send(chat_id, text, keypad=registry.make_keypad(rows))


registry.handle_settings = handle_settings


# ── History ──


def handle_history(chat_id: str) -> None:
    """تاریخچه عملیات"""
    p = registry.get_player(chat_id)
    log = p.get("log", [])
    if not log:
        registry.send(
            chat_id,
            "📜 تاریخچه عملیات\n━━━━━━━━━━━━\nهنوز عملیاتی ثبت نشده.",
            keypad=registry.make_keypad([[registry.B("main_menu")]]),
        )
        return
    lines = []
    for entry in log[-20:]:
        lines.append(f"• {entry}")
    text = (
        "📜 تاریخچه عملیات\n"
        "━━━━━━━━━━━━\n"
        "آخرین عملیات‌ها:\n"
        + "\n".join(lines)
        + "\n━━━━━━━━━━━━"
    )
    registry.send(
        chat_id,
        text,
        keypad=registry.make_keypad([[registry.B("main_menu")]]),
    )


registry.handle_history = handle_history


# ── Stats ──


def handle_stats(chat_id: str) -> None:
    """آمار کامل بازیکن"""
    p = registry.get_player(chat_id)
    registry.recalc_power(p)
    stats = p.get("stats", {})
    total_sv = stats.get("scavenges", 0)
    ok_sv = stats.get("scavenge_success", 0)
    fail_sv = max(0, total_sv - ok_sv)
    rate = f"{int(ok_sv / max(1, total_sv) * 100)}%" if total_sv else "0%"
    raids_done = stats.get("raids_done", 0)
    raids_won = stats.get("raids_won", 0)
    raids_lost = max(0, raids_done - raids_won)
    raid_rate = f"{int(raids_won / max(1, raids_done) * 100)}%" if raids_done else "0%"
    defends = stats.get("defends", 0)
    defends_won = stats.get("defends_won", 0)
    defends_lost = max(0, defends - defends_won)
    defend_rate = f"{int(defends_won / max(1, defends) * 100)}%" if defends else "0%"
    crafting = stats.get("crafting_done", 0)
    water_earned = stats.get("water_earned", 0)
    water_spent = stats.get("water_spent", 0)
    market_deals = stats.get("market_deals", 0)
    market_volume = stats.get("market_volume", 0)
    alliance_shared = stats.get("alliance_shared", 0)
    honor = p.get("honor", 0)
    days_played = stats.get("days_played", 0)
    text = (
        "📊 آمار بازیکن\n"
        "━━━━━━━━━━━━\n"
        "📋 آمار کلی:\n"
        f"• 👤 روزهای بازی: {days_played}\n"
        f"• 🎖️ افتخار: {honor:+d}\n\n"
        "🗺️ گشت‌زنی:\n"
        f"• کل گشت‌ها: {total_sv}\n"
        f"• موفق: {ok_sv} | ناموفق: {fail_sv}\n"
        f"• نرخ موفقیت: {rate}\n\n"
        "⚔️ غارت:\n"
        f"• حمله‌ها: {raids_done}\n"
        f"• پیروزی: {raids_won} | شکست: {raids_lost}\n"
        f"• نرخ پیروزی: {raid_rate}\n\n"
        "🛡️ دفاع:\n"
        f"• دفاع‌ها: {defends}\n"
        f"• موفق: {defends_won} | ناموفق: {defends_lost}\n"
        f"• نرخ موفقیت: {defend_rate}\n\n"
        "🛠️ کارگاه:\n"
        f"• ساخته‌شده: {crafting} آیتم\n\n"
        "💰 اقتصاد:\n"
        f"• 💧 آب کسب‌شده: {water_earned:,}\n"
        f"• 💧 آب خرج‌شده: {water_spent:,}\n"
        f"• 🤝 سهم اتحاد: {alliance_shared:,} 💧\n"
        f"• 🏪 معاملات بازار: {market_deals} ({market_volume:,} 💧)\n"
        "━━━━━━━━━━━━\n"
    )
    registry.send(
        chat_id,
        text,
        keypad=registry.make_keypad([[registry.B("main_menu")]]),
    )


registry.handle_stats = handle_stats


# ── Achievements ──


def handle_achievements(chat_id: str) -> None:
    """افتخارات و دستاوردها"""
    p = registry.get_player(chat_id)
    honor = p.get("honor", 0)
    stats = p.get("stats", {})
    scavenges = stats.get("scavenges", 0)
    raids = stats.get("raids_done", 0)
    defends_won = stats.get("defends_won", 0)
    crafting = stats.get("crafting_done", 0)
    market_deals = stats.get("market_deals", 0)
    alliance_shared = stats.get("alliance_shared", 0)
    water_earned = stats.get("water_earned", 0)

    achievements_data = [
        ("🗺️ کاوشگر", scavenges >= 10, scavenges >= 100, scavenges),
        ("⚔️ جنگجو", raids >= 10, raids >= 100, raids),
        ("🛡️ دژ", defends_won >= 10, defends_won >= 50, defends_won),
        ("🔧 صنعتگر", crafting >= 5, crafting >= 50, crafting),
        ("💰 تاجر", market_deals >= 10, market_deals >= 100, market_deals),
        ("🤝 متحد", alliance_shared >= 1000, alliance_shared >= 10000, alliance_shared),
        ("💧 ثروتمند", water_earned >= 10000, water_earned >= 100000, water_earned),
        ("🎖️ افسر", honor >= 100, honor >= 500, honor),
    ]

    lines = []
    for label, bronze, silver, value in achievements_data:
        if silver:
            lines.append(f"{label} 🥇 — پیشرفته")
        elif bronze:
            lines.append(f"{label} 🥉 — مقدماتی")
        else:
            progress = value  # current progress
            lines.append(f"{label} ⬜ — قفل ({value:,})")

    text = (
        "🏅 افتخارات و دستاوردها\n"
        "━━━━━━━━━━━━\n"
        f"🎖️ کل افتخار: {honor:+d}\n"
        f"👑 عنوان: {registry.honor_title(honor)}\n"
        "━━━━━━━━━━━━\n"
        + "\n".join(lines)
        + "\n━━━━━━━━━━━━\n"
        "🥇 پیشرفته | 🥉 مقدماتی | ⬜ قفل"
    )
    registry.send(
        chat_id,
        text,
        keypad=registry.make_keypad([[registry.B("main_menu")]]),
    )


registry.handle_achievements = handle_achievements


# ── Player Search ──


def handle_search_player(chat_id: str, query: str) -> None:
    """جستجوی بازیکن و نمایش پروفایل"""
    target_id = registry.find_player_by_name(query)
    if not target_id:
        registry.send(
            chat_id,
            "❌ بازیکنی با این اسم پیدا نشد.",
            keypad=registry.make_keypad([[registry.B("main_menu")]]),
        )
        return
    if target_id == chat_id:
        return registry.handle_profile(chat_id)
    target = registry.game.get("players", {}).get(target_id, {})
    if not target.get("registered"):
        registry.send(
            chat_id,
            "❌ بازیکن مورد نظر ثبت‌نام نکرده.",
            keypad=registry.make_keypad([[registry.B("main_menu")]]),
        )
        return
    registry.recalc_power(target)
    lv, xp, mx, label = registry.level_info(target)
    stats = target.get("stats", {})
    total_sv = stats.get("scavenges", 0)
    ok_sv = stats.get("scavenge_success", 0)
    fail_sv = max(0, total_sv - ok_sv)
    rate = f"{int(ok_sv / max(1, total_sv) * 100)}%" if total_sv else "0%"
    raids_done = stats.get("raids_done", 0)
    defends = stats.get("defends", 0)
    honor = target.get("honor", 0)
    al = target.get("alliance") or "-"
    text = (
        f"👤 پروفایل: {registry.display_name(target.get('name', 'بی‌نام'))}\n"
        f"━━━━━━━━━━━━\n"
        f"🏷️ {label} | سطح {lv}\n"
        f"🎖️ افتخار: {honor:+d}\n"
        f"🤝 اتحاد: {al}\n"
        f"━━━━━━━━━━━━\n"
        f"⚔️ حمله: {target.get('total_attack', 0):,}"
        f" | 🛡️ دفاع: {target.get('total_defense', 0):,}\n"
        f"📊 توان کل: {target.get('total_attack', 0) + target.get('total_defense', 0):,}\n"
        f"━━━━━━━━━━━━\n"
        f"🗺️ گشت‌ها: {total_sv} ({rate} موفقیت)\n"
        f"⚔️ غارت‌ها: {raids_done} | 🛡️ دفاع‌ها: {defends}\n"
        f"━━━━━━━━━━━━\n"
    )
    registry.chat_state_repo.delete(chat_id)
    registry.send(
        chat_id,
        text,
        keypad=registry.make_keypad([[registry.B("main_menu")]]),
    )


registry.handle_search_player = handle_search_player


def handle_state(chat_id: str, text: str, sender_id: str = "") -> bool:
    st = registry.chat_state_repo.get(chat_id)
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
    if text == registry.B("more") or text == registry.B("more_menu"):
        return registry.handle_more_menu(chat_id)
    if (
        registry.chat_state_repo.get(chat_id)
        and text in registry.ux_global_nav_buttons()
    ):
        registry.clear_chat_state(chat_id)
    return registry._ux_prev_dispatch(chat_id, text, sender_name, button_id, sender_id)


registry.dispatch = dispatch
