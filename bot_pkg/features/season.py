from typing import Any

from ..registry import registry


def season_score_breakdown(chat_id: str) -> dict[str, int]:
    p = registry.game["players"][chat_id]
    registry.recalc_power(p)
    atk = int(p.get("total_attack", 0))
    dfc = int(p.get("total_defense", 0))
    balanced_power_bonus = min(atk, dfc) * 0.45
    combat = int(
        atk * 1.45
        + dfc * 1.25
        + balanced_power_bonus
        + int(p.get("stats", {}).get("raids_done", 0)) * 180
        + int(p.get("stats", {}).get("boss_damage", 0)) * 0.08
    )
    res_value = sum(
        int(p.get("resources", {}).get(r, 0)) * registry.system_reference_price(r)
        for r in registry.RESOURCES
    )
    economy = int(
        int(p.get("water", 0)) * 1.1
        + res_value * 0.28
        + int(p.get("stats", {}).get("market_sales", 0)) * 90
        + int(p.get("stats", {}).get("alliance_shared", 0)) * 70
    )
    building_levels = sum(int(v) for v in p.get("buildings", {}).values())
    stats = p.get("stats", {})
    progress = int(
        registry.cartel_score_bonus(chat_id) * 1.2
        + int(p.get("level", 1)) * 950
        + int(p.get("xp", 0)) * 18
        + building_levels * 420
        + int(stats.get("scavenge_success", 0)) * 65
        + int(stats.get("raids_done", 0)) * 95
        + int(stats.get("missions_completed", 0)) * 180
        + int(p.get("season_points_bonus", 0)) * 1.4
    )
    honor = int(p.get("honor", 0)) * 6.5
    total = max(0, combat + economy + progress + honor)
    return {
        "combat": combat,
        "economy": economy,
        "progress": progress,
        "honor": honor,
        "total": total,
    }


registry.season_score_breakdown = season_score_breakdown


def season_score(chat_id: str) -> int:
    return registry.season_score_breakdown(chat_id)["total"]


registry.season_score = season_score


def ranked_players(include_banned: bool = False) -> list[tuple[str, int]]:
    rows = [
        (cid, registry.season_score(cid))
        for cid, p in registry.game["players"].items()
        if p.get("registered") and (include_banned or not p.get("banned"))
    ]
    rows.sort(key=lambda x: x[1], reverse=True)
    return rows


registry.ranked_players = ranked_players


def season_left_text() -> str:
    end = registry.fromiso(registry.game.get("season", {}).get("end"), registry.now())
    sec = max(0, int((end - registry.now()).total_seconds()))
    d, rem = divmod(sec, 86400)
    h, rem = divmod(rem, 3600)
    m, _ = divmod(rem, 60)
    if d:
        return registry.T("season.left_days", days=d, hours=h)
    if h:
        return registry.T("season.left_hours", hours=h, minutes=m)
    return registry.T("season.left_minutes", minutes=m)


registry.season_left_text = season_left_text


def maybe_roll_season() -> None:
    season = registry.game.get("season") or registry.default_season(1)
    if registry.fromiso(season.get("end"), registry.now()) > registry.now():
        return
    rows = registry.ranked_players()
    winners_lines = []
    archive_rows = []
    top_prizes = {
        1: "👑 پادشاه زباله",
        2: "🥈 امپراتور نقره‌ای",
        3: "🥉 لرد برنزی",
        4: "قهرمان آهن",
        5: "بازمانده افسانه‌ای",
    }
    for i, (cid, score) in enumerate(rows[:10], start=1):
        p = registry.game["players"][cid]
        title = top_prizes.get(i, "مدال برتر")
        p.setdefault("season_titles", [])
        if title not in p["season_titles"]:
            p["season_titles"].append(title)
        line = f"{i}. {registry.display_name(p.get('name'))} — {registry.fmt_num(score)} امتیاز\n   🏆 {title}"
        winners_lines.append(line)
        archive_rows.append(
            {"rank": i, "chat_id": cid, "name": p.get("name"), "score": score}
        )
    old_id = int(season.get("id", 1))
    new_id = old_id + 1
    old_archive = {
        "id": old_id,
        "ended_at": registry.iso(registry.now()),
        "winners": archive_rows,
    }
    preserved: dict[str, dict[str, Any]] = {}
    for cid, p in registry.game["players"].items():
        rank = next((i for i, (x, _) in enumerate(rows, start=1) if x == cid), None)
        score = registry.season_score(cid) if p.get("registered") else 0
        np = registry.new_player(p.get("name") or "", cid)
        np["registered"] = p.get("registered", bool(p.get("name")))
        np["ref_code"] = p.get("ref_code", registry.generate_ref_code(cid))
        np["referrals_count"] = p.get("referrals_count", 0)
        np["referral_used"] = p.get("referral_used", False)
        np["referred_by"] = p.get("referred_by")
        np["career"] = p.get(
            "career", {"seasons_played": 0, "best_rank": None, "best_score": 0}
        )
        np["season_titles"] = p.get("season_titles", [])
        np["profile_frames"] = p.get("profile_frames", [])
        np["honor"] = p.get("honor", 0)
        if p.get("registered"):
            np["career"]["seasons_played"] = (
                int(np["career"].get("seasons_played", 0)) + 1
            )
            if rank and (
                np["career"].get("best_rank") is None
                or rank < np["career"].get("best_rank")
            ):
                np["career"]["best_rank"] = rank
            if score > int(np["career"].get("best_score", 0)):
                np["career"]["best_score"] = score
        preserved[cid] = np
    registry.game["players"] = preserved
    for al in registry.game.get("alliances", {}).values():
        al["vault"] = 0
        al["total_shared"] = 0
        al["level"] = 1
        al["applicants"] = []
        al["group_raid_session"] = None
        al["group_raid_cd"] = None
        al["log"] = []
        al.setdefault("resource_vault", {})
        for r in registry.RESOURCES:
            al["resource_vault"][r] = 0
        al["mission_day"] = None
        al["alliance_missions"] = []
        al["members"] = [
            cid
            for cid in al.get("members", [])
            if cid in registry.game["players"]
            and registry.game["players"][cid].get("registered")
        ]
    registry.game["market_orders"] = []
    registry.game["next_order_id"] = 1
    registry.game["world_event_active"] = None
    archives = list(season.get("archives", []))[-5:] + [old_archive]
    registry.game["season"] = registry.default_season(new_id)
    registry.game["season"]["archives"] = archives
    winners_text = "\n".join(winners_lines) or "بدون بازیکن"
    end_msg = f"🏁 پایان سیزن {old_id} — حماسه آخرالزمان\n\n🔥 برترین‌های این فصل:\n{winners_text}\n\n👑 تالار مشاهیر به‌روزرسانی شد.\n\nسیزن {new_id} آغاز شد.\nهمه از صفر شروع می‌کنند، اما نام افسانه‌ها برای همیشه باقی می‌ماند.\n\nشهر دوباره منتظر حماسه است..."
    meta = registry.build_meta_bold(
        end_msg,
        [
            f"پایان سیزن {old_id} — حماسه آخرالزمان",
            "برترین‌های این فصل:",
            "تالار مشاهیر",
            f"سیزن {new_id}",
        ],
    )
    for cid, p in registry.game["players"].items():
        if p.get("registered"):
            registry.send(
                cid, end_msg, keypad=registry.main_keypad(cid), meta_data=meta
            )
    registry.send_group_radio(end_msg, force=True, reason="season_end")
    registry.save_game()


registry.maybe_roll_season = maybe_roll_season
