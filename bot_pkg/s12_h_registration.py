import re

from .registry import registry


def extract_ref_from_start(text: str) -> str | None:
    m = re.search("REF\\d{4,}", text or "", re.IGNORECASE)
    return m.group(0).upper() if m else None


registry.extract_ref_from_start = extract_ref_from_start


def normalize_unique_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


registry.normalize_unique_name = normalize_unique_name


def garage_name_exists(name: str, except_chat_id: str | None = None) -> bool:
    target = registry.normalize_unique_name(name)
    for cid, player in registry.game.get("players", {}).items():
        if except_chat_id and cid == except_chat_id:
            continue
        existing = registry.normalize_unique_name(player.get("name", ""))
        if existing == target:
            return True
    return False


registry.garage_name_exists = garage_name_exists


def is_reserved_registration_name(value: str) -> bool:
    """Prevent keypad/menu labels from being saved as garage names."""
    raw = (value or "").strip()
    norm = registry.normalize_unique_name(raw)
    button_labels = []
    try:
        button_labels = [str(v) for v in registry.TEXTS.get("buttons", {}).values()]
    except Exception:
        button_labels = []
    reserved = {"/start", "start", "شروع", "منوی اصلی", "↩️ منوی اصلی", *button_labels}
    return norm in {registry.normalize_unique_name(x) for x in reserved if x}


registry.is_reserved_registration_name = is_reserved_registration_name


def ensure_registered(chat_id: str, text: str, sender_name: str) -> bool:
    p = registry.get_player(chat_id)
    if registry.extract_ref_from_start(text):
        p["pending_referral"] = registry.extract_ref_from_start(text)
    state = registry.game.setdefault("chat_states", {}).get(chat_id, {}).get("state")
    if state == "awaiting_name":
        if registry.is_reserved_registration_name(text):
            registry.send(
                chat_id, registry.T("registration.bad_name"), remove_keypad=True
            )
            return False
        name = registry.clean_name(text, 20)
        if not name:
            registry.send(
                chat_id, registry.T("registration.bad_name"), remove_keypad=True
            )
            return False
        if registry.garage_name_exists(name, except_chat_id=chat_id):
            registry.send(
                chat_id, registry.T("registration.name_taken"), remove_keypad=True
            )
            return False
        p["name"] = name
        p["registered"] = True
        p["registered_at"] = registry.iso(registry.now())
        registry.game["chat_states"][chat_id] = {"state": "awaiting_referral_optional"}
        registry.save_game()
        registry.send(
            chat_id,
            registry.T("registration.ask_ref"),
            keypad=registry.make_keypad([[registry.B("skip")]]),
        )
        return False
    if state == "awaiting_referral_optional":
        code = text.strip()
        pending = p.get("pending_referral")
        if code != registry.B("skip") or pending:
            registry.apply_referral(chat_id, pending or code)
        p["pending_referral"] = None
        registry.game["chat_states"].pop(chat_id, None)
        registry.save_game()
        registry.send(
            chat_id,
            registry.T(
                "registration.done",
                name=p["name"],
                water=p["water"],
                scrap=p["resources"].get("scrap"),
                plastic=p["resources"].get("plastic"),
                glass=p["resources"].get("glass"),
            ),
            keypad=registry.main_keypad(chat_id),
        )
        return False
    if p.get("registered"):
        return True
    registry.game["chat_states"][chat_id] = {"state": "awaiting_name"}
    registry.save_game()
    registry.send(chat_id, registry.T("registration.ask_name"), remove_keypad=True)
    return False


registry.ensure_registered = ensure_registered


def apply_referral(chat_id: str, code: str) -> bool:
    code = (code or "").strip().upper()
    p = registry.game["players"][chat_id]
    if p.get("referral_used"):
        return False
    inviter_id = None
    for cid, op in registry.game["players"].items():
        if cid != chat_id and op.get("ref_code", "").upper() == code:
            inviter_id = cid
            break
    if not inviter_id:
        return False
    inviter = registry.game["players"][inviter_id]
    p["referral_used"] = True
    p["referred_by"] = inviter_id
    p["water"] += 500
    p["resources"]["scrap"] += 15
    p["resources"]["plastic"] += 15
    p["resources"]["glass"] += 8
    p["season_points_bonus"] += 500
    inviter["referrals_count"] = int(inviter.get("referrals_count", 0)) + 1
    inviter["water"] += 700
    inviter["resources"]["scrap"] += 20
    inviter["resources"]["copper"] += 5
    inviter["resources"]["battery"] += 1
    inviter["season_points_bonus"] += 1000
    registry.log_action(chat_id, "referral_used", {"inviter": inviter_id})
    registry.log_action(inviter_id, "referral_invited", {"new_player": chat_id})
    registry.send(
        inviter_id,
        registry.T(
            "registration.ref_ok",
            inviter=registry.display_name(inviter.get("name")),
            water=700,
        ),
        keypad=registry.main_keypad(inviter_id),
    )
    return True


registry.apply_referral = apply_referral
