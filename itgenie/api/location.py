import frappe
import requests
import re
from urllib.parse import unquote


def dms_to_decimal(deg, minutes, seconds, direction):
    decimal = float(deg) + float(minutes)/60 + float(seconds)/3600
    if direction in ['S', 'W']:
        decimal = -decimal
    return decimal


def extract_coords(url):
    decoded = unquote(url)

    # 1. !3d and !4d independently (most accurate)
    lats_3d = re.findall(r'!3d(-?\d+\.\d+)', decoded)
    lngs_4d = re.findall(r'!4d(-?\d+\.\d+)', decoded)
    if lats_3d and lngs_4d:
        return lats_3d[-1], lngs_4d[-1]

    # 2. /maps/search/lat,+lng (short URL expanded format)
    match = re.search(r'/maps/search/(-?\d+\.\d+),\+?(-?\d+\.\d+)', decoded)
    if match:
        return match.group(1), match.group(2)

    # 3. @lat,lng,zoom
    match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+),\d+', decoded)
    if match:
        return match.group(1), match.group(2)

    # 4. @lat,lng
    match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', decoded)
    if match:
        return match.group(1), match.group(2)

    # 5. ?q=lat,lng or &q=lat,lng
    match = re.search(r'[?&]q=(-?\d+\.\d+),\+?(-?\d+\.\d+)', decoded)
    if match:
        return match.group(1), match.group(2)

    # 6. /place/lat,lng
    match = re.search(r'/place/(-?\d+\.\d+),(-?\d+\.\d+)', decoded)
    if match:
        return match.group(1), match.group(2)

    # 7. DMS format: 13°03'02.6"N 80°09'33.9"E
    dms_match = re.search(
        r'(\d{1,3})[°º](\d{1,2})[\'′\u2019]([0-9.]+)[\"″\u201d]([NS])'
        r'[^0-9]*'
        r'(\d{1,3})[°º](\d{1,2})[\'′\u2019]([0-9.]+)[\"″\u201d]([EW])',
        decoded
    )
    if dms_match:
        lat = dms_to_decimal(
            dms_match.group(1), dms_match.group(2),
            dms_match.group(3), dms_match.group(4)
        )
        lng = dms_to_decimal(
            dms_match.group(5), dms_match.group(6),
            dms_match.group(7), dms_match.group(8)
        )
        return str(lat), str(lng)

    return None, None


def expand_short_url(url):
    """Expand short URLs like maps.app.goo.gl"""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        # Try HEAD first (faster)
        response = requests.head(
            url,
            allow_redirects=True,
            timeout=10,
            headers=headers
        )
        final_url = response.url

        # If HEAD didn't redirect to google maps, try GET
        if "google.com/maps" not in final_url:
            response = requests.get(
                url,
                allow_redirects=True,
                timeout=10,
                headers=headers
            )
            final_url = response.url

        frappe.log_error(message=f"Expanded: {final_url}", title="MAP EXPAND")
        return final_url

    except Exception as e:
        frappe.log_error(message=str(e), title="MAP EXPAND ERROR")
        return url


@frappe.whitelist()
def get_car(url):
    try:
        if not url:
            return {"lat": None, "lng": None, "error": "Empty URL"}

        url = url.strip()

        frappe.log_error(message=f"Input: {url}", title="MAP INPUT")

        # STEP 1: Try direct extraction from original URL
        lat, lng = extract_coords(url)
        if lat is not None and lng is not None:
            frappe.log_error(message=f"Direct: {lat}, {lng}", title="MAP RESULT")
            return {"lat": float(lat), "lng": float(lng), "full_url": url}

        # STEP 2: Expand short URL and retry
        final_url = expand_short_url(url)
        lat, lng = extract_coords(final_url)
        if lat is not None and lng is not None:
            frappe.log_error(message=f"Expanded: {lat}, {lng}", title="MAP RESULT")
            return {"lat": float(lat), "lng": float(lng), "full_url": final_url}

        return {
            "lat": None,
            "lng": None,
            "error": "Could not extract coordinates",
            "tried_url": final_url
        }

    except Exception:
        frappe.log_error(message=frappe.get_traceback(), title="MAP ERROR")
        return {"lat": None, "lng": None, "error": "Server error"}
