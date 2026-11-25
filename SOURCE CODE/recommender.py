"""Learning resources for gaps, in screening priority order."""
from matcher import catalog


def recommendations(gaps):
    for gap in gaps:
        yield gap, catalog().get(gap.name)
