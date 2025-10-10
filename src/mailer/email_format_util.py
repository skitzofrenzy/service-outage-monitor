# email/email_format_util.py
def format_events_as_html(events):
    html = [
        "<h2>Scheduled Outages</h2>",
        '<table border="1" cellpadding="5" cellspacing="0">',
        "<thead><tr><th>Date</th><th>Time</th><th>Status</th><th>Location</th></tr></thead><tbody>"
    ]
    for ev in events:
        date_cell = ev.get('date_str') or ev['start'].strftime("%d/%m/%Y")
        time_cell = f"{ev['start'].strftime('%H:%M')}–{ev['end'].strftime('%H:%M')}"
        status    = ev.get('status') or ('Cancelled' if ev.get('title','').startswith('Cancelled:') else 'Active')
        location  = ev.get('location', '')
        html.append(
            "<tr>"
            f"<td>{date_cell}</td>"
            f"<td>{time_cell}</td>"
            f"<td>{status}</td>"
            f"<td>{location}</td>"
            "</tr>"
        )
    html.append("</tbody></table>")
    return "".join(html)

def format_criteria_table(blocks):
    # blocks: list of tuples (title, url, area_kws, loc_kws)
    from html import escape
    lines = [
        "<h3>Criteria used this run</h3>",
        '<table border="1" cellpadding="5" cellspacing="0">',
        "<thead><tr><th>Provider</th><th>URL</th><th>Area Keywords</th><th>Location Keywords</th></tr></thead><tbody>"
    ]
    for (title, url, area_kws, loc_kws) in blocks:
        lines.append(
            "<tr>"
            f"<td>{escape(title)}</td>"
            f"<td><a href=\"{escape(url)}\">{escape(url)}</a></td>"
            f"<td>{escape(', '.join(area_kws))}</td>"
            f"<td>{escape(', '.join(loc_kws))}</td>"
            "</tr>"
        )
    lines.append("</tbody></table>")
    return "".join(lines)
