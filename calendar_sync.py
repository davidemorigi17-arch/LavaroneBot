from googleapiclient.discovery import build

def push_event(service, calendar_id, name, start, end):

    event = {
        'summary': name,
        'start': {'date': start},
        'end': {'date': end}
    }

    service.events().insert(
        calendarId=calendar_id,
        body=event
    ).execute()
