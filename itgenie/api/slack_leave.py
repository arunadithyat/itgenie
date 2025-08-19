import frappe
import json
import requests


@frappe.whitelist(allow_guest=True)
def leave_application_modal():
    payload = frappe.request.form
    trigger_id = payload.get("trigger_id")

    modal_view = {
        "type": "modal",
        "callback_id": "leave_submit",
        "title": {"type": "plain_text", "text": "Leave Application"},
        "submit": {"type": "plain_text", "text": "Apply"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "emp_id",
                "label": {"type": "plain_text", "text": "Employee ID"},
                "element": {"type": "plain_text_input", "action_id": "value"}
            },
            {
                "type": "input",
                "block_id": "leave_type",
                "label": {"type": "plain_text", "text": "Leave Type"},
                "element": {
                    "type": "static_select",
                    "action_id": "value",
                    "options": [
                        {"text": {"type": "plain_text", "text": "Casual Leave"}, "value": "Casual Leave"},
                        {"text": {"type": "plain_text", "text": "Sick Leave"}, "value": "Sick Leave"},
                        {"text": {"type": "plain_text", "text": "Earned Leave"}, "value": "Earned Leave"}
                    ]
                }
            },
            {
                "type": "input",
                "block_id": "from_date",
                "label": {"type": "plain_text", "text": "From Date"},
                "element": {"type": "datepicker", "action_id": "value"}
            },
            {
                "type": "input",
                "block_id": "to_date",
                "label": {"type": "plain_text", "text": "To Date"},
                "element": {"type": "datepicker", "action_id": "value"}
            },
            {
                "type": "input",
                "block_id": "reason",
                "label": {"type": "plain_text", "text": "Reason for Leave"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "value",
                    "multiline": True
                }
            }
        ]
    }

    headers = {
        "Authorization": f"Bearer {frappe.conf.slack_bot_token}",
        "Content-Type": "application/json"
    }

    res = requests.post("https://slack.com/api/views.open", headers=headers, json={
        "trigger_id": trigger_id,
        "view": modal_view
    })

    slack_response = res.json()
    if not slack_response.get("ok"):
        frappe.log_error(json.dumps(slack_response, indent=2), "Slack Leave Modal Error")
        frappe.response["message"] = slack_response.get("error", "Modal open failed")
        frappe.response["status_code"] = 400
        return

    frappe.response["message"] = "Leave Application Modal Opened"
