def build(user, include_archived=False, role="viewer"):
    rows = [f"{user}:active"]
    if include_archived:
        rows.append(f"{user}:archived")
    if role == "admin":
        rows.append(f"{user}:secret")
    return rows
