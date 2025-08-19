import frappe
import json
import requests
from werkzeug.wrappers import Response


# -------------------------------
# Open the modal
# -------------------------------
@frappe.whitelist(allow_guest=True)
def timesheet_points_modal():
    payload = frappe.request.form
    trigger_id = payload.get("trigger_id")
    today = frappe.utils.today()

    ts_id = ""  # to avoid undefined reference later

    timesheets = frappe.get_all(
        "Timesheet",
        filters={"custom_from_date": today, "employee": "1223", "docstatus": 0},
        fields=["name", "employee", "employee_name"],
    )

    blocks = []

    if not timesheets:
        blocks.append({
            "type": "section",
            "text": {"type": "plain_text", "text": "✅ No Timesheets found for today."}
        })
    else:
        ts = timesheets[0]
        ts_id = ts["name"]
        employee_name = ts["employee_name"]

        # Header
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Timesheet:* {ts_id} - {employee_name}"}
        })

        # Child rows (Details)
        time_logs = frappe.get_all(
            "Timesheet Detail",
            filters={"parent": ts_id},
            fields=["name", "idx", "activity_type", "custom_points", "custom_weightage"]
        )
        time_logs = sorted(time_logs, key=lambda x: x["idx"])

        for log in time_logs:
            idx = log["idx"]
            activity_type = log.get("activity_type", "") or ""
            weightage = float(log.get("custom_weightage") or 0.0)
            if weightage == 0.0:
                continue  # skip 0% weightage

            label = f"{activity_type} - {weightage:.1f}%"

            element = {
                "type": "external_select",
                "action_id": "points_input",
                "min_query_length": 0
            }

            blocks.append({
                "type": "input",
                "block_id": f"points_block_{idx}",
                "element": element,
                "label": {"type": "plain_text", "text": label[:75]}
            })

    # ✅ Provide JSON private_metadata so the submit handler can read the timesheet id
    private_metadata = json.dumps({"timesheet": ts_id})

    modal_view = {
        "type": "modal",
        "callback_id": "update_multiple_custom_points",
        "title": {"type": "plain_text", "text": "Update Activity Points"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": blocks,
        "private_metadata": private_metadata
    }

    headers = {
        "Authorization": f"Bearer {frappe.conf.slack_bot_token}",
        "Content-Type": "application/json"
    }

    res = requests.post(
        "https://slack.com/api/views.open",
        headers=headers,
        json={"trigger_id": trigger_id, "view": modal_view}
    )

    data = res.json()
    if not data.get("ok"):
        frappe.log_error(json.dumps(data, indent=2), "Slack Modal Error")
        frappe.response["message"] = "Failed to open modal"
        frappe.response["status_code"] = 400
    else:
        frappe.response["status_code"] = 200


# -------------------------------
# Slack external select options handler
# -------------------------------
@frappe.whitelist(allow_guest=True)
def slack_external_options():
    try:
        payload_str = frappe.local.form_dict.get("payload")
        payload = json.loads(payload_str) if payload_str else {}

        action_id = payload.get("action_id")
        if action_id != "points_input":
            return Response(json.dumps({"options": []}), status=200, mimetype="application/json")

        # Generate 0 to 100 step 5
        options = [
            {
                "text": {"type": "plain_text", "text": str(i)},
                "value": str(i)
            }
            for i in range(0, 105, 5)
        ]

        return Response(json.dumps({"options": options}), status=200, mimetype="application/json")

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Slack External Select Error")
        return Response(json.dumps({"options": []}), status=200, mimetype="application/json")


# -------------------------------
# Handle view_submission, update points synchronously, close modal
# -------------------------------
@frappe.whitelist(allow_guest=True)
def handle_timesheet_points_update():
    try:
        payload = None
        payload_str = frappe.local.form_dict.get("payload")
        if payload_str:
            try:
                payload = json.loads(payload_str)
            except Exception:
                frappe.log_error("Slack payload decode error", (payload_str[:3000] if isinstance(payload_str, str) else "non-str"))
        if not payload:
            data = frappe.request.get_json(silent=True)
            if isinstance(data, dict):
                payload = data

        updated_rows = 0
        timesheet_id = None

        if isinstance(payload, dict) and payload.get("type") == "view_submission":
            view = payload.get("view") or {}
            state = (view.get("state") or {}).get("values") or {}

            meta_raw = view.get("private_metadata")
            if meta_raw:
                try:
                    meta = json.loads(meta_raw) if isinstance(meta_raw, str) else meta_raw
                    timesheet_id = (meta or {}).get("timesheet")
                except Exception:
                    pass

            if not timesheet_id:
                for blk in view.get("blocks") or []:
                    if blk.get("type") == "section":
                        text = ((blk.get("text") or {}).get("text") or "").strip()
                        if "Timesheet:" in text:
                            part = text.split("Timesheet:")[-1].strip()
                            timesheet_id = part.split(" - ")[0].strip()
                            break

            if not timesheet_id:
                frappe.log_error("Timesheet id not found in submission", json.dumps(payload)[:2000])
                first_block = next(iter(state.keys()), "__all__")
                err_payload = {
                    "response_action": "errors",
                    "errors": { first_block: "Timesheet ID not found in submission." }
                }
                return Response(json.dumps(err_payload), status=200, mimetype="application/json")

            selections = {}
            for block_id, actions in state.items():
                action = actions.get("points_input") or next(iter(actions.values()), {})
                selected = (action.get("selected_option") or {}).get("value")
                if selected is not None:
                    try:
                        selections[block_id] = int(selected)
                    except Exception:
                        pass

            total_points = sum(selections.values())
            if total_points > 100:
                first_block = next(iter(selections.keys()), "__all__")
                err_payload = {
                    "response_action": "errors",
                    "errors": {
                        first_block: f"Total points cannot exceed 100. Current total: {total_points}."
                    }
                }
                frappe.log_error("Timesheet points validation failed", f"Timesheet={timesheet_id} | total={total_points} | selections={selections}")
                return Response(json.dumps(err_payload), status=200, mimetype="application/json")

            def idx_from_block(block_id: str):
                try:
                    return int((block_id or "").split("_")[-1])
                except Exception:
                    return None

            ts = frappe.get_doc("Timesheet", timesheet_id)

            if ts.docstatus == 1:
                first_block = next(iter(selections.keys()), "__all__") or "__all__"
                err_payload = {
                    "response_action": "errors",
                    "errors": {
                        first_block: "This Timesheet is already submitted and cannot be updated."
                    }
                }
                frappe.log_error("Timesheet already submitted", f"Timesheet={timesheet_id} | docstatus=1")
                return Response(json.dumps(err_payload), status=200, mimetype="application/json")

            detail_by_idx = {d.idx: d for d in ts.time_logs}

            for block_id, points in selections.items():
                target_idx = idx_from_block(block_id)
                row = detail_by_idx.get(target_idx) if target_idx else None
                if row:
                    row.db_set("custom_points", points, update_modified=False)
                    updated_rows += 1

            frappe.db.commit()

            try:
                ts.reload()
                if ts.docstatus == 0:
                    ts.submit()
                    frappe.db.commit()
                    frappe.log_error("Timesheet points updated & submitted", f"Timesheet={timesheet_id} | updated_rows={updated_rows} | total_points={total_points}")
                else:
                    frappe.log_error("Timesheet already submitted post-update", f"Timesheet={timesheet_id}")
            except Exception as e:
                first_block = next(iter(selections.keys()), "__all__")
                err_payload = {
                    "response_action": "errors",
                    "errors": {
                        first_block: f"Submit failed: {frappe.get_message(e) or str(e)}"
                    }
                }
                frappe.log_error("Timesheet submit failed", f"{frappe.get_traceback()}\nTimesheet={timesheet_id}")
                return Response(json.dumps(err_payload), status=200, mimetype="application/json")

        return Response("{}", status=200, mimetype="application/json")

    except Exception:
        frappe.log_error("Slack Modal Fatal Error", frappe.get_traceback())
        return Response("{}", status=200, mimetype="application/json")
