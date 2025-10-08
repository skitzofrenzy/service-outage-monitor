# email_format_util.py
def format_events_as_html(events):
    html = [
        "<html><body>",
        "<h2>Scheduled Outages</h2>",
        '<table border="1" cellpadding="5" cellspacing="0">',
        "<thead><tr>"
        "<th>Date</th><th>Time</th><th>Status</th><th>Location</th>"
        "</tr></thead><tbody>"
    ]

    for ev in events:
        date_cell = ev.get('date_str') or ev['start'].strftime("%d/%m/%Y")
        time_cell = f"{ev['start'].strftime('%H:%M')}–{ev['end'].strftime('%H:%M')}"
        # prefer explicit status; otherwise infer from title
        status = ev.get('status') or ('Cancelled' if ev.get('title','').startswith('Cancelled:') else 'Active')
        title = ev.get('title', '')
        location = ev.get('location', '')

        html.append(
            "<tr>"
            f"<td>{date_cell}</td>"
            f"<td>{time_cell}</td>"
            f"<td>{status}</td>"
            f"<td>{location}</td>"
            "</tr>"
        )

    html += ["</tbody></table></body></html>"]
    return "".join(html)
