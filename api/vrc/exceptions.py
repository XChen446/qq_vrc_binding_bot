class VRCAPIException(Exception):
    """VRChat API 基础异常"""
    pass

class VRCAuthException(VRCAPIException):
    """身份验证失败"""
    pass

class VRCRateLimitException(VRCAPIException):
    """被频率限制"""
    pass
