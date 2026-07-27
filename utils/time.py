import re
from datetime import datetime, timedelta, timezone

def ist_now():
    """
    Returns UTC now for DB compatibility (Naive)
    Pryton uses naive UTC for comparison with SQLALchemy DateTime objects.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)

def parse_duration(duration_str: str) -> timedelta:
    """
    Parses strings like '1d', '2h', '30m', '10s' into timedelta.
    Supports combined formats like '1d2h'.
    """
    if not duration_str: return None
    
    # Regex for days, hours, minutes, seconds
    regex = re.compile(r'((?P<days>\d+?)d)?((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')
    parts = regex.match(duration_str.lower())
    if not parts: return None
    
    parts = parts.groupdict()
    time_params = {name: int(param) for name, param in parts.items() if param}
    
    return timedelta(**time_params) if time_params else None
