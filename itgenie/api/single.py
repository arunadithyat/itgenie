import frappe
@frappe.whitelist()
def production_records(company, filter, limit=500):
    if not company or not filter:
        frappe.throw("Company and filter are required")

    limit = int(limit or 500)

    data = run_query(company, filter, limit)

    return {
        "company": company,
        "filter": filter,
        "mode": data["mode"],
        "records": data["records"],
        "total": data["total"],
    }

QUERY_MAP = {
    "qty_ytd": {"mode": "qty", "date_range": "fiscal_year"},
    "qty_qtd": {"mode": "qty", "date_range": "quarter"},
    "qty_mtd": {"mode": "qty", "date_range": "month"},
    "qty_today": {"mode": "qty", "date_range": "today"},
    "in_progress": {"mode": "status", "extra_cond": "wo.status='In Process'"},
    "pending": {"mode": "status", "extra_cond": "wo.status='Not Started'"},
    "overdue": {"mode": "status", "extra_cond": "wo.status NOT IN ('Completed','Cancelled','Closed') AND wo.planned_end_date < CURDATE()"},
    "rework": {"mode": "status", "extra_cond": "wo.custom_need_rework=1"},
    "completed_on_time": {"mode": "status", "extra_cond": "wo.status IN ('Completed','Closed') AND DATE(wo.actual_end_date) <= DATE(wo.creation)"},
    "delayed": {"mode": "status", "extra_cond": "wo.status IN ('Completed','Closed') AND (DATE(wo.actual_end_date) > DATE(wo.creation) OR wo.actual_end_date IS NULL)"},
    "to_manufacture": {"mode": "manufacture"},
}

def run_query(company, filter, limit):
    config = QUERY_MAP.get(filter)
    if not config:
        frappe.throw(f"Unknown filter: {filter}")

    if config["mode"] == "qty":
        start, end = get_date_range(config["date_range"])
        return qty_query(company, start, end, limit, exact=(filter=="qty_today"))

    # elif config["mode"] == "status":
    #     start, end = get_date_range("fiscal_year")  # most status queries are FY
    #     return status_query(company, config["extra_cond"], start, end, limit)

    # elif config["mode"] == "manufacture":
    #     return manufacture_query(company, limit)
    
    # elif filter == "trend_monthly":
    #     return trend_monthly_query(company, limit or 12)
    
    # elif filter == "trend_mtd":
    #     return trend_last_12_months(company, limit or 12)



COMPANY_CONFIG = {
    "Homegenie Building Products Private Limited": {
        "warehouses": ("Madurai - HBPPL","Finished Goods - HBPPL","Chemical Plant Rocotile - HBPPL"),
        "item_groups": ("Rocotile","SMF Chemical"),
    },
    "Bioman Sewage Solutions Private Limited": {
        "warehouses": ("Finished Goods - BSSP",),
        "item_groups": ("Bio Tank-FG","Bioman","Bio Tanks"),
    },
    "Doortisan Creations Private Limited": {
        "warehouses": ("Finished Goods - DPl",),
        "item_groups": ("Teak Shutter","Teak Frame","Flush Door", ...),
    },
    "Timbe Windows Private Limited": {
        "warehouses": ("Finished Goods - TUWPL",),
        "item_groups": ("Frames","Shutters", ...),
    },
}

def qty_query(company, start, end, limit, exact=False):
    cfg = COMPANY_CONFIG[company]
    join_item = "LEFT JOIN `tabItem` it ON it.name = wo.production_item"
    base_where = f"""
        AND wo.fg_warehouse IN {cfg["warehouses"]}
        AND wo.status NOT IN ('Cancelled','Draft')
        AND wo.company=%s
        AND it.item_group IN {cfg["item_groups"]}
    """

    if exact:
        date_cond = "DATE(wo.creation) = %s"
        params = (start, company, limit)
    else:
        date_cond = "DATE(wo.creation) >= %s AND DATE(wo.creation) < %s"
        params = (start, end, company, limit)

    rows = frappe.db.sql(f"""
        SELECT wo.production_item AS item_code,
               it.item_name,
               it.stock_uom AS uom,
               it.item_group,
               SUM(wo.produced_qty) AS qty
        FROM `tabWork Order` wo {join_item}
        WHERE {date_cond}
        {base_where}
        GROUP BY wo.production_item, it.item_name, it.stock_uom, it.item_group
        HAVING SUM(wo.produced_qty) > 0
        ORDER BY qty DESC
        LIMIT %s
    """, params, as_dict=True)

    return {"mode": "qty", "records": rows, "total": sum(r.qty for r in rows)}

# def trend_monthly_query(company, months=12):
#     """Return monthly production totals for the last N months"""
#     rows = frappe.db.sql("""
#         SELECT DATE_FORMAT(wo.creation, '%%Y-%%m') AS month,
#                SUM(wo.produced_qty) AS qty
#         FROM `tabWork Order` wo
#         LEFT JOIN `tabItem` it ON it.name = wo.production_item
#         WHERE wo.company=%s
#           AND wo.status NOT IN ('Cancelled','Draft')
#         GROUP BY DATE_FORMAT(wo.creation, '%%Y-%%m')
#         ORDER BY month DESC
#         LIMIT %s
#     """, (company, months), as_dict=True)

#     # Reverse so oldest → newest
#     rows = rows[::-1]

#     return {
#         "labels": [r.month for r in rows],
#         "values": [float(r.qty or 0) for r in rows],
#         "mode": "trend"
#     }

# def trend_last_12_months(company, limit=12):
#     today = frappe.utils.today()
#     months = []
#     results = []

#     for i in range(limit-1, -1, -1):
#         month_start = frappe.utils.add_months(frappe.utils.get_first_day(today), -i)
#         month_end = frappe.utils.add_months(month_start, 1)
#         res = production_records(company=company, filter="qty_mtd", limit=500, start_date=month_start, end_date=month_end)
#         results.append({
#             "month": month_start.strftime("%b %Y"),
#             "total": res["total"] if res else 0
#         })
    
#     return {
#         "labels": [r["month"] for r in results],
#         "values": [r["total"] for r in results],
#         "mode": "trend"
#     }
# def manufacture_query(company, limit=500):
#     """Dispatch manufacture requirement query based on company"""
#     if company == "Homegenie Building Products Private Limited":
#         return _homegenie_need_to_manufacture()
#     elif company == "Bioman Sewage Solutions Private Limited":
#         return _bioman_to_manufacture(limit)
#     elif company == "Doortisan Creations Private Limited":
#         return _doortisan_to_manufacture(limit)
#     elif company == "Timbe Windows Private Limited":
#         return _timbe_to_manufacture(limit)
#     else:
#         return {"records": [], "total": 0, "mode": "qty"}
# def _doortisan_to_manufacture(limit=500):
#     rows = frappe.db.sql(""" ... """, (int(limit),), as_dict=True)

#     rows = [{**r, "qty": float(r["qty"])} for r in rows]

#     return {
#         "records": rows,
#         "total": sum(r["qty"] for r in rows),
#         "mode": "qty"
#     }
# def _timbe_to_manufacture(limit=500):
#     rows = frappe.db.sql(""" ... """, ('%Installation%', 'Fully Billed', 'Sales', 'FT-2x4', int(limit)), as_dict=True)

#     rows = [{**r, "qty": float(r["qty"])} for r in rows]

#     return {
#         "records": rows,
#         "total": sum(r["qty"] for r in rows),
#         "mode": "qty"
#     }

# from frappe.utils import getdate, add_months, today, get_first_day

# def get_date_range(period: str):
#     """Return (start_date, end_date) tuple for fiscal_year, quarter, month, today"""
#     today_date = getdate(today())

#     # Fiscal Year: Apr → Mar
#     if period == "fiscal_year":
#         fy_start_year = today_date.year if today_date.month >= 4 else today_date.year - 1
#         fy_start = getdate(f"{fy_start_year}-04-01")
#         fy_end = getdate(f"{fy_start_year+1}-04-01")
#         return fy_start, fy_end

#     # Quarter
#     if period == "quarter":
#         fy_start_year = today_date.year if today_date.month >= 4 else today_date.year - 1
#         fiscal_month = (today_date.month - 4) % 12
#         q_index = fiscal_month // 3
#         q_start_month = [4, 7, 10, 1][q_index]
#         q_start_year = fy_start_year if q_index < 3 else fy_start_year + 1
#         q_start = getdate(f"{q_start_year}-{str(q_start_month).zfill(2)}-01")
#         q_end = add_months(q_start, 3)
#         return q_start, q_end

#     # Month
#     if period == "month":
#         month_start = getdate(f"{today_date.year}-{str(today_date.month).zfill(2)}-01")
#         month_end = add_months(month_start, 1)
#         return month_start, month_end

#     # Today (exact day)
#     if period == "today":
#         return today_date, today_date

#     # Default: return today as both start & end
#     return today_date, today_date

# def status_query(company, extra_cond, start=None, end=None, limit=500):
#     """Generic status-based query (in_progress, pending, overdue, etc.)"""
#     cfg = COMPANY_CONFIG[company]
#     join_item = "LEFT JOIN `tabItem` it ON it.name = wo.production_item"
#     where_cond = f"""
#         {extra_cond}
#         AND wo.fg_warehouse IN {cfg["warehouses"]}
#         AND wo.status NOT IN ('Cancelled','Draft')
#         AND wo.company=%s
#         AND it.item_group IN {cfg["item_groups"]}
#     """

#     date_filter = ""
#     params = [company, limit]
#     if start and end:
#         date_filter = "AND DATE(wo.creation) >= %s AND DATE(wo.creation) < %s"
#         params = [start, end, company, limit]

#     rows = frappe.db.sql(f"""
#         SELECT wo.production_item AS item_code,
#                it.item_name,
#                it.stock_uom AS uom,
#                it.item_group,
#                SUM(wo.produced_qty) AS qty
#         FROM `tabWork Order` wo {join_item}
#         WHERE {where_cond}
#         {date_filter}
#         GROUP BY wo.production_item, it.item_name, it.stock_uom, it.item_group
#         HAVING SUM(wo.produced_qty) > 0
#         ORDER BY qty DESC
#         LIMIT %s
#     """, tuple(params), as_dict=True)

#     return {"mode": "qty", "records": rows, "total": sum(r.qty for r in rows)}






