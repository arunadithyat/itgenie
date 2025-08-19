import json
import frappe
from slack_sdk import WebClient
from werkzeug.wrappers import Response
from slack_sdk.errors import SlackApiError
from collections import defaultdict
import time



SLACK_BOT_TOKEN = frappe.conf.slack_bot_token  # Store in site_config.json
slack_client = WebClient(token=SLACK_BOT_TOKEN)

# -------------------------
# FETCH TIMESHEETS
# -------------------------
def get_timesheets_with_missing_points():
    return frappe.db.sql("""
        SELECT ts.name, tsd.activity_type, tsd.custom_weightage
        FROM `tabTimesheet` ts
        JOIN `tabTimesheet Detail` tsd ON ts.name = tsd.parent
        WHERE DATE(ts.custom_from_date) = CURDATE()
        AND tsd.custom_points  < 0 
    """, as_dict=True)

# -------------------------
# PUSH INITIAL MODAL
# -------------------------
def push_modal_to_slack(trigger_id, timesheet):
    blocks = []

    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*Timesheet:* {timesheet['name']}"
        }
    })

    for idx, detail in enumerate(timesheet["details"]):
        blocks.append({
            "type": "section",
            "block_id": f"activity_{idx}",
            "text": {
                "type": "mrkdwn",
                "text": f"*Activity:* {detail['activity_type']}\n*Weightage:* {detail['custom_weightage']}"
            }
        })
        blocks.append({
            "type": "actions",
            "block_id": f"actions_{idx}",
            "elements": [
                {
                    "type": "static_select",
                    "action_id": "select_points",
                    "placeholder": {"type": "plain_text", "text": "Select points"},
                    "options": [{"text": {"type": "plain_text", "text": str(p)}, "value": str(p)} for p in range(0, 105, 5)]
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Save"},
                    "style": "primary",
                    "action_id": "save_points",
                    "value": f"{timesheet['name']}::{detail['activity_type']}"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Close"},
                    "style": "danger",
                    "action_id": "close_item",
                    "value": f"{timesheet['name']}::{detail['activity_type']}"
                }
            ]
        })
        blocks.append({"type": "divider"})

    modal_view = {
        "type": "modal",
        "callback_id": "batch_timesheet_points",
        "title": {"type": "plain_text", "text": "Update Timesheet Points"},
        "blocks": blocks,
        "close": {"type": "plain_text", "text": "Close"}
    }

    slack_client.views_push(trigger_id=trigger_id, view=modal_view)

# -------------------------
# UPDATE MODAL
# -------------------------
def update_modal(view_id, current_timesheet, all_timesheets, index):
    modal_view = {
        "type": "modal",
        "callback_id": "timesheet_points_update",
        "private_metadata": json.dumps({"timesheets": all_timesheets, "current_index": index}),
        "title": {"type": "plain_text", "text": "Update Timesheet Points"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Timesheet:* {current_timesheet['name']}\n*Activity:* {current_timesheet['activity_type']}\n*Weightage:* {current_timesheet['custom_weightage']}"
                }
            },
            {
                "type": "input",
                "block_id": "points_input",
                "element": {
                    "type": "static_select",
                    "action_id": "points_value",
                    "placeholder": {"type": "plain_text", "text": "Select points"},
                    "options": [{"text": {"type": "plain_text", "text": str(p)}, "value": str(p)} for p in range(0, 105, 5)]
                },
                "label": {"type": "plain_text", "text": "Points"}
            }
        ],
        "submit": {"type": "plain_text", "text": "Save"},
        "close": {"type": "plain_text", "text": "Close"}
    }
    slack_client.views_update(view_id=view_id, view=modal_view)




# -------------------------
# SLASH COMMAND HANDLER

@frappe.whitelist(allow_guest=True)
def slack_command():
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    from collections import defaultdict
    import json

    payload = frappe.form_dict
    trigger_id = payload.get("trigger_id")

    # 🔒 Browser-safe fallback (HTML message)
    if not trigger_id:
        if frappe.request and "text/html" in frappe.get_request_header("Accept", ""):
            return """
                <html><body>
                <h3>Slack Timesheet Modal Endpoint</h3>
                <p>This endpoint is designed to be used from a Slack slash command.</p>
                <p>If you're seeing this in the browser, it means no <code>trigger_id</code> was provided.</p>
                <p>Try executing <code>/your-slash-command</code> in Slack to use this modal.</p>
                </body></html>
            """
        # Slack or API clients fallback
        return Response(
            response=json.dumps({
                "response_type": "ephemeral",
                "text": "⚠️ No trigger ID received from Slack."
            }),
            status=200,
            mimetype="application/json"
        )

    slack_token = frappe.conf.slack_bot_token
    slack_client = WebClient(token=slack_token)

    # Query today's timesheet entries for employee 1223 with missing points
    rows = frappe.db.sql("""
        SELECT ts.name AS timesheet_name,
               tsd.activity_type,
               tsd.custom_weightage,
               tsd.name AS detail_name
        FROM `tabTimesheet` ts
        JOIN `tabTimesheet Detail` tsd ON ts.name = tsd.parent
        WHERE ts.custom_from_date = CURDATE()
          AND ts.employee = %s
          AND (tsd.custom_points IS NULL OR tsd.custom_points <= 0)
        ORDER BY ts.name
    """, ("1223",), as_dict=True)

    if not rows:
        slack_client.chat_postEphemeral(
            channel=payload.get("channel_id"),
            user=payload.get("user_id"),
            text="✅ No timesheet entries found for employee `1223` with missing points today."
        )
        return Response(response="{}", status=200, mimetype="application/json")

    # Group timesheet rows by timesheet name
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["timesheet_name"]].append(row)

    blocks = []
    block_count = 0
    block_limit = 95

    for ts_name, activities in grouped.items():
        if block_count + len(activities) * 2 + 3 > block_limit:
            break

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Timesheet:* {ts_name}"
            }
        })
        block_count += 1

        for activity in activities:
            detail_id = activity["detail_name"]
            activity_label = (activity["activity_type"] or "")[:100].replace('\n', ' ')
            weight = activity.get("custom_weightage") or 0

            blocks.append({
                "type": "section",
                "block_id": f"section_{detail_id}",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Activity:* {activity_label}\n*Weightage:* {weight}"
                }
            })
            blocks.append({
                "type": "input",
                "block_id": f"input_points_{detail_id}",
                "label": {
                    "type": "plain_text",
                    "text": f"Points for {activity_label}"
                },
                "element": {
                    "type": "static_select",
                    "action_id": f"select_points_{detail_id}",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Choose points"
                    },
                    "options": [
                        {
                            "text": {"type": "plain_text", "text": str(p)},
                            "value": str(p)
                        } for p in range(0, 105, 5)
                    ]
                }
            })
            block_count += 2

    # Construct modal view
    modal_view = {
        "type": "modal",
        "callback_id": "timesheet_activity_update",
        "title": {
            "type": "plain_text",
            "text": "Timesheet Points"
        },
        "submit": {
            "type": "plain_text",
            "text": "Submit"
        },
        "close": {
            "type": "plain_text",
            "text": "Cancel"
        },
        "blocks": blocks
    }

    # Open the modal
    try:
        slack_client.views_open(trigger_id=trigger_id, view=modal_view)
    except SlackApiError as e:
        error_msg = e.response.get("error", "unknown_error")
        frappe.log_error(json.dumps(e.response.data), "Slack Modal Error")
        return Response(
            response=json.dumps({
                "response_type": "ephemeral",
                "text": f"❌ Slack error: `{error_msg}`"
            }),
            status=200,
            mimetype="application/json"
        )

    return Response(response="{}", status=200, mimetype="application/json")

# SLACK INTERACTION HANDLER
# -------------------------
@frappe.whitelist(allow_guest=True)
def slack_interactions():
    payload = json.loads(frappe.form_dict.get("payload", "{}"))

    if payload.get("type") == "view_submission" and payload["view"]["callback_id"] == "timesheet_points_update":
        metadata = json.loads(payload["view"]["private_metadata"])
        timesheets = metadata["timesheets"]
        current_index = metadata["current_index"]

        selected_points = payload["view"]["state"]["values"]["points_input"]["points_value"]["selected_option"]["value"]
        ts_name = timesheets[current_index]["name"]

        frappe.db.sql("""
            UPDATE `tabTimesheet Detail`
            SET custom_points = %s
            WHERE parent = %s
        """, (selected_points, ts_name))
        frappe.db.commit()

        if current_index + 1 < len(timesheets):
            next_index = current_index + 1
            next_ts = timesheets[next_index]
            update_modal(payload["view"]["id"], next_ts, timesheets, next_index)
        else:
            return json.dumps({"response_action": "clear"})

    return ""
