import frappe
import requests


WHISPER_URL = "http://13.201.29.122:8000/transcribe"
WHISPER_SECRET = "homegenie_whisper_secure_2026"


@frappe.whitelist()
def queue_call_transcription(docname):

    if not docname:
        frappe.throw("Call Log name is required")

    doc = frappe.get_doc("Call Log", docname)

    if not doc.custom_url:
        frappe.throw("Recording URL not found")

    frappe.db.set_value(
        "Call Log",
        docname,
        "transcription_status",
        "Processing",
        update_modified=False
    )

    frappe.db.commit()

    frappe.enqueue(
        "itgenie.lead_calling.transcription.process_call_transcription",
        queue="long",
        timeout=900,
        docname=docname
    )

    return {
        "status": "processing",
        "message": "Transcription processing"
    }


def process_call_transcription(docname):

    frappe.db.set_value(
        "Call Log",
        docname,
        "transcription_status",
        "Processing",
        update_modified=False
    )

    frappe.db.commit()

    doc = frappe.get_doc("Call Log", docname)

    if not doc.custom_url:

        frappe.db.set_value(
            "Call Log",
            docname,
            "transcription_status",
            "Failed",
            update_modified=False
        )

        frappe.db.commit()

        return

    try:

        response = requests.post(
            WHISPER_URL,
            headers={
                "Authorization": f"Bearer {WHISPER_SECRET}",
                "Content-Type": "application/json"
            },
            json={
                "recording_url": doc.custom_url
            },
            timeout=900
        )

        if response.status_code != 200:

            frappe.db.set_value(
                "Call Log",
                docname,
                "transcription_status",
                "Failed",
                update_modified=False
            )

            frappe.db.commit()

            frappe.log_error(
                response.text,
                "Whisper Transcription Failed"
            )

            return

        data = response.json()

        transcript = data.get("transcript", "")

        frappe.db.set_value(
            "Call Log",
            docname,
            {
                "transcript": transcript,
                "transcription_status": "Completed"
            },
            update_modified=False
        )

        frappe.db.commit()

    except Exception:

        frappe.db.set_value(
            "Call Log",
            docname,
            "transcription_status",
            "Failed",
            update_modified=False
        )

        frappe.db.commit()

        frappe.log_error(
            frappe.get_traceback(),
            "Call Log Transcription Error"
        )
