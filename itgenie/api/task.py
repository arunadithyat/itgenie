import frappe
import json
import requests


@frappe.whitelist(allow_guest=True)
def project_tasks_modal():
    """
    Slash command handler to open project tasks modal.
    """
    payload = frappe.request.form
    trigger_id = payload.get("trigger_id")

    # Run SQL query
    data = frappe.db.sql("""
        SELECT
            p.project_name AS project_title,
            t.subject AS subject,
            td.allocated_to AS assign_to,
            u.full_name AS assign_to_name,
            t.priority AS priority,
            t.exp_end_date AS deadline,
            p.custom_exp_end_date AS custom_exp_end_date,
            p.percent_complete AS percent_complete
        FROM
            `tabProject` p
        JOIN
            `tabTask` t ON t.project = p.name
        LEFT JOIN
            `tabToDo` td ON td.reference_type = 'Task'
                        AND td.reference_name = t.name
                        AND td.status = 'Open'
        LEFT JOIN
            `tabUser` u ON u.name = td.allocated_to
        WHERE
            p.project_type = 'AutomateGenie'
            AND t.status NOT IN ('Completed', 'Cancelled')
        ORDER BY
            p.project_name, t.exp_end_date
    """, as_dict=True)

    blocks = []
    blocks.append({
        "type": "header",
        "text": {"type": "plain_text", "text": f"🚀 AutomateGenie Tasks ({len(data)})", "emoji": True}
    })

    if not data:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "🎉 No active tasks found."}
        })
    else:
        for row in data:
            blocks.extend([
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*🧾 Project:* {row.project_title}\n"
                            f"*📌 Task:* {row.subject}\n"
                            f"*👤 Assigned to:* {row.assign_to_name or 'Unassigned'}\n"
                            f"*🎯 Priority:* {row.priority or 'N/A'}\n"
                            f"*📅 Deadline:* {row.deadline or '-'}\n"
                            f"*📈 Progress:* {row.percent_complete or 0}%"
                        )
                    }
                },
                {"type": "divider"}
            ])

    modal_view = {
        "type": "modal",
        "callback_id": "project_tasks_modal",
        "title": {"type": "plain_text", "text": "Project Tasks"},
        "close": {"type": "plain_text", "text": "Close"},
        "blocks": blocks[:100]  # Slack max limit
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
        frappe.log_error(json.dumps(slack_response, indent=2), "Slack Project Modal Error")
        frappe.response["message"] = slack_response.get("error", "Modal open failed")
        frappe.response["status_code"] = 400
        return

   # frappe.response["status_code"] = 200
    frappe.response["message"]  = "AutomateGenie Tasks"
