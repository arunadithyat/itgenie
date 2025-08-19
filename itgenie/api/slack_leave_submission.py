import frappe
import json
import requests


@frappe.whitelist(allow_guest=True)
def leave_submission_handler():
    try:
        payload = json.loads(frappe.form_dict.get("payload"))
        view_state = payload["view"]["state"]["values"]
        user_id = payload["user"]["id"]

        emp_id = view_state["emp_id"]["value"]["value"]
        leave_type = view_state["leave_type"]["value"]["selected_option"]["value"]
        from_date = view_state["from_date"]["value"]["selected_date"]
        to_date = view_state["to_date"]["value"]["selected_date"]
        reason = view_state["reason"]["value"]["value"]

        # ✅ Enqueue side effects
        frappe.enqueue(
            method=create_leave_and_notify,
            queue="default",
            timeout=30,
            employee=emp_id,
            leave_type=leave_type,
            from_date=from_date,
            to_date=to_date,
            reason=reason,
            user_id=user_id
        )

        # ✅ Return immediately to close modal
        return {"response_action": "clear"}

    except Exception as e:
        frappe.logger().error("Slack leave submission error: " + frappe.get_traceback())
        return {
            "response_action": "errors",
            "errors": {
                "reason": "Leave submission failed. Try again."
            }
        }


def create_leave_and_notify(employee, leave_type, from_date, to_date, reason, user_id):
    try:
        doc = frappe.get_doc({
            "doctype": "Leave Application",
            "employee": employee,
            "leave_type": leave_type,
            "from_date": from_date,
            "to_date": to_date,
            "description": reason
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        # Send Slack confirmation
        slack_token = frappe.conf.slack_bot_token
        message = f"✅ Your leave from *{from_date}* to *{to_date}* for `{leave_type}` was submitted."

        requests.post("https://slack.com/api/chat.postMessage", headers={
            "Authorization": f"Bearer {slack_token}",
            "Content-Type": "application/json"
        }, json={
            "channel": user_id,
            "text": message
        })

    except Exception as e:
        frappe.logger().error("Slack notify/create failed: " + frappe.get_traceback())
