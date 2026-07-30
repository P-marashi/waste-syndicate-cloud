import random
from datetime import timedelta
from typing import Any

from ..registry import registry


def is_game_group_chat(chat_id: str) -> bool:
    return bool(registry.GAME_GROUP_ID) and str(chat_id) == str(registry.GAME_GROUP_ID)


registry.is_game_group_chat = is_game_group_chat


def group_radio_is_enabled() -> bool:
    return bool(registry.GROUP_RADIO_ENABLED and registry.GAME_GROUP_ID)


registry.group_radio_is_enabled = group_radio_is_enabled


def send_group_radio(text: str, force: bool = False, reason: str = "radio") -> bool:
    """Send a cinematic public message only to the configured game group."""
    if not registry.group_radio_is_enabled():
        return False
    text = (text or "").strip()
    if not text:
        return False
    if not force:
        last = registry.fromiso(
            registry.game.get("last_group_radio_at"),
            registry.now() - timedelta(seconds=registry.GROUP_RADIO_MIN_INTERVAL + 1),
        )
        if (registry.now() - last).total_seconds() < registry.GROUP_RADIO_MIN_INTERVAL:
            return False
    registry.send(registry.GAME_GROUP_ID, text)
    registry.game["last_group_radio_at"] = registry.iso(registry.now())
    log = registry.game.setdefault("group_radio_log", [])
    log.insert(
        0, {"at": registry.iso(registry.now()), "reason": reason, "text": text[:220]}
    )
    del log[80:]
    return True


registry.send_group_radio = send_group_radio


def add_news(text: str, important: bool = False) -> None:
    item = {"at": registry.iso(registry.now()), "text": text}
    feed = registry.game.setdefault("news_feed", [])
    feed.insert(0, item)
    del feed[60:]
    if important:
        registry.send_group_radio(
            registry.T("group_radio.important_news", text=text),
            force=True,
            reason="important_news",
        )
        for cid, p in list(registry.game.get("players", {}).items()):
            if p.get("registered") and (not p.get("banned")):
                registry.send(
                    cid,
                    f"📰 خبر فوری آخرالزمان\n\n{text}",
                    keypad=registry.main_keypad(cid),
                )


registry.add_news = add_news


def group_radio_boss_status_text(boss: dict[str, Any] | None = None) -> str:
    boss = boss or registry.active_boss()
    if not boss:
        return registry.T("group_radio.no_boss")
    hp = int(boss.get("hp", 0))
    max_hp = max(1, int(boss.get("max_hp", 1)))
    hp_pct = int(hp / max_hp * 100)
    parts = boss.get("participants", {})
    top = sorted(parts.items(), key=lambda x: int(x[1].get("damage", 0)), reverse=True)[
        :3
    ]
    top_lines = (
        "\n".join(
            (
                f"{i}. {registry.player_name(cid)} — {registry.fmt_num(v.get('damage', 0))} آسیب"
                for i, (cid, v) in enumerate(top, 1)
            )
        )
        or "هنوز کسی جرئت نکرده جلو بره."
    )
    left = registry.fmt_cd(
        (
            registry.fromiso(boss.get("expires_at"), registry.now()) - registry.now()
        ).total_seconds()
    )
    return registry.T(
        "group_radio.boss_status",
        name=boss.get("name", "باس جهانی"),
        hp=registry.fmt_num(hp),
        max_hp=registry.fmt_num(max_hp),
        pct=hp_pct,
        left=left,
        top=top_lines,
    )


registry.group_radio_boss_status_text = group_radio_boss_status_text


def group_radio_leaderboard_text() -> str:
    rows = registry.ranked_players()[:3]
    if not rows:
        return registry.T("group_radio.no_players")
    top_lines = "\n".join(
        (
            f"{i}. {registry.player_name(cid)} — {registry.fmt_num(score)} امتیاز"
            for i, (cid, score) in enumerate(rows, 1)
        )
    )
    return registry.T("group_radio.leaderboard", top=top_lines)


registry.group_radio_leaderboard_text = group_radio_leaderboard_text


def group_radio_titles_text() -> str:
    today = registry.today_key()
    active_rows = []
    completed = 0
    silent = []
    for cid, p in registry.game.get("players", {}).items():
        if not p.get("registered") or p.get("banned"):
            continue
        missions = p.get("daily_missions") if p.get("mission_day") == today else []
        progress = sum(
            int(m.get("progress", 0)) for m in missions if isinstance(m, dict)
        )
        goals = sum(int(m.get("goal", 0)) for m in missions if isinstance(m, dict))
        if (
            missions
            and goals
            and all(
                int(m.get("progress", 0)) >= int(m.get("goal", 1)) for m in missions
            )
        ):
            completed += 1
        if progress > 0:
            active_rows.append((cid, progress))
        else:
            silent.append(cid)
    active_rows.sort(key=lambda x: x[1], reverse=True)
    active = (
        registry.player_name(active_rows[0][0])
        if active_rows
        else "هنوز کسی خودش رو ثابت نکرده"
    )
    sleepy = (
        registry.player_name(random.choice(silent))
        if silent
        else "امروز کسی کامل خواب نیست"
    )
    return registry.T(
        "group_radio.titles", active=active, sleepy=sleepy, completed=completed
    )


registry.group_radio_titles_text = group_radio_titles_text


def group_radio_alliance_text() -> str:
    alliances = [
        al for al in registry.game.get("alliances", {}).values() if isinstance(al, dict)
    ]
    if not alliances:
        return registry.T("group_radio.no_alliance")
    alliances.sort(
        key=lambda al: (
            int(al.get("level", 1)),
            int(al.get("vault", 0)),
            len(al.get("members", [])),
        ),
        reverse=True,
    )
    al = alliances[0]
    return registry.T(
        "group_radio.alliance",
        name=al.get("name", "بی‌نام"),
        level=registry.cartel_level(al),
        members=len(al.get("members", [])),
        vault=registry.fmt_num(al.get("vault", 0)),
    )


registry.group_radio_alliance_text = group_radio_alliance_text


def group_radio_market_text() -> str:
    today = registry.today_key()
    sold_today = 0
    open_orders = 0
    for o in registry.game.get("market_orders", []):
        if o.get("status") == "open":
            open_orders += 1
        if o.get("status") == "sold" and str(o.get("sold_at", "")).startswith(today):
            sold_today += 1
    return registry.T("group_radio.market", sold=sold_today, open=open_orders)


registry.group_radio_market_text = group_radio_market_text


def group_radio_rumor_text() -> str:
    return registry.T("group_radio.rumor")


registry.group_radio_rumor_text = group_radio_rumor_text


def group_radio_periodic_text() -> str:
    boss = registry.active_boss()
    if boss and random.random() < 0.55:
        return registry.group_radio_boss_status_text(boss)
    choices = [
        registry.group_radio_leaderboard_text,
        registry.group_radio_titles_text,
        registry.group_radio_alliance_text,
        registry.group_radio_market_text,
        registry.group_radio_rumor_text,
    ]
    return random.choice(choices)()


registry.group_radio_periodic_text = group_radio_periodic_text


def maybe_group_rank_change() -> None:
    rows = registry.ranked_players()[:2]
    if not rows:
        return
    top_id = rows[0][0]
    old_top = registry.game.get("last_group_rank1")
    if old_top and old_top != top_id:
        challenger = registry.player_name(top_id)
        fallen = (
            registry.player_name(old_top)
            if old_top in registry.game.get("players", {})
            else "نفر قبلی"
        )
        registry.send_group_radio(
            registry.T(
                "group_radio.rank_changed", challenger=challenger, fallen=fallen
            ),
            force=True,
            reason="rank_changed",
        )
    registry.game["last_group_rank1"] = top_id


registry.maybe_group_rank_change = maybe_group_rank_change


def periodic_group_radio() -> None:
    if not registry.group_radio_is_enabled():
        return
    registry.maybe_group_rank_change()
    boss = registry.active_boss()
    if boss:
        last_boss = registry.fromiso(
            registry.game.get("last_group_boss_report_at"),
            registry.now() - timedelta(seconds=registry.GROUP_BOSS_REPORT_INTERVAL + 1),
        )
        if (
            registry.now() - last_boss
        ).total_seconds() >= registry.GROUP_BOSS_REPORT_INTERVAL:
            if registry.send_group_radio(
                registry.group_radio_boss_status_text(boss),
                force=True,
                reason="boss_status",
            ):
                registry.game["last_group_boss_report_at"] = registry.iso(
                    registry.now()
                )
            return
    registry.send_group_radio(
        registry.group_radio_periodic_text(), force=False, reason="periodic"
    )


registry.periodic_group_radio = periodic_group_radio


def handle_group_message(chat_id: str, text: str, sender_id: str = "") -> None:
    """Keep the public group clean: ignore chatter, allow only admin radio commands."""
    text = (text or "").strip()
    if not text:
        return
    if not registry.is_group_admin(sender_id):
        return
    if text in ["/radio_test", "تست رادیو", "📡 تست رادیو"]:
        registry.send_group_radio(
            registry.T("group_radio.admin_test"), force=True, reason="admin_test"
        )
        return
    if text in ["/radio_status", "وضعیت رادیو", "📡 وضعیت رادیو"]:
        last = (
            registry.fmt_dt(registry.game.get("last_group_radio_at"))
            if registry.game.get("last_group_radio_at")
            else "هنوز پیامی ثبت نشده"
        )
        log_count = len(registry.game.get("group_radio_log", []))
        registry.send_group_radio(
            registry.T(
                "group_radio.admin_status",
                group=registry.GAME_GROUP_ID,
                last=last,
                count=log_count,
            ),
            force=True,
            reason="admin_status",
        )
        return
    if text.startswith("/radio "):
        msg = text[len("/radio ") :].strip()
        if msg:
            registry.send_group_radio(msg, force=True, reason="admin_manual")
        return


registry.handle_group_message = handle_group_message
