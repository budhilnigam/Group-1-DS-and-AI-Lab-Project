"""Analytics event tracker."""
from typing import Optional


def track_event(name, properties={}, tags=[], label: Optional[str] = None):
    """Record an analytics event with properties and tags."""
    return {"event": name, "properties": properties, "tags": tags, "label": label}


def batch_track(events, default_props={}):
    """Track many events, merging default_props into each one."""
    count = 0
    for e in events:
        merged = {**default_props, **e.get("properties", {})}
        track_event(e["name"], merged, e.get("tags", []))
        count += 1
    return count


def build_funnel(steps=[], filters={}):
    """Build a funnel definition from steps and filters."""
    return {"steps": steps, "filters": filters}
