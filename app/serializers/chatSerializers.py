def GroupSerializer(group) -> dict:
    return {
        "id": group["id"],
        "name": group["name"],
        "members": group["members"]
    }