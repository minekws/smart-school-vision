from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

from services.file_service import read_json_safe
from utils.paths import day_dir, days_dir

logger = logging.getLogger("smartschool.stats")

EMOTION_LABELS = {
    "happy": "Радость",
    "neutral": "Нейтрально",
    "sad": "Грусть",
    "angry": "Злость",
    "surprised": "Удивление",
    "fear": "Страх",
}

DAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт"]


async def build_weekly_charts(camera_id: str) -> Dict[str, Any]:
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = min(today, week_start + timedelta(days=4))

    late_by_day = {d: {"on_time": 0, "late": 0} for d in DAY_NAMES}
    flicker_daily: Dict[str, Dict] = {}
    flicker_total = {"with": 0, "without": 0}
    emotions_total: Dict[str, int] = {}
    emotion_daily_average: Dict[str, float] = {}

    safety_slots = {
        "07:30-08:00": {"with_flicker": 0, "without_flicker": 0},
        "08:00-08:30": {"with_flicker": 0, "without_flicker": 0},
        "08:30-09:00": {"with_flicker": 0, "without_flicker": 0},
        "После 09:00": {"with_flicker": 0, "without_flicker": 0},
    }

    current = week_start
    while current <= week_end:
        date_str = current.isoformat()
        static_path = day_dir(camera_id, date_str) / "static.json"
        day_data = await read_json_safe(static_path)

        if day_data and isinstance(day_data, dict):
            _process_day(
                day_data, current, date_str,
                late_by_day, flicker_daily, flicker_total,
                emotions_total, emotion_daily_average, safety_slots,
                camera_id,
            )
        current += timedelta(days=1)

    return _assemble_charts(
        late_by_day, flicker_daily, flicker_total,
        emotions_total, emotion_daily_average, safety_slots,
        camera_id, week_start, week_end,
    )


def _process_day(
    day_data, current, date_str,
    late_by_day, flicker_daily, flicker_total,
    emotions_total, emotion_daily_average, safety_slots,
    camera_id,
):
    if current.weekday() < 5:
        day_name = DAY_NAMES[current.weekday()]
        late = day_data.get("opoz_total", 0)
        total = day_data.get("person_total", 0)
        late_by_day[day_name]["late"] += late
        late_by_day[day_name]["on_time"] += max(0, total - late)

    flicker = day_data.get("flicker_total", 0)
    total = day_data.get("person_total", 0)
    no_flicker = max(0, total - flicker)
    day_label = current.strftime("%d.%m")

    flicker_daily[day_label] = {
        "with": flicker,
        "without": no_flicker,
        "percentage": round(flicker / total * 100 if total else 0, 1),
    }
    flicker_total["with"] += flicker
    flicker_total["without"] += no_flicker

    emotion_stats = day_data.get("emotion_stats", {})
    for emotion, count in emotion_stats.items():
        emotions_total[emotion] = emotions_total.get(emotion, 0) + count

    if total > 0:
        pos = emotion_stats.get("happy", 0) + emotion_stats.get("surprised", 0)
        neg = (
            emotion_stats.get("sad", 0)
            + emotion_stats.get("angry", 0)
            + emotion_stats.get("fear", 0)
        )
        idx = round(50 + (pos / total * 50) - (neg / total * 50), 1)
        emotion_daily_average[day_label] = idx


def _time_slot(hour: int, minute: int) -> str:
    if hour < 8:
        return "07:30-08:00"
    if hour == 8 and minute < 30:
        return "08:00-08:30"
    if hour == 8 or (hour == 9 and minute == 0):
        return "08:30-09:00"
    return "После 09:00"


def _assemble_charts(
    late_by_day, flicker_daily, flicker_total,
    emotions_total, emotion_daily_average, safety_slots,
    camera_id, start_date, end_date,
) -> Dict[str, Any]:

    sorted_emotions = sorted(emotions_total.items(), key=lambda x: x[1], reverse=True)
    ft = flicker_total["with"] + flicker_total["without"]
    total_late = sum(d["late"] for d in late_by_day.values())

    return {
        "charts": {
            "late_by_weekday": {
                "type": "column",
                "title": "Статистика опозданий по дням недели",
                "categories": list(late_by_day.keys()),
                "series": [
                    {"name": "Вовремя", "data": [d["on_time"] for d in late_by_day.values()]},
                    {"name": "Опоздали", "data": [d["late"] for d in late_by_day.values()]},
                ],
            },
            "flicker_pie": {
                "type": "pie",
                "title": "Наличие светоотражающих элементов",
                "data": [
                    {"name": "Со светоотражателем", "value": flicker_total["with"]},
                    {"name": "Без светоотражателя", "value": flicker_total["without"]},
                ],
                "percentage": round(flicker_total["with"] / ft * 100 if ft else 0, 1),
            },
            "flicker_dynamics": {
                "type": "line",
                "title": "Динамика использования светоотражателей (%)",
                "categories": list(flicker_daily.keys()),
                "series": [
                    {
                        "name": "Процент со светоотражателями",
                        "data": [d["percentage"] for d in flicker_daily.values()],
                    }
                ],
                "y_axis": {"min": 0, "max": 100, "suffix": "%"},
            },
            "emotional_climate": {
                "type": "bar_horizontal",
                "title": "Эмоциональный климат (Пн–Пт)",
                "categories": [EMOTION_LABELS.get(e, e) for e, _ in sorted_emotions],
                "series": [{"name": "Количество", "data": [c for _, c in sorted_emotions]}],
            },
            "emotion_index": {
                "type": "area",
                "title": "Индекс эмоционального состояния",
                "categories": list(emotion_daily_average.keys()),
                "series": [
                    {"name": "Эмоциональный индекс", "data": list(emotion_daily_average.values())}
                ],
                "y_axis": {"min": 0, "max": 100},
            },
            "safety_time_correlation": {
                "type": "column",
                "title": "Время прибытия vs светоотражатели",
                "categories": list(safety_slots.keys()),
                "series": [
                    {"name": "Со светоотражателем", "data": [s["with_flicker"] for s in safety_slots.values()]},
                    {"name": "Без светоотражателя", "data": [s["without_flicker"] for s in safety_slots.values()]},
                ],
                "stacked": True,
            },
            "summary_stats": {
                "total_students": ft,
                "total_late": total_late,
                "late_percentage": round(total_late / ft * 100 if ft else 0, 1),
                "flicker_percentage": round(flicker_total["with"] / ft * 100 if ft else 0, 1),
                "average_emotion_index": round(
                    sum(emotion_daily_average.values()) / len(emotion_daily_average)
                    if emotion_daily_average
                    else 50,
                    1,
                ),
                "most_common_emotion": sorted_emotions[0][0] if sorted_emotions else "neutral",
            },
        },
        "metadata": {
            "camera_id": camera_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "generated_at": datetime.now().isoformat(),
        },
    }