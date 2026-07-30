import time

from .registry import registry


def main() -> None:
    if not registry.BOT_TOKEN:
        raise SystemExit(
            "BOT_TOKEN env var is empty. Run with: BOT_TOKEN=... python waste_syndicate_bot.py"
        )
    registry.load_texts()
    registry.load_game()
    print("🛢️  سندیکای دلالان زباله v4 — SEASONAL LOCAL KEYPAD")
    registry.game["next_offset_id"] = registry.load_offset()
    if registry.SKIP_PENDING_ON_START:
        registry.skip_old_updates()
        registry.game["next_offset_id"] = registry.load_offset()
    if registry.BOT_TOKEN == "PUT_YOUR_RUBIKA_BOT_TOKEN_HERE":
        print(
            "⚠️ BOT_TOKEN is not set. Edit the file or run: BOT_TOKEN=... python waste_syndicate_bot_v4_seasonal.py"
        )
    me = registry.api("getMe")
    print("[getMe RAW]", me)
    bot = me.get("bot", {})
    print(f"   Bot: @{bot.get('username', '?')} | {bot.get('bot_title', '?')}")
    while True:
        try:
            registry.maybe_roll_season()
            registry.award_territory_daily()
            registry.maybe_system_daily_restock()
            registry.maybe_daily_event()
            registry.maybe_spawn_boss(False)
            registry.periodic_group_radio()
            payload = {"limit": 30}
            if registry.game.get("next_offset_id"):
                payload["offset_id"] = registry.game["next_offset_id"]
            resp = registry.api("getUpdates", payload)
            if registry.DEBUG:
                print("[getUpdates RAW]", resp)
            next_offset = resp.get("next_offset_id")
            if next_offset:
                registry.game["next_offset_id"] = next_offset
                registry.save_offset(next_offset)
            for raw_upd in resp.get("updates", []):
                registry.process_update(raw_upd)
            registry.save_game()
            time.sleep(registry.POLL_INTERVAL)
        except KeyboardInterrupt:
            registry.save_game()
            print("\nBot stopped.")
            break
        except Exception as e:
            print("[LOOP]", repr(e))
            time.sleep(registry.POLL_INTERVAL)


registry.main = main
if __name__ == "__main__":
    registry.main()
