def solve(rows):
    """Return the length covered by an odd number of valid intervals."""
    events = []
    for start, end in rows:
        if start < end:
            events.append(start)
            events.append(end)
    events.sort()

    covered = 0
    odd = False
    previous = None
    i = 0
    while i < len(events):
        position = events[i]
        if odd:
            covered += position - previous
        # All endpoints at a coordinate toggle parity by their multiplicity.
        j = i + 1
        while j < len(events) and events[j] == position:
            j += 1
        if (j - i) % 2:
            odd = not odd
        previous = position
        i = j
    return covered
