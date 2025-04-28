def seconds_to_human(seconds: int, *, sep: str = ":", full: bool = True) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if full:
        return f"{h}{sep}{m:02.0f}{sep}{s:02.0f}"
    h_str = f"{h}h{sep}" if h else ""
    m_str = f"{m:02.0f}m{sep}" if m else ""
    s_str = f"{s:02.0f}s"
    return f"{h_str}{m_str}{s_str}"
