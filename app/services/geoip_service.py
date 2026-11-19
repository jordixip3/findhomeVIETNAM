def extract_client_ip(headers: dict, fallback: str = "127.0.0.1") -> str:
    cf = headers.get("cf-connecting-ip")
    if cf: return cf.strip()
    xf = headers.get("x-forwarded-for")
    if xf: return xf.split(",")[0].strip()
    return headers.get("x-real-ip", fallback).strip()

def detect_device_type(ua: str) -> str:
    ua = (ua or "").lower()
    if any(m in ua for m in ["iphone", "android", "mobile"]): return "Mobile"
    if "ipad" in ua or "tablet" in ua: return "Tablet"
    return "Desktop"

def resolve_geoip(ip: str):
    return {"country": "Global Node", "country_code": "AS", "city": "Metro Core", "latitude": 35.0, "longitude": 105.0}
