import base64
import requests
import datetime
import frappe
from urllib.parse import quote

# ---------- CONFIG ----------
ZOOM_ACCOUNT_ID = "w_hW_7NxTWu4_y6JrAaWXQ"
ZOOM_CLIENT_ID = "ydSD5zxwQrimWMKcCMMEwQ"
ZOOM_CLIENT_SECRET = "ovsSCktogvt0kb1EmwMFqhsoKX6P86NC"
DEFAULT_HOST_EMAIL = "dhamuruga@gmail.com"

# ---- Zoom API Credentials ----
IST_OFFSET = datetime.timedelta(hours=5, minutes=30)


# ---------- Utility Functions ----------
def token():
    url = "https://zoom.us/oauth/token"
    params = {"grant_type": "account_credentials", "account_id": ZOOM_ACCOUNT_ID}
    auth = "Basic " + base64.b64encode(
        f"{ZOOM_CLIENT_ID}:{ZOOM_CLIENT_SECRET}".encode()
    ).decode()

    r = requests.post(url, params=params, headers={"Authorization": auth}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def todayIST():
    now_utc = datetime.datetime.utcnow()
    today_ist = (now_utc + IST_OFFSET).date()
    return today_ist.isoformat()


def meetings(token_value, email):
    base = "https://api.zoom.us/v2"
    url = f"{base}/report/users/{email}/meetings"
    headers = {"Authorization": f"Bearer {token_value}"}

    meetings_data = []
    next_page = None

    while True:
        params = {"from": todayIST(), "to": todayIST(), "page_size": 100}

        if next_page:
            params["next_page_token"] = next_page

        r = requests.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()

        meetings_data += data.get("meetings", [])
        next_page = data.get("next_page_token")

        if not next_page:
            break

    return meetings_data


def participants(token_value, meeting_uuid):
    base = "https://api.zoom.us/v2"
    enc_uuid = quote(meeting_uuid, safe="")
    url = f"{base}/past_meetings/{enc_uuid}/participants"
    headers = {"Authorization": f"Bearer {token_value}"}

    parts = []
    next_page = None

    while True:
        params = {"page_size": 300}

        if next_page:
            params["next_page_token"] = next_page

        r = requests.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()

        parts += data.get("participants", [])
        next_page = data.get("next_page_token")

        if not next_page:
            break

    return parts


# ---------- Main Function ----------
@frappe.whitelist()
def todayMeetingsWithParticipants(hostEmail=None, namesOnly=0):
    """Fetch today's completed meetings and their participant names or details"""

    email = (hostEmail or DEFAULT_HOST_EMAIL).strip()
    tok = token()
    mt_list = meetings(tok, email)

    all_data = []

    for m in mt_list:
        uuid = (m.get("uuid") or "").strip()
        if not uuid:
            continue

        part_list = participants(tok, uuid)

        if int(namesOnly) == 1:
            people = [p.get("name") or p.get("user_name") or "" for p in part_list]
        else:
            people = [{
                "name": p.get("name") or p.get("user_name"),
                "email": p.get("email"),
                "join_time": p.get("join_time"),
                "leave_time": p.get("leave_time"),
                "duration_minutes": p.get("duration"),
                "location": p.get("location"),
                "ip_address": p.get("ip_address"),
            } for p in part_list]

        all_data.append({
            "uuid": uuid,
            "meeting_id": m.get("id"),
            "topic": m.get("topic"),
            "start_time": m.get("start_time"),
            "end_time": m.get("end_time"),
            "duration": m.get("duration"),
            "participants_count": len(people),
            "participants": people,
        })

    all_data.sort(key=lambda x: x.get("start_time") or "")

    return {
        "date_ist": todayIST(),
        "host_email": email,
        "meetings_count": len(all_data),
        "meetings": all_data,
    }

