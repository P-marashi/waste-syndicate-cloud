# جمع‌کردن تدریجی registry

این فایل چک‌لیست فاز زیرساخت + مسیر ادامه‌ست، برای وقتی این ریپو رو
دوباره باز می‌کنیم.

## چی انجام شد (infra/redis-chat-state)
- `chat_states` از `registry.game` (و از Mongo) به Redis منتقل شد —
  `bot_pkg/storage/redis_client.py` + `ChatStateRepository`.
- ۴۵ تا `save_game()` اضافی که فقط برای همین یه تغییر صدا زده می‌شدن حذف شدن.
- الگوی repository (`get`/`save`/`delete`) برای اولین بار برای یه نوع
  داده‌ی ephemeral (نه فقط Mongo-durable) استفاده شد.

## قانون از این به بعد
هیچ کد جدیدی چیزی به `registry` اضافه نمی‌کنه. تابع جدید = import مستقیم.

## فاز بعدی (به انتخاب کاربر: مارکت / ساختمان‌ها / بازیکن)
برای هر دامنه:
1. منطق خالص (بدون I/O، بدون registry) → `bot_pkg/services/<domain>_service.py`
   (خیلی از این‌ها از قبل شروع شده — `market_service.py`,
   `scavenge_service.py` و غیره).
2. CRUD روی داده‌ی ماندگار → `bot_pkg/storage/repositories/<domain>_repository.py`
   (الگوی `PlayerRepository`/`ChatStateRepository`).
3. هندلر نازک: فقط پارس پیام، صدا زدن service/repository، فرمت پیام خروجی.
4. حذف تدریجی entryهای مربوطه از `bootstrap.py`ها وقتی هندلر قدیمی
   (`sXX_h_*.py`) کامل مهاجرت کرد.

## معیار پایان کار
```
grep -rn "registry\.\w\+ = " bot_pkg/ | wc -l
```
این عدد باید هر اسپرینت کمتر بشه تا به صفر برسه.
