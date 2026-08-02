from .registry import registry


def handle_state(chat_id: str, text: str, sender_id: str = "") -> bool:
    st = registry.chat_state_repo.get(chat_id)
    if not st:
        return False
    if text == registry.B("main_menu"):
        registry.chat_state_repo.delete(chat_id)
        registry.handle_profile(chat_id)
        return True
    if text in ["/start", "شروع"]:
        registry.chat_state_repo.delete(chat_id)
        registry.handle_start(chat_id)
        return True
    if text == registry.B("back_main"):
        registry.chat_state_repo.delete(chat_id)
        registry.handle_profile(chat_id)
        return True
    if text == registry.B("back_market"):
        registry.chat_state_repo.delete(chat_id)
        registry.handle_market_menu(chat_id)
        return True
    if text == registry.B("alliance_manage"):
        registry.chat_state_repo.delete(chat_id)
        registry.handle_alliance_manage(chat_id)
        return True
    if text == registry.B("admin_panel") and registry.is_admin(chat_id, sender_id):
        registry.chat_state_repo.delete(chat_id)
        registry.handle_admin_panel(chat_id, sender_id)
        return True
    state = st.get("state")
    if str(state).startswith("awaiting_admin_") and (
        not registry.is_admin(chat_id, sender_id)
    ):
        registry.send(
            chat_id,
            registry.T("admin.not_allowed"),
            keypad=registry.main_keypad(chat_id),
        )
        return True
    if state == "awaiting_market_order":
        registry.handle_create_order(chat_id, text)
        return True
    if state == "awaiting_barter_order":
        registry.handle_create_barter(chat_id, text)
        return True
    if state == "awaiting_rental_order":
        registry.handle_create_rental(chat_id, text)
        return True
    if state == "awaiting_system_sell_qty":
        registry.handle_system_sell_qty(chat_id, text)
        return True
    if state == "awaiting_system_buy_qty":
        registry.handle_system_buy_qty(chat_id, text)
        return True
    if state == "awaiting_alliance_name":
        registry.handle_create_alliance(chat_id, text)
        return True
    if state == "awaiting_kick_member":
        registry.handle_kick_member(chat_id, text)
        return True
    if state == "awaiting_referral_code":
        registry.handle_referral_code(chat_id, text)
        return True
    if state == "awaiting_private_message_target":
        registry.handle_private_message_target(chat_id, text)
        return True
    if state == "awaiting_player_search":
        registry.handle_search_player(chat_id, text)
        return True
    if state == "awaiting_private_message_body":
        registry.handle_private_message_body(chat_id, text)
        return True
    if state == "awaiting_admin_broadcast":
        registry.handle_admin_broadcast(chat_id, text, sender_id)
        return True
    if state == "awaiting_admin_rename_player_target":
        registry.handle_admin_rename_player_target(chat_id, text, sender_id)
        return True
    if state == "awaiting_admin_rename_player_name":
        registry.handle_admin_rename_player_name(chat_id, text, sender_id)
        return True
    if state == "awaiting_admin_rename_alliance_target":
        registry.handle_admin_rename_alliance_target(chat_id, text, sender_id)
        return True
    if state == "awaiting_admin_rename_alliance_name":
        registry.handle_admin_rename_alliance_name(chat_id, text, sender_id)
        return True
    if state == "awaiting_admin_ban_target":
        registry.handle_admin_ban_target(chat_id, text, sender_id)
        return True
    if state == "awaiting_admin_ban_reason":
        registry.handle_admin_ban_reason(chat_id, text, sender_id)
        return True
    if state == "awaiting_admin_unban_target":
        registry.handle_admin_unban_target(chat_id, text, sender_id)
        return True
    if state == "awaiting_admin_penalty_target":
        registry.handle_admin_penalty_target(chat_id, text, sender_id)
        return True
    if state == "awaiting_admin_penalty_details":
        registry.handle_admin_penalty_details(chat_id, text, sender_id)
        return True
    return False


registry.handle_state = handle_state


def dispatch(
    chat_id: str, text: str, sender_name: str, button_id: str = "", sender_id: str = ""
) -> None:
    text = (text or button_id or "").strip()
    if not registry.ensure_registered(chat_id, text, sender_name):
        return
    if registry.is_banned(chat_id) and (not registry.is_admin(chat_id)):
        registry.send(
            chat_id,
            registry.T("admin.banned_blocked", reason=registry.ban_reason(chat_id)),
            keypad=registry.make_keypad([[registry.B("help")]]),
        )
        return
    registry.expire_barter_orders()
    registry.process_resource_rentals()
    if registry.handle_state(chat_id, text, sender_id):
        return
    if text == registry.B("main_menu") or text == registry.B("back_main"):
        return registry.handle_profile(chat_id)
    if text in ["/start", "start", "شروع"]:
        return registry.handle_start(chat_id, sender_name)
    # ── Profile / Garage ──
    if text == registry.B("profile") or text == registry.B("garage"):
        return registry.handle_profile(chat_id)
    # ── City Map ──
    if text == registry.B("city_map"):
        return registry.handle_city_map(chat_id)
    # ── Scavenge (Gossht) ──
    if text == registry.B("scavenge"):
        return registry.handle_scavenge_menu(chat_id)
    if registry.zone_by_label(text):
        return registry.handle_scavenge(
            chat_id, registry.zone_by_label(text) or "alley"
        )
    # ── Market ──
    if text == registry.B("market") or text == registry.B("back_market"):
        return registry.handle_market_menu(chat_id)
    if text == registry.B("market_people"):
        return registry.handle_market_people(chat_id)
    if text == registry.B("buy"):
        return registry.handle_market_people(chat_id)
    if text == registry.B("sell"):
        return registry.handle_create_order_prompt(chat_id)
    if text == registry.B("barter"):
        return registry.handle_barter_menu(chat_id)
    if text == registry.B("market_create_order"):
        return registry.handle_create_order_prompt(chat_id)
    if text == registry.B("market_my_orders"):
        return registry.handle_my_orders(chat_id)
    if text == registry.B("market_barter"):
        return registry.handle_barter_menu(chat_id)
    if text == registry.B("market_create_barter"):
        return registry.handle_create_barter_prompt(chat_id)
    if text == registry.B("market_my_barters"):
        return registry.handle_my_barters(chat_id)
    if text == registry.B("market_resource_rentals"):
        return registry.handle_resource_rentals(chat_id)
    if text == registry.B("rental_create"):
        return registry.handle_create_rental_prompt(chat_id)
    if text == registry.B("rental_my"):
        return registry.handle_my_rentals(chat_id)
    if text == registry.B("market_system_sell"):
        return registry.handle_system_sell_menu(chat_id)
    if text == registry.B("market_system_buy"):
        return registry.handle_system_buy_menu(chat_id)
    if text == registry.B("market_prices"):
        return registry.handle_market_menu(chat_id)
    if text.startswith("قبول معاوضه"):
        return registry.handle_accept_barter(chat_id, text)
    if text.startswith("لغو معاوضه"):
        return registry.handle_cancel_barter(chat_id, text)
    if text.startswith("قبول قرارداد"):
        return registry.handle_accept_rental(chat_id, text)
    if text.startswith("لغو قرارداد"):
        return registry.handle_cancel_rental(chat_id, text)
    if text.startswith("خرید #"):
        return registry.handle_buy_order(chat_id, text)
    if text.startswith("لغو #"):
        return registry.handle_cancel_order(chat_id, text)
    if registry.system_sell_resource_from_text(text):
        return registry.handle_system_sell_select(
            chat_id, registry.system_sell_resource_from_text(text) or "scrap"
        )
    if registry.system_buy_resource_from_text(text):
        return registry.handle_system_buy_select(
            chat_id, registry.system_buy_resource_from_text(text) or "scrap"
        )
    # ── Buildings ──
    if text == registry.B("buildings"):
        return registry.handle_buildings_menu(chat_id)
    if text.startswith("⬆️ ارتقا به سطح"):
        # User clicked upgrade button on building detail page
        bk = (registry.chat_state_repo.get(chat_id) or {}).get("last_building")
        if bk:
            return registry.handle_upgrade(chat_id, bk)
    if registry.building_key_from_text(text):
        bk = registry.building_key_from_text(text) or "purifier"
        return registry.handle_building_detail(chat_id, bk)
    # ── Craft ──
    if text == registry.B("craft"):
        return registry.handle_craft_menu(chat_id)
    if registry.craft_key_from_text(text):
        return registry.handle_craft(
            chat_id, registry.craft_key_from_text(text) or "shock_rifle"
        )
    # ── Attack ──
    if text == registry.B("attack"):
        return registry.handle_attack_menu(chat_id)
    bucket = registry.raid_bucket_from_text(text)
    if bucket:
        return registry.handle_random_raid(chat_id, bucket)
    if text.startswith(("حمله دقیق:", "حمله:")):
        target = registry.raid_target_from_text(text)
        return (
            registry.handle_raid(chat_id, target, precise=True)
            if target
            else registry.send(
                chat_id,
                registry.T("errors.target_not_found"),
                keypad=registry.main_keypad(chat_id),
            )
        )
    if text == registry.B("shield"):
        return registry.handle_shield(chat_id)
    if text == registry.B("shield_buy"):
        return registry.handle_buy_shield(chat_id)
    # ── Alliance ──
    if text == registry.B("alliance"):
        return registry.handle_alliance_menu(chat_id)
    if text == registry.B("alliance_group_raid"):
        return registry.handle_alliance_group_raid(chat_id)
    if text == registry.B("alliance_group_ready"):
        return registry.handle_alliance_group_ready(chat_id)
    if text == registry.B("alliance_group_start"):
        return registry.handle_alliance_group_start(chat_id)
    if text == registry.B("alliance_group_cancel"):
        return registry.handle_alliance_group_cancel(chat_id)
    if text == registry.B("alliance_create"):
        return registry.handle_create_alliance_prompt(chat_id)
    if text == registry.B("alliance_list"):
        return registry.handle_list_alliances(chat_id)
    if text.startswith("پیوستن:"):
        return registry.handle_join_alliance(chat_id, text)
    if text == registry.B("alliance_leave"):
        return registry.handle_leave_alliance(chat_id)
    if text == registry.B("alliance_manage"):
        return registry.handle_alliance_manage(chat_id)
    if text == registry.B("alliance_open_toggle"):
        return registry.handle_toggle_alliance(chat_id)
    if text == registry.B("alliance_applicants"):
        return registry.handle_applicants(chat_id)
    if text.startswith(("قبول:", "رد:")):
        return registry.handle_applicant_decision(chat_id, text)
    if text == registry.B("alliance_kick"):
        return registry.handle_kick_prompt(chat_id)
    if text == registry.B("alliance_upgrade"):
        return registry.handle_alliance_upgrade(chat_id)
    if text == registry.B("alliance_vault"):
        return registry.handle_alliance_menu(chat_id)
    if text == registry.B("alliance_members"):
        return registry.handle_alliance_members(chat_id)
    if text == registry.B("alliance_treasury"):
        return registry.handle_alliance_treasury(chat_id)
    if text == registry.B("alliance_requests"):
        return registry.handle_alliance_requests(chat_id)
    # ── Inventory ──
    if text == registry.B("inventory"):
        return registry.handle_inventory(chat_id)
    if text == registry.B("resources"):
        return registry.handle_inventory_category(chat_id, "resources")
    if text == registry.B("equipment"):
        return registry.handle_inventory_category(chat_id, "equipment")
    if text == registry.B("special_items"):
        return registry.handle_inventory_category(chat_id, "special_items")
    # ── Daily ──
    if text == registry.B("daily") or text == registry.B("daily_reward"):
        return registry.handle_daily(chat_id)
    # ── Invite ──
    if text == registry.B("invite"):
        return registry.handle_invite(chat_id)
    if text == registry.B("enter_referral"):
        return registry.handle_enter_referral(chat_id)
    # ── Season ──
    if text == registry.B("season"):
        return registry.handle_season(chat_id)
    # ── Leaderboard ──
    if text == registry.B("leaderboard"):
        return registry.handle_leaderboard(chat_id)
    # ── Events ──
    if text == registry.B("event") or text == registry.B("events"):
        return registry.handle_event(chat_id)
    # ── Stats / Achievements ──
    if text == registry.B("stats"):
        return registry.handle_stats(chat_id)
    if text == registry.B("achievements") or text == registry.B("achievements_list"):
        return registry.handle_achievements(chat_id)
    if text == registry.B("search_player"):
        p = registry.get_player(chat_id)
        registry.chat_state_repo.save(chat_id, {"state": "awaiting_player_search"})
        registry.send(
            chat_id,
            "🔍 اسم بازیکن رو بگو تا پروفایلش رو ببینم:",
            keypad=registry.make_keypad([[registry.B("main_menu")]]),
        )
        return
    if text == registry.B("world_boss"):
        return registry.handle_world_boss(chat_id)
    if text == registry.B("boss_attack"):
        return registry.handle_boss_attack(chat_id)
    # ── News ──
    if text == registry.B("news"):
        return registry.handle_news(chat_id)
    # ── Daily Missions ──
    if text == registry.B("daily_missions"):
        return registry.handle_daily_missions(chat_id)
    # ── Open Cache ──
    if text == registry.B("open_cache"):
        return registry.handle_open_cache(chat_id)
    # ── Messages ──
    if text == registry.B("messages"):
        return registry.handle_messages_menu(chat_id)
    if text == registry.B("messages_send"):
        return registry.handle_private_message_target_prompt(chat_id)
    # ── Admin ──
    if text == registry.B("admin_panel"):
        return registry.handle_admin_panel(chat_id, sender_id)
    if text == registry.B("admin_broadcast"):
        return registry.handle_admin_broadcast_prompt(chat_id, sender_id)
    if text == registry.B("admin_stats"):
        return registry.handle_admin_stats(chat_id, sender_id)
    if text == registry.B("admin_rename_player"):
        return registry.handle_admin_rename_player_prompt(chat_id, sender_id)
    if text == registry.B("admin_rename_alliance"):
        return registry.handle_admin_rename_alliance_prompt(chat_id, sender_id)
    if text == registry.B("admin_ban_player"):
        return registry.handle_admin_ban_prompt(chat_id, sender_id)
    if text == registry.B("admin_unban_player"):
        return registry.handle_admin_unban_prompt(chat_id, sender_id)
    if text == registry.B("admin_penalty_player"):
        return registry.handle_admin_penalty_prompt(chat_id, sender_id)
    if text == registry.B("admin_messages"):
        return registry.handle_admin_messages(chat_id, sender_id)
    if text == registry.B("admin_players"):
        return registry.handle_admin_players(chat_id, 1, sender_id)
    admin_players_page = registry.parse_admin_players_page(text)
    if admin_players_page is not None:
        return registry.handle_admin_players(chat_id, admin_players_page, sender_id)
    if text == registry.B("admin_alliances"):
        return registry.handle_admin_alliances(chat_id, sender_id)
    if text == registry.B("admin_market"):
        return registry.handle_admin_market(chat_id, sender_id)
    if text == registry.B("settings"):
        return registry.handle_settings(chat_id)
    if text == registry.B("history"):
        return registry.handle_history(chat_id)
    if text.startswith("🔔") or text == registry.B("settings_toggle_notifications"):
        p = registry.get_player(chat_id)
        prefs = p.setdefault("preferences", {})
        prefs["notifications"] = not prefs.get("notifications", True)
        registry.save_game()
        return registry.handle_settings(chat_id)
    if text.startswith("🔊") or text == registry.B("settings_toggle_sound"):
        p = registry.get_player(chat_id)
        prefs = p.setdefault("preferences", {})
        prefs["sound"] = not prefs.get("sound", True)
        registry.save_game()
        return registry.handle_settings(chat_id)
    if text.startswith("📄") or text == registry.B("settings_toggle_compact"):
        p = registry.get_player(chat_id)
        prefs = p.setdefault("preferences", {})
        prefs["compact_mode"] = not prefs.get("compact_mode", False)
        registry.save_game()
        return registry.handle_settings(chat_id)
    if text == registry.B("help"):
        return registry.handle_help(chat_id)
    registry.send(
        chat_id, registry.T("errors.unknown"), keypad=registry.main_keypad(chat_id)
    )
    registry.handle_start(chat_id, sender_name)


registry.dispatch = dispatch
