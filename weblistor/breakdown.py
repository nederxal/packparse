from fractions import Fraction


BEATS_PER_MEASURE = 4
MAX_STEP_GAP = Fraction(1, 4)
MIN_STREAM_BEATS = BEATS_PER_MEASURE
STEP_STARTS = frozenset("124")


def stream_breakdown(measures):
    """Format runs of at least one measure at 16th-note cadence or faster."""
    runs = []
    start = previous = last_gap = None
    for index, measure in enumerate(measures):
        for row_index, row in enumerate(measure):
            if STEP_STARTS.isdisjoint(row):
                continue
            beat = index * BEATS_PER_MEASURE + Fraction(
                row_index * BEATS_PER_MEASURE, len(measure)
            )
            gap = beat - previous if previous is not None else None
            if gap is None or gap > MAX_STEP_GAP:
                if last_gap is not None:
                    runs.append((start, previous + last_gap))
                start, last_gap = beat, None
            else:
                last_gap = gap
            previous = beat
    if last_gap is not None:
        chart_end = len(measures) * BEATS_PER_MEASURE
        runs.append((start, min(previous + last_gap, chart_end)))

    parts = []
    previous_end = None
    for start, end in runs:
        if end - start < MIN_STREAM_BEATS:
            continue
        if previous_end is not None:
            parts.append(break_separator((start - previous_end) / BEATS_PER_MEASURE))
        length = (end - start) / BEATS_PER_MEASURE
        parts.append(str(int(length + Fraction(1, 2))))
        previous_end = end
    return "".join(parts)


def break_separator(measures):
    if measures <= Fraction(1, 2):
        return "'"
    if measures <= 4:
        return "-"
    if measures <= 32:
        return "/"
    return "|"
