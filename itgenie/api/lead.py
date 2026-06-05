import frappe
import requests
from datetime import datetime, timezone, timedelta


# ─────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────

def _get_access_token():
    token = frappe.db.get_single_value("FB Configuration", "access_token")
    if not token:
        frappe.throw("Facebook Access Token is not configured in FB Configuration.")
    return token


def _paginate(url, params):
    """
    Generic paginator for Facebook Graph API.
    Yields one item at a time across all pages.
    """
    while url:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            frappe.throw(
                f"Facebook API Error [{data['error'].get('code')}]: "
                f"{data['error'].get('message')}"
            )

        for item in data.get("data", []):
            yield item

        url = data.get("paging", {}).get("next")
        params = {}  # next URL already carries all query params


# ─────────────────────────────────────────────────────────────
# 1. GET ACTIVE FACEBOOK PAGES
# ─────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_fb_pages():
    """
    Returns all Facebook Pages the configured token has access to.

    Sample response:
    [
        {
            "id": "123456789",
            "name": "My Business Page",
            "category": "Software",
            "page_access_token": "EAABsbCS..."
        },
        ...
    ]
    """
    access_token = _get_access_token()

    pages = list(_paginate(
        url="https://graph.facebook.com/v20.0/me/accounts",
        params={
            "fields": "id,name,category,access_token",
            "limit": 100,
            "access_token": access_token,
        }
    ))

    # Rename to avoid confusion with the user-level token
    for page in pages:
        page["page_access_token"] = page.pop("access_token", None)

    return pages


# ─────────────────────────────────────────────────────────────
# 2. GET ACTIVE LEAD-AD FORMS FOR A PAGE
# ─────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_fb_forms(page_id):
    """
    Returns all ACTIVE lead-ad forms for a given page.
    Uses the page-level access token (required by Facebook for /leadgen_forms).

    Sample response:
    [
        {
            "id": "987654321",
            "name": "Summer Campaign Form",
            "status": "ACTIVE",
            "leads_count": 142,
            "created_time": "2024-06-01T10:00:00+0000"
        },
        ...
    ]
    """
    access_token = _get_access_token()

    # Step 1 — get the page-level access token
    resp = requests.get(
        f"https://graph.facebook.com/v20.0/{page_id}",
        params={"fields": "access_token", "access_token": access_token},
        timeout=30,
    )
    resp.raise_for_status()
    page_data = resp.json()

    if "error" in page_data:
        frappe.throw(
            f"Could not fetch page token for page {page_id}: "
            f"{page_data['error'].get('message')}"
        )

    page_access_token = page_data.get("access_token", access_token)

    # Step 2 — fetch all forms, return only ACTIVE ones
    forms = [
        form for form in _paginate(
            url=f"https://graph.facebook.com/v20.0/{page_id}/leadgen_forms",
            params={
                "fields": "id,name,status,leads_count,created_time",
                "limit": 100,
                "access_token": page_access_token,
            }
        )
        if form.get("status") == "ACTIVE"
    ]

    return forms


# ─────────────────────────────────────────────────────────────
# 3. VALIDATE LEADS FOR A SINGLE FORM
# ─────────────────────────────────────────────────────────────

@frappe.whitelist()
def validate_form_leads(form_id, start_date, end_date):
    """
    Compares Meta lead count vs ERPNext lead count for a specific form
    within the given date range (both dates inclusive, format: YYYY-MM-DD).

    Sample response:
    {
        "form_id":          "987654321",
        "start_date":       "2024-06-01",
        "end_date":         "2024-06-30",
        "meta_count":       150,
        "erp_count":        145,
        "difference":       5,
        "variance_pct":     3.33,
        "status":           "Mismatch",
        "missing_lead_ids": ["fb_lead_id_1", "fb_lead_id_2", ...]
    }
    """
    access_token = _get_access_token()

    start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_dt   = datetime.strptime(end_date,   "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)

    # ── Collect all Meta lead IDs within the date range ──
    meta_lead_ids = []

    for lead in _paginate(
        url=f"https://graph.facebook.com/v20.0/{form_id}/leads",
        params={
            "fields": "id,created_time",
            "limit": 100,
            "access_token": access_token,
        }
    ):
        created_time = datetime.strptime(lead["created_time"], "%Y-%m-%dT%H:%M:%S%z")
        if start_dt <= created_time < end_dt:
            meta_lead_ids.append(lead["id"])

    meta_count = len(meta_lead_ids)

    # ── ERPNext count for the same form + date range ──
    existing_in_erp = frappe.db.sql("""
        SELECT COUNT(*)
        FROM `tabLead`
        WHERE custom_form_id = %s
          AND DATE(creation) BETWEEN %s AND %s
    """, (form_id, start_date, end_date))[0][0]
    erp_count = existing_in_erp

    # ── Find which Meta lead IDs are missing in ERPNext ──
    missing_lead_ids = []
    if meta_lead_ids:
        fb_lead_id_field = None
        for candidate in ("fb_lead_id", "lead_id"):
            if frappe.db.has_column("Lead", candidate):
                fb_lead_id_field = candidate
                break

        if fb_lead_id_field:
            existing_lead_ids_in_erp = {
                row[0] for row in frappe.db.sql(
                    "SELECT `{0}` FROM `tabLead` WHERE `{0}` IN ({1})".format(
                        fb_lead_id_field,
                        ", ".join(["%s"] * len(meta_lead_ids))
                    ),
                    tuple(meta_lead_ids)
                )
            }
            missing_lead_ids = [lid for lid in meta_lead_ids if lid not in existing_lead_ids_in_erp]

    difference   = meta_count - erp_count
    variance_pct = round((difference / meta_count * 100), 2) if meta_count else 0.0

    return {
        "form_id":          form_id,
        "start_date":       start_date,
        "end_date":         end_date,
        "meta_count":       meta_count,
        "erp_count":        erp_count,
        "difference":       difference,
        "variance_pct":     variance_pct,
        "status":           "Matched" if difference == 0 else "Mismatch",
        "missing_lead_ids": missing_lead_ids,
    }


# ─────────────────────────────────────────────────────────────
# 4. VALIDATE ALL ACTIVE FORMS FOR A PAGE
# ─────────────────────────────────────────────────────────────

@frappe.whitelist()
def validate_page_leads(page_id, start_date, end_date):
    """
    Runs validation for every ACTIVE form on the given page and returns
    a per-form breakdown plus a page-level summary.

    Sample response:
    {
        "page_id":    "123456789",
        "start_date": "2024-06-01",
        "end_date":   "2024-06-30",
        "summary": {
            "total_forms":      5,
            "matched_forms":    3,
            "mismatched_forms": 2,
            "total_meta_count": 500,
            "total_erp_count":  492,
            "total_difference": 8,
            "variance_pct":     1.6
        },
        "forms": [
            {
                "form_id":          "987654321",
                "form_name":        "Summer Campaign",
                "meta_count":       150,
                "erp_count":        148,
                "difference":       2,
                "variance_pct":     1.33,
                "status":           "Mismatch",
                "missing_lead_ids": [...]
            },
            ...
        ]
    }
    """
    forms   = get_fb_forms(page_id)
    results = []

    for form in forms:
        try:
            v = validate_form_leads(form["id"], start_date, end_date)
            results.append({
                "form_id":          form["id"],
                "form_name":        form.get("name", "—"),
                "meta_count":       v["meta_count"],
                "erp_count":        v["erp_count"],
                "difference":       v["difference"],
                "variance_pct":     v["variance_pct"],
                "status":           v["status"],
                "missing_lead_ids": v["missing_lead_ids"],
            })
        except Exception as e:
            results.append({
                "form_id":          form["id"],
                "form_name":        form.get("name", "—"),
                "meta_count":       None,
                "erp_count":        None,
                "difference":       None,
                "variance_pct":     None,
                "status":           "Error",
                "error":            str(e),
                "missing_lead_ids": [],
            })

    # ── Page-level summary (exclude error rows) ──
    valid = [r for r in results if r["status"] != "Error"]

    total_meta = sum(r["meta_count"] for r in valid)
    total_erp  = sum(r["erp_count"]  for r in valid)
    total_diff = total_meta - total_erp

    summary = {
        "total_forms":      len(forms),
        "matched_forms":    sum(1 for r in valid if r["status"] == "Matched"),
        "mismatched_forms": sum(1 for r in valid if r["status"] == "Mismatch"),
        "total_meta_count": total_meta,
        "total_erp_count":  total_erp,
        "total_difference": total_diff,
        "variance_pct":     round((total_diff / total_meta * 100), 2) if total_meta else 0.0,
    }

    return {
        "page_id":    page_id,
        "start_date": start_date,
        "end_date":   end_date,
        "summary":    summary,
        "forms":      results,
    }



# import frappe
# import requests
# from datetime import datetime, timezone, timedelta

# @frappe.whitelist()
# def validate_meta_leads(form_id, start_date, end_date):
# # def validate_meta_leads():
#     access_token = frappe.db.get_single_value(
#         "FB Configuration",
#         "access_token"
#     )

#     start_dt = datetime.strptime(
#         start_date,
#         "%Y-%m-%d"
#     ).replace(tzinfo=timezone.utc)

#     end_dt = datetime.strptime(
#         end_date,
#         "%Y-%m-%d"
#     ).replace(tzinfo=timezone.utc) + timedelta(days=1)

#     url = f"https://graph.facebook.com/v20.0/{form_id}/leads"

#     params = {
#         "fields": "id,created_time",
#         "limit": 100,
#         "access_token": access_token
#     }

#     facebook_count = 0

#     while url:

#         response = requests.get(url, params=params)
#         data = response.json()

#         for lead in data.get("data", []):

#             created_time = datetime.strptime(
#                 lead["created_time"],
#                 "%Y-%m-%dT%H:%M:%S%z"
#             )

#             if start_dt <= created_time < end_dt:
#                 facebook_count += 1

#         url = data.get("paging", {}).get("next")

#         params = {}

#     erpnext_count = frappe.db.sql("""
#         SELECT COUNT(*)
#         FROM `tabLead`
#         WHERE custom_form_id = %s
#         AND DATE(creation) BETWEEN %s AND %s
#     """, (form_id, start_date, end_date))[0][0]

#     return {
#         "facebook_count": facebook_count,
#         "erpnext_count": erpnext_count,
#         "difference": facebook_count - erpnext_count,
#         "status": "Matched" if facebook_count == erpnext_count else "Mismatch"
#     }


# # @frappe.whitelist()
# # def get_meta_lead_dashboard():
# #     today = frappe.utils.today()

# #     return validate_meta_leads(
# #         start_date=today,
# #         end_date=today,
# #         page_id=None,
# #         form_id=None,
# #         only_mismatch=1
# #     )


# # @frappe.whitelist()
# # def validate_meta_leads(start_date=None, end_date=None, page_id=None, form_id=None, only_mismatch=0):

# #     import requests
# #     from datetime import datetime, timezone, timedelta

# #     access_token = frappe.db.get_single_value("FB Configuration", "access_token")

# #     if not start_date:
# #         start_date = frappe.utils.today()

# #     if not end_date:
# #         end_date = frappe.utils.today()

# #     start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
# #     end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)

# #     def get_all_graph_data(url, params):
# #         rows = []
# #         while url:
# #             response = requests.get(url, params=params)
# #             data = response.json()

# #             if data.get("error"):
# #                 frappe.throw(str(data.get("error")))

# #             rows.extend(data.get("data", []))
# #             url = data.get("paging", {}).get("next")
# #             params = {}

# #         return rows

# #     def count_facebook_leads(meta_form_id, token):
# #         url = "https://graph.facebook.com/v20.0/" + meta_form_id + "/leads"

# #         params = {
# #             "fields": "id,created_time",
# #             "limit": 100,
# #             "access_token": token
# #         }

# #         leads = get_all_graph_data(url, params)

# #         count = 0

# #         for lead in leads:
# #             created_time = datetime.strptime(
# #                 lead["created_time"],
# #                 "%Y-%m-%dT%H:%M:%S%z"
# #             )

# #             if start_dt <= created_time < end_dt:
# #                 count += 1

# #         return count

# #     pages_url = "https://graph.facebook.com/v20.0/me/accounts"

# #     pages = get_all_graph_data(
# #         pages_url,
# #         {
# #             "fields": "id,name,access_token",
# #             "limit": 100,
# #             "access_token": access_token
# #         }
# #     )

# #     result = []

# #     for page in pages:

# #         if page_id and page.get("id") != page_id:
# #             continue

# #         current_page_id = page.get("id")
# #         page_name = page.get("name")
# #         page_token = page.get("access_token") or access_token

# #         forms_url = "https://graph.facebook.com/v20.0/" + current_page_id + "/leadgen_forms"

# #         forms = get_all_graph_data(
# #             forms_url,
# #             {
# #                 "fields": "id,name,status",
# #                 "limit": 100,
# #                 "access_token": page_token
# #             }
# #         )

# #         for form in forms:

# #             if form.get("status") != "ACTIVE":
# #                 continue

# #             if form_id and form.get("id") != form_id:
# #                 continue

# #             current_form_id = form.get("id")

# #             facebook_count = count_facebook_leads(current_form_id, page_token)

# #             erpnext_count = frappe.db.sql("""
# #                 SELECT COUNT(*)
# #                 FROM `tabLead`
# #                 WHERE custom_form_id = %s
# #                 AND DATE(custom_meta_created_time) BETWEEN %s AND %s
# #             """, (current_form_id, start_date, end_date))[0][0]

# #             difference = facebook_count - erpnext_count
# #             status = "Matched" if difference == 0 else "Mismatch"

# #             if int(only_mismatch or 0) == 1 and status == "Matched":
# #                 continue

# #             result.append({
# #                 "page_id": current_page_id,
# #                 "page_name": page_name,
# #                 "form_id": current_form_id,
# #                 "form_name": form.get("name"),
# #                 "form_status": form.get("status"),
# #                 "start_date": start_date,
# #                 "end_date": end_date,
# #                 "facebook_count": facebook_count,
# #                 "erpnext_count": erpnext_count,
# #                 "difference": difference,
# #                 "status": status,
# #                 "indicator": "red" if status == "Mismatch" else "green"
# #             })

# #     return {
# #         "start_date": start_date,
# #         "end_date": end_date,
# #         "total_rows": len(result),
# #         "data": result
# #     }
