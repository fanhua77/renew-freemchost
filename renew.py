import os
import sys
from datetime import datetime
import json
import requests

# ==================== 🔧 核心配置区 ====================
LOGIN_URL = "https://laehfeigoiycigkfknfn.supabase.co/auth/v1/token?grant_type=password"
EMAIL = os.getenv("MY_EMAIL")
PASSWORD = os.getenv("MY_PASSWORD")
SUPABASE_ANON_KEY = os.getenv("ANON_KEY")

RENEW_ACTION_URL = "https://freemchost.com/_serverFn/798181797bd95a02dee916a26c18d3539a58152db8660e097ca48d7cdd8ee50c"
RENEW_DETAIL_URL = "https://freemchost.com/_serverFn/4f1effc1137be00b6dda3a226e97ae9c9a3e36e88cb167929270f1ed233df17e"
SERVER_ID = "da2e2d7d-f3f5-4a0f-8568-1af631548118"

SCKEY = os.getenv("SCKEY")

if not all([EMAIL, PASSWORD, SUPABASE_ANON_KEY]):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] 🛑 错误: 未能在环境中检测到必要的凭证 (MY_EMAIL, MY_PASSWORD 或 ANON_KEY)。")
    sys.exit(1)
# =====================================================

def log(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {message}")

def notify(title, content):
    if SCKEY:
        try:
            requests.post(f"https://sctapi.ftqq.com/{SCKEY}.send", data={"title": title, "desp": content}, timeout=5)
        except Exception as e:
            log(f"🔔 推送通知失败: {e}")

def parse_action_response(res_json):
    action_info = {"expires_at": None, "status_code": "未知"}
    try:
        outer_p = res_json.get("p", {})
        keys = outer_p.get("k", [])
        values = outer_p.get("v", [])

        if "result" in keys:
            idx = keys.index("result")
            if idx < len(values):
                result_node_p = values[idx].get("p", {})
                sub_keys = result_node_p.get("k", [])
                sub_values = result_node_p.get("v", [])

                if "expires_at" in sub_keys:
                    sub_idx = sub_keys.index("expires_at")
                    if sub_idx < len(sub_values):
                        action_info["expires_at"] = sub_values[sub_idx].get("s")
        
        if "error" in keys:
            err_idx = keys.index("error")
            if err_idx < len(values):
                action_info["status_code"] = values[err_idx].get("s", "未知")
    except Exception as e:
        log(f"解析续期动作响应异常: {e}")
    return action_info

def parse_detail_response(res_json):
    info = {"name": "未知", "status": "未知"}
    try:
        outer_v = res_json.get("p", {}).get("v", [])
        if not outer_v:
            return info

        mid_v = outer_v[0].get("p", {}).get("v", [])
        if not mid_v:
            return info

        server_node = mid_v[0]
        keys = server_node.get("p", {}).get("k", [])
        values = server_node.get("p", {}).get("v", [])

        if "name" in keys:
            info["name"] = values[keys.index("name")].get("s", "未知")
        if "status" in keys:
            info["status"] = values[keys.index("status")].get("s", "未知")
    except Exception as e:
        log(f"解析最终详情响应异常: {e}")
    return info

def get_new_token():
    log("🔑 正在尝试模拟登录以获取个人 Token...")
    headers = {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9",
        "content-type": "application/json",
        "apikey": SUPABASE_ANON_KEY,
        "authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "origin": "https://new.freemchost.com",
        "referer": "https://new.freemchost.com/",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
    }
    payload = {"email": EMAIL, "password": PASSWORD, "gotrue_meta_security": {}}
    try:
        response = requests.post(LOGIN_URL, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            token = response.json().get("access_token")
            if token:
                log("✅ 成功模拟登录，已捕获最新专属 Token！")
                return token
        log(f"❌ 登录失败，状态码: {response.status_code}")
    except Exception as e:
        log(f"💥 登录请求引发异常: {e}")
    return None

def run_auto_renew():
    log("▶️ 开始全自动登录 + 链式续期确认流程...")
    token = get_new_token()
    if not token:
        log("🛑 未能取得有效 Token，流程被迫中断。")
        sys.exit(1)

    base_headers = {
        "accept": "application/x-tss-framed, application/x-ndjson, application/json",
        "authorization": f"Bearer {token}",
        "content-type": "application/json",
        "origin": "https://new.freemchost.com",
        "referer": f"https://new.freemchost.com/app/servers/{SERVER_ID}",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "x-tsr-serverfn": "true"
    }
    renew_payload = {
        "t": {"t": 10, "i": 0, "p": {"k": ["data"], "v": [{"t": 10, "i": 1, "p": {"k": ["id"], "v": [{"t": 1, "s": SERVER_ID}]}, "o": 0}]}}, "f": 63, "m": []
    }

    log("⚡ 步骤 1/2: 正在向后端发送续期指令...")
    expires_at = None
    try:
        action_res = requests.post(RENEW_ACTION_URL, headers=base_headers, json=renew_payload, timeout=15)
        if action_res.status_code == 200:
            action_info = parse_action_response(action_res.json())
            expires_at = action_info["expires_at"]
        else:
            log(f"❌ 续期动作请求失败，状态码: {action_res.status_code}")
            sys.exit(1)
    except Exception as e:
        log(f"💥 续期动作接口引发异常: {e}")
        sys.exit(1)

    if not expires_at:
        log("⚠️ 接口 A 响应成功，但未能提取出新到期日期，流程中断。")
        sys.exit(1)

    log("🔍 步骤 2/2: 续期指令已生效，正在拉取最终服务器完整状态确认...")
    server_name = "未知"
    server_status = "未知"
    try:
        detail_res = requests.post(RENEW_DETAIL_URL, headers=base_headers, json=renew_payload, timeout=15)
        if detail_res.status_code == 200:
            server_info = parse_detail_response(detail_res.json())
            server_name = server_info["name"]
            server_status = server_info["status"]
    except Exception as e:
        pass

    # 将 UTC 时间字符串（2026-07-14T08:40:40.997Z）优雅地清洗为标准格式
    try:
        clean_time = expires_at.replace("T", " ").split(".")[0].replace("Z", "")
    except Exception:
        clean_time = expires_at

    log("🎉【全链路全自动续期成功】-----------------------")
    print(f"📌 服务器名称: {server_name}")
    print(f"📊 当前状态: {server_status}")
    print(f"📅 到期时间: {clean_time}")
    log("--------------------------------------------------")

if __name__ == "__main__":
    run_auto_renew()
