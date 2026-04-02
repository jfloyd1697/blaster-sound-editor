def unique_name(base: str, existing: set[str]) -> str:
    if base not in existing:
        return base

    i = 1
    while f"{base}_{i}" in existing:
        i += 1
    return f"{base}_{i}"