from datetime import datetime

def overlap(a_start, a_end, b_start, b_end):
    return not (a_end < b_start or b_end < a_start)


def parse(date_str):
    return datetime.strptime(date_str, "%d-%m-%Y")
