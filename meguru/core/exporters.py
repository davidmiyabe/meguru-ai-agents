"""Utilities for exporting itineraries to common formats."""

from __future__ import annotations

import textwrap
import uuid
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from typing import Iterable, List, Optional

from meguru.schemas import DayPlan, Itinerary, ItineraryEvent


def _format_dt(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _escape_ics_text(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    escaped = escaped.replace("\n", "\\n")
    return escaped


def itinerary_to_ics(itinerary: Itinerary, *, calendar_name: Optional[str] = None) -> str:
    """Serialise the itinerary to the iCalendar format."""

    lines: List[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Meguru//Trip Planner//EN",
    ]
    if calendar_name:
        lines.append(f"X-WR-CALNAME:{_escape_ics_text(calendar_name)}")
    dtstamp = _format_dt(datetime.now(timezone.utc))

    for day_index, day in enumerate(itinerary.days):
        if not isinstance(day, DayPlan):
            continue
        if not day.events:
            continue
        base_date = day.date or itinerary.start_date
        if not base_date:
            continue
        for event_index, event in enumerate(day.events):
            if not isinstance(event, ItineraryEvent):
                continue
            uid = uuid.uuid4().hex
            summary_parts: List[str] = []
            if event.place and event.place.name:
                summary_parts.append(event.place.name)
            if event.title and event.title not in summary_parts:
                summary_parts.append(event.title)
            summary = summary_parts[0] if summary_parts else event.title or "Activity"
            start_dt = (
                datetime.combine(base_date, event.start_time)
                if event.start_time
                else None
            )
            end_dt = (
                datetime.combine(base_date, event.end_time) if event.end_time else None
            )
            duration_delta = (
                timedelta(minutes=event.duration_minutes)
                if event.duration_minutes
                else None
            )
            if start_dt and not end_dt and duration_delta:
                end_dt = start_dt + duration_delta
            elif end_dt and not start_dt and duration_delta:
                start_dt = end_dt - duration_delta
            if not start_dt and not end_dt:
                start_dt = datetime.combine(base_date, datetime.min.time())
                end_dt = start_dt + timedelta(hours=1)
            elif start_dt and not end_dt:
                end_dt = start_dt + (duration_delta or timedelta(hours=1))
            elif end_dt and not start_dt:
                start_dt = end_dt - (duration_delta or timedelta(hours=1))

            lines.append("BEGIN:VEVENT")
            lines.append(f"UID:{uid}@meguru.ai")
            lines.append(f"DTSTAMP:{dtstamp}")
            if start_dt:
                lines.append(f"DTSTART:{_format_dt(start_dt)}")
            if end_dt:
                lines.append(f"DTEND:{_format_dt(end_dt)}")
            lines.append(f"SUMMARY:{_escape_ics_text(summary)}")
            description_parts: List[str] = []
            if event.description:
                description_parts.append(event.description)
            if event.justification:
                description_parts.append(event.justification)
            if event.duration_minutes and not event.end_time:
                description_parts.append(
                    f"Estimated duration: {event.duration_minutes} minutes"
                )
            if description_parts:
                lines.append(
                    f"DESCRIPTION:{_escape_ics_text(' '.join(description_parts))}"
                )
            if event.place and event.place.formatted_address:
                lines.append(f"LOCATION:{_escape_ics_text(event.place.formatted_address)}")
            lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap_lines(text: str, width: int) -> Iterable[str]:
    for line in text.splitlines():
        yield from textwrap.wrap(line, width=width) or [""]


def itinerary_to_pdf(itinerary: Itinerary) -> bytes:
    """Render a very small PDF document summarising the itinerary."""

    buffer = BytesIO()
    objects: List[bytes] = []

    def add_object(payload: bytes) -> int:
        objects.append(payload)
        return len(objects)

    # Page content
    content_lines: List[str] = []
    cursor_y = 770
    line_height = 14

    def write_line(text: str, *, bold: bool = False) -> None:
        nonlocal cursor_y
        font = "F2" if bold else "F1"
        content_lines.append(f"BT /{font} 12 Tf 72 {cursor_y} Td ({_pdf_escape(text)}) Tj ET")
        cursor_y -= line_height

    title = itinerary.destination or "Trip Itinerary"
    write_line(title, bold=True)
    if itinerary.start_date and itinerary.end_date:
        write_line(
            f"{itinerary.start_date.strftime('%b %d, %Y')} – {itinerary.end_date.strftime('%b %d, %Y')}",
            bold=False,
        )
    if itinerary.notes:
        for wrapped in _wrap_lines(itinerary.notes, 90):
            write_line(wrapped)
        cursor_y -= line_height // 2

    for day in itinerary.days:
        label_parts: List[str] = []
        if day.label:
            label_parts.append(day.label)
        if day.date:
            label_parts.append(day.date.strftime("%A %d %B"))
        write_line(" ".join(label_parts) or "Day", bold=True)
        if day.summary:
            for wrapped in _wrap_lines(day.summary, 90):
                write_line(f"  {wrapped}")
        for event in day.events:
            computed_end = event.end_time
            if (
                event.start_time
                and not computed_end
                and event.duration_minutes
            ):
                base = datetime.combine(date.today(), event.start_time)
                computed_end = (base + timedelta(minutes=event.duration_minutes)).time()
            time_range: List[str] = []
            if event.start_time:
                time_range.append(event.start_time.strftime("%H:%M"))
            if computed_end:
                time_range.append(computed_end.strftime("%H:%M"))
            range_text = "-".join(time_range)
            if not range_text and event.duration_minutes:
                range_text = f"~{event.duration_minutes} min"
            elif (
                event.start_time
                and event.duration_minutes
                and not event.end_time
            ):
                range_text = (
                    f"{event.start_time.strftime('%H:%M')} "
                    f"({event.duration_minutes} min)"
                )
            label_parts = []
            if event.place and event.place.name:
                label_parts.append(event.place.name)
            if event.title and event.title not in label_parts:
                label_parts.append(event.title)
            header = "  "
            if range_text:
                header += f"[{range_text}] "
            header += " - ".join(label_parts) if label_parts else event.title or "Activity"
            write_line(header)
            if event.description:
                for wrapped in _wrap_lines(event.description, 84):
                    write_line(f"    {wrapped}")
            if event.location:
                write_line(f"    {event.location}")
            if event.place and event.place.formatted_address:
                write_line(f"    {event.place.formatted_address}")
            if event.justification:
                for wrapped in _wrap_lines(event.justification, 84):
                    write_line(f"    {wrapped}")
            if event.duration_minutes:
                write_line(f"    Estimated duration: {event.duration_minutes} min")
        cursor_y -= line_height // 2

    content_stream = "\n".join(content_lines).encode("utf-8")
    contents_obj_index = add_object(
        f"<< /Length {len(content_stream)} >>\nstream\n".encode("utf-8") + content_stream + b"\nendstream"
    )

    # Fonts
    font_regular_index = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Name /F1 >>")
    font_bold_index = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Name /F2 >>")

    # Page
    page_obj_index = add_object(
        f"<< /Type /Page /Parent 1 0 R /MediaBox [0 0 612 792] /Contents {contents_obj_index} 0 R /Resources << /Font << /F1 {font_regular_index} 0 R /F2 {font_bold_index} 0 R >> >> >>".encode(
            "utf-8"
        )
    )

    # Pages
    pages_obj_index = add_object(f"<< /Type /Pages /Count 1 /Kids [{page_obj_index} 0 R] >>".encode("utf-8"))

    # Catalog
    catalog_index = add_object(f"<< /Type /Catalog /Pages {pages_obj_index} 0 R >>".encode("utf-8"))

    # Serialize PDF
    buffer.write(b"%PDF-1.4\n")
    offsets: List[int] = [0]
    for index, payload in enumerate(objects, start=1):
        offsets.append(buffer.tell())
        buffer.write(f"{index} 0 obj\n".encode("utf-8"))
        buffer.write(payload)
        buffer.write(b"\nendobj\n")
    xref_position = buffer.tell()
    buffer.write(f"xref\n0 {len(objects) + 1}\n".encode("utf-8"))
    buffer.write(b"0000000000 65535 f \n")
    cursor = len(objects)
    for idx in range(cursor):
        offset = offsets[idx + 1]
        buffer.write(f"{offset:010d} 00000 n \n".encode("utf-8"))
    buffer.write(b"trailer\n")
    buffer.write(f"<< /Size {len(objects) + 1} /Root {catalog_index} 0 R >>\n".encode("utf-8"))
    buffer.write(f"startxref\n{xref_position}\n%%EOF".encode("utf-8"))
    return buffer.getvalue()


__all__ = ["itinerary_to_ics", "itinerary_to_pdf"]

