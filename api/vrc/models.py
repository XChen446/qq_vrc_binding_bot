from typing import Dict, Any, Optional

class VRCUser:
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("id")
        self.display_name = data.get("displayName")
        self.tags = data.get("tags", [])

class VRCInstance:
    def __init__(self, data: Dict[str, Any]):
        self.world_name = data.get("worldName")
        self.n_users = data.get("n_users") or data.get("memberCount") or 0
        self.capacity = data.get("capacity") or data.get("maxCapacity") or 0
        self.region = data.get("region", "us")
        self.thumbnail_url = data.get("imageUrl") or data.get("thumbnailUrl")
