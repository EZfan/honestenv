def cmp_version(left: str, right: str) -> int:
    """Compare two dotted versions."""
    return (left > right) - (left < right)
