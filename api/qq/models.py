from typing import Dict, Any

class QQEvent:
    def __init__(self, data: Dict[str, Any]):
        self.raw_data = data
        self.post_type = data.get("post_type")
        self.message_type = data.get("message_type")
        self.notice_type = data.get("notice_type")
        self.request_type = data.get("request_type")
        self.user_id = data.get("user_id")
        self.group_id = data.get("group_id")
        self.raw_message = data.get("raw_message")
        self.sub_type = data.get("sub_type")
        self.flag = data.get("flag")
        self.comment = data.get("comment")
