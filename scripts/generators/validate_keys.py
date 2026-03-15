def validate_ops_unique(ops: list[dict]):
    seen = {}
    errors = []

    for op in ops:
        key = op.get("key")
        path = op.get("path")

        if not key:
            errors.append(f"Missing op key for path: {path}")
            continue
        if not path:
            errors.append(f"Missing op path for key: {key}")
            continue

        if key in seen:
            errors.append(
                f"Duplicate key emitted:\n"
                f"  {key}\n"
                f"  {seen[key]} AND {path}"
            )
        else:
            seen[key] = path

    if errors:
        raise Exception("\n\n".join(errors))