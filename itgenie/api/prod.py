import frappe

@frappe.whitelist()
def production_records(company=None, filter=None, limit=500):
    """Master API: routes to company-specific query helpers"""
    if not company or not filter:
        frappe.throw("Company and filter are required")

    limit = int(limit or 500)

    

    # ----------------- HOMEGENIE -----------------
    if company == "Homegenie Building Products Private Limited":
        if filter == "qty_ytd":
            return _homegenie_ytd(limit)
        elif filter == "qty_qtd":
            return _homegenie_qtd(limit)
        elif filter == "qty_mtd":
            return _homegenie_mtd(limit)
        elif filter == "qty_today":
            return _homegenie_today(limit)
        elif filter == "in_progress":
            return _homegenie_in_progress(limit)
        elif filter == "pending":
            return _homegenie_pending(limit)
        elif filter == "overdue":
            return _homegenie_overdue(limit)
        elif filter == "rework":
            return _homegenie_rework(limit)
        elif filter == "to_manufacture":
            return _homegenie_need_to_manufacture()
        elif filter == "delayed":
            return _homegenie_delayed(limit)
        elif filter == "completed_on_time":
            return _homegenie_on_time(limit)
        
    # ----------------- BIOMAN -----------------
    elif company == "Bioman Sewage Solutions Private Limited":
        if filter == "qty_ytd":
           return _bioman_ytd(limit)
        elif filter == "qty_qtd":
           return _bioman_qtd(limit)
        elif filter == "qty_mtd":
          return _bioman_mtd(limit)
        elif filter == "qty_today":
          return _bioman_today(limit)
        elif filter == "in_progress":
          return _bioman_in_progress(limit)
        elif filter == "pending":
          return _bioman_pending(limit)
        elif filter == "overdue":
          return _bioman_overdue(limit)
        elif filter == "rework":
          return _bioman_rework(limit)
        elif filter == "to_manufacture":
          return _bioman_to_manufacture(limit)
        elif filter == "delayed":
          return _bioman_delayed(limit)
        elif filter == "completed_on_time":
          return _bioman_on_time(limit)
        
        # ----------------- DOORTISAN -----------------
    elif company == "Doortisan Creations Private Limited":
        if filter == "qty_ytd":
         return _doortisan_ytd(limit)
        elif filter == "qty_qtd":
         return _doortisan_qtd(limit)
        elif filter == "qty_mtd":
         return _doortisan_mtd(limit)
        elif filter == "qty_today":
         return _doortisan_today(limit)
        elif filter == "in_progress":
         return _doortisan_in_progress(limit)
        elif filter == "pending":
         return _doortisan_pending(limit)
        elif filter == "overdue":
         return _doortisan_overdue(limit)
        elif filter == "rework":
         return _doortisan_rework(limit)
        elif filter == "to_manufacture":
         return _doortisan_to_manufacture(limit)
        elif filter == "delayed":
          return _doortisan_delayed(limit)
        elif filter == "completed_on_time":
          return _doortisan_on_time(limit)
        
        # ----------------- TIMBE -----------------
        
    elif company == "Timbe Windows Private Limited":
        if filter == "qty_ytd":
         return _timbe_ytd(limit)
        elif filter == "qty_qtd":
         return _timbe_qtd(limit)
        elif filter == "qty_mtd":
          return _timbe_mtd(limit)
        elif filter == "qty_today":
         return _timbe_today(limit)
        elif filter == "in_progress":
         return _timbe_in_progress(limit)
        elif filter == "pending":
          return _timbe_pending(limit)
        elif filter == "overdue":
         return _timbe_overdue(limit)
        elif filter == "rework":
         return _timbe_rework(limit)
        elif filter == "to_manufacture":
         return _timbe_to_manufacture(limit)
        elif filter == "completed_on_time":
         return _timbe_on_time(limit)
        elif filter == "delayed":
         return _timbe_delayed(limit)




# ==========================
# HOMEGENIE HELPERS
# ==========================

def _homegenie_ytd(limit=500):
    today_date   = frappe.utils.getdate(frappe.utils.today())
    fy_start_year = today_date.year if today_date.month >= 4 else today_date.year - 1
    fy_start      = frappe.utils.getdate(f"{fy_start_year}-04-01")
    fy_next_start = frappe.utils.getdate(f"{fy_start_year+1}-04-01")
    return _homegenie_qty_query(fy_start, fy_next_start, limit)


def _homegenie_qtd(limit=500):
    today_date   = frappe.utils.getdate(frappe.utils.today())
    fy_start_year = today_date.year if today_date.month >= 4 else today_date.year - 1
    fiscal_month  = (today_date.month - 4) % 12
    q_index       = fiscal_month // 3
    q_start_month = [4, 7, 10, 1][q_index]
    q_start_year  = fy_start_year if q_index < 3 else fy_start_year + 1
    q_start       = frappe.utils.getdate(f"{q_start_year}-{str(q_start_month).zfill(2)}-01")
    q_next_start  = frappe.utils.add_months(q_start, 3)
    return _homegenie_qty_query(q_start, q_next_start, limit)


def _homegenie_mtd(limit=500):
    today_date   = frappe.utils.getdate(frappe.utils.today())
    month_start  = frappe.utils.getdate(f"{today_date.year}-{str(today_date.month).zfill(2)}-01")
    month_next   = frappe.utils.add_months(month_start, 1)
    return _homegenie_qty_query(month_start, month_next, limit)


def _homegenie_today(limit=500):
    today_date = frappe.utils.getdate(frappe.utils.today())
    return _homegenie_qty_query(today_date, today_date, limit, exact=True)


def _homegenie_qty_query(start_date, end_date=None, limit=500, exact=False):
    join_item = "LEFT JOIN `tabItem` it ON it.name = wo.production_item"
    base_where = """
        AND wo.fg_warehouse IN ('Madurai - HBPPL','Finished Goods - HBPPL','Chemical Plant Rocotile - HBPPL')
        AND wo.status NOT IN ('Cancelled','Draft')
        AND wo.company REGEXP 'Homegenie'
        AND it.item_group IN ('Rocotile','SMF Chemical')
    """

    if exact:
        date_cond = "DATE(wo.creation) = %s"
        params = (start_date, limit)
    else:
        date_cond = "DATE(wo.creation) >= %s AND DATE(wo.creation) < %s"
        params = (start_date, end_date, limit)

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

    return {"records": rows, "total": sum(r.qty for r in rows), "mode": "qty"}


# --- Status buckets ---
def _homegenie_in_progress(limit=500):
    return _homegenie_status_query("wo.status='In Process'", limit)

def _homegenie_pending(limit=500):
    return _homegenie_status_query("wo.status='Not Started'", limit)

def _homegenie_overdue(limit=500):
    return _homegenie_status_query(
        "wo.status NOT IN ('Completed','Cancelled','Closed') AND wo.planned_end_date < CURDATE()", limit
    )

def _homegenie_rework(limit=500):
    return _homegenie_status_query("wo.custom_need_rework=1", limit)

# def _homegenie_on_time(limit=500):
#     today_date = frappe.utils.getdate(frappe.utils.today())
#     fy_start_year = today_date.year if today_date.month >= 4 else today_date.year - 1
#     fy_start = frappe.utils.getdate(f"{fy_start_year}-04-01")
#     fy_next_start = frappe.utils.getdate(f"{fy_start_year+1}-04-01")

#     return _homegenie_status_query(
#         "wo.status IN ('Completed','Closed') AND DATE(wo.actual_end_date) <= DATE(wo.planned_end_date)",
#         limit, fy_start, fy_next_start
#     )

def _homegenie_on_time(limit=500):
    """On-time Work Orders for current fiscal year"""

    today_date   = frappe.utils.getdate(frappe.utils.today())
    fy_start_year = today_date.year if today_date.month >= 4 else today_date.year - 1
    fy_start      = frappe.utils.getdate(f"{fy_start_year}-04-01")
    fy_next_start = frappe.utils.getdate(f"{fy_start_year+1}-04-01")

    return _homegenie_status_query(
        "wo.status IN ('Completed','Closed') AND DATE(wo.actual_end_date) <= DATE(wo.creation)",
        limit, fy_start, fy_next_start
    )

 

def _homegenie_delayed(limit=500):
    today_date   = frappe.utils.getdate(frappe.utils.today())
    fy_start_year = today_date.year if today_date.month >= 4 else today_date.year - 1
    fy_start      = frappe.utils.getdate(f"{fy_start_year}-04-01")
    fy_next_start = frappe.utils.getdate(f"{fy_start_year+1}-04-01")
    return _homegenie_status_query(
        "wo.status IN ('Completed','Closed') AND (DATE(wo.actual_end_date) > DATE(wo.creation) OR wo.actual_end_date IS NULL)",
        limit, fy_start, fy_next_start
    )


def _homegenie_status_query(extra_cond, limit=500, start_date=None, end_date=None):
    join_item = "LEFT JOIN `tabItem` it ON it.name = wo.production_item"
    where_cond = f"""
        {extra_cond}
        AND wo.fg_warehouse IN ('Madurai - HBPPL','Finished Goods - HBPPL','Chemical Plant Rocotile - HBPPL')
        AND wo.status NOT IN ('Cancelled','Draft')
        AND wo.company REGEXP 'Homegenie'
        AND it.item_group IN ('Rocotile','SMF Chemical')
    """

    date_filter = ""
    params = [limit]
    if start_date and end_date:
        date_filter = "AND DATE(wo.creation) >= %s AND DATE(wo.creation) < %s"
        params = [start_date, end_date, limit]

    rows = frappe.db.sql(f"""
        SELECT wo.production_item AS item_code,
               it.item_name,
               it.stock_uom AS uom,
               it.item_group,
               SUM(wo.produced_qty) AS qty
        FROM `tabWork Order` wo {join_item}
        WHERE {where_cond}
        {date_filter}
        GROUP BY wo.production_item, it.item_name, it.stock_uom, it.item_group
        HAVING SUM(wo.produced_qty) > 0
        ORDER BY qty DESC
        LIMIT %s
    """, tuple(params), as_dict=True)

    return {"records": rows, "total": sum(r.qty for r in rows), "mode": "qty"}


# --- Need to Manufacture ---
def _homegenie_need_to_manufacture():
    to_manufacture = frappe.db.sql("""
        SELECT
            SOI.item_code,
            SOI.item_name,
            SUM(SOI.qty - SOI.delivered_qty) AS required,
            IFNULL(BIN.available_qty, 0) AS fg,
            IFNULL(BIN1.available_qty, 0) AS sfg,
            CASE
                WHEN (SUM(SOI.qty - SOI.delivered_qty) - IFNULL(BIN.available_qty,0) - IFNULL(BIN1.available_qty,0)) <= 0 THEN 0
                ELSE (SUM(SOI.qty - SOI.delivered_qty) - IFNULL(BIN.available_qty,0) - IFNULL(BIN1.available_qty,0))
            END AS to_manufacture
        FROM `tabSales Order` SO
        LEFT JOIN `tabSales Order Item` SOI ON SO.name = SOI.parent
        LEFT JOIN (
            SELECT item_code, SUM(actual_qty) AS available_qty
            FROM `tabBin`
            WHERE warehouse NOT IN (
                'Madurai - Work in Progress - Drying - HBPPL',
                "D'Sign Doors - Work in Progress - HBPPL",
                'Madurai - Work in Progress - HBPPL',
                'Chennai - Work in Progess - HBPPL',
                'Madurai - Work in Progress - Packing - HBPPL',
                'Madurai - Work in Progress - Demoulding - HBPPL',
                'Chennai - Work in Progress - Packing - HBPPL',
                'Chennai - Work in Progress - Drying - HBPPL',
                'Chennai - Work in Progress - Demoulding  - HBPPL',
                'Madurai - Scrap Warehouse - HBPPL',
                'Chennai - Scrap Warehouse - HBPPL',
                'Damage Warehouse - HBPPL',
                'Madurai - Stores - HBPPL'
            )
            GROUP BY item_code
        ) BIN ON BIN.item_code = SOI.item_code
        LEFT JOIN (
            SELECT item_code, SUM(actual_qty) AS available_qty
            FROM `tabBin`
            WHERE warehouse IN (
                'Madurai - Work in Progress - Drying - HBPPL',
                'Madurai - Work in Progress - HBPPL',
                'Chennai - Work in Progess - HBPPL',
                'Madurai - Work in Progress - Packing - HBPPL',
                'Madurai - Work in Progress - Demoulding - HBPPL',
                'Chennai - Work in Progress - Packing - HBPPL',
                'Chennai - Work in Progress - Drying - HBPPL',
                'Chennai - Work in Progress - Demoulding  - HBPPL'
            )
            GROUP BY item_code
        ) BIN1 ON BIN1.item_code = SOI.item_code
        WHERE SO.company = 'Homegenie Building Products Private Limited'
          AND SO.billing_status != "Fully Billed"
          AND SO.status NOT IN ('Draft', 'Cancelled', 'Closed', 'Completed')
          AND SO.order_type = "Sales"
          AND SO.selling_price_list = "Standard Selling"
          AND SOI.item_code IN ('Mega', 'Mineral Grout')
        GROUP BY SOI.item_code, SOI.item_name
        HAVING to_manufacture > 0                           
    """, as_dict=True)

    return {
        "records": to_manufacture or [],
        "total": sum(r.to_manufacture for r in to_manufacture) if to_manufacture else 0,
        "mode": "qty"
    }

# ================================
# BIOMAN RECORD HELPERS
# ================================

def _bioman_qty_query(start_date, end_date=None, limit=500, exact=False):
    """Generic helper for YTD/QTD/MTD/Today quantities"""
    join_item = "LEFT JOIN `tabItem` it ON it.name = wo.production_item"
    base_where = """
        AND wo.status NOT IN ('Cancelled','Draft')
        AND wo.company REGEXP 'Bioman'
        AND it.item_group IN ('Bio Tank-FG','Bioman','Bio Tanks')
    """

    if exact:  # for Today
        date_cond = "DATE(wo.creation)=%s"
        params = (start_date, limit)
    else:
        date_cond = "DATE(wo.creation) >= %s AND DATE(wo.creation) < %s"
        params = (start_date, end_date, limit)

    rows = frappe.db.sql(
        f"""
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
        """,
        params,
        as_dict=True
    )

    return {"records": rows, "total": sum(r.qty for r in rows), "mode": "qty"}


def _bioman_ytd(limit=500):
    today_date = frappe.utils.getdate(frappe.utils.today())
    fy_start_year = today_date.year if today_date.month >= 4 else today_date.year - 1
    fy_start      = frappe.utils.getdate(f"{fy_start_year}-04-01")
    fy_next_start = frappe.utils.getdate(f"{fy_start_year+1}-04-01")
    return _bioman_qty_query(fy_start, fy_next_start, limit)


def _bioman_qtd(limit=500):
    today_date = frappe.utils.getdate(frappe.utils.today())
    fy_start_year = today_date.year if today_date.month >= 4 else today_date.year - 1
    fiscal_month  = (today_date.month - 4) % 12
    q_index       = fiscal_month // 3
    q_start_month = [4, 7, 10, 1][q_index]
    q_start_year  = fy_start_year if q_index < 3 else fy_start_year + 1
    q_start       = frappe.utils.getdate(f"{q_start_year}-{str(q_start_month).zfill(2)}-01")
    q_next_start  = frappe.utils.add_months(q_start, 3)
    return _bioman_qty_query(q_start, q_next_start, limit)


def _bioman_mtd(limit=500):
    today_date = frappe.utils.getdate(frappe.utils.today())
    month_start   = frappe.utils.getdate(f"{today_date.year}-{str(today_date.month).zfill(2)}-01")
    month_next    = frappe.utils.add_months(month_start, 1)
    return _bioman_qty_query(month_start, month_next, limit)


def _bioman_today(limit=500):
    today_date = frappe.utils.getdate(frappe.utils.today())
    return _bioman_qty_query(today_date, today_date, limit, exact=True)


# --- Status Buckets ---
def _bioman_in_progress(limit=500):
    return _bioman_status_query("wo.status='In Process'", limit)

def _bioman_pending(limit=500):
    return _bioman_status_query("wo.status='Not Started'", limit)

def _bioman_overdue(limit=500):
    return _bioman_status_query(
        "wo.status NOT IN ('Completed','Cancelled','Closed') AND wo.planned_end_date < CURDATE()", limit
    )

def _bioman_rework(limit=500):
    return _bioman_status_query("wo.custom_need_rework=1", limit)


def _bioman_status_query(extra_cond, limit=500, start_date=None, end_date=None):
    join_item = "LEFT JOIN `tabItem` it ON it.name = wo.production_item"
    where_cond = f"""
        {extra_cond}
        AND wo.status NOT IN ('Cancelled','Draft')
        AND wo.company REGEXP 'Bioman'
        AND it.item_group IN ('Bio Tank-FG','Bioman','Bio Tanks')
    """

    date_filter = ""
    params = [limit]
    if start_date and end_date:
        date_filter = "AND DATE(wo.creation) >= %s AND DATE(wo.creation) < %s"
        params = [start_date, end_date, limit]

    rows = frappe.db.sql(f"""
        SELECT wo.production_item AS item_code,
               it.item_name,
               it.stock_uom AS uom,
               it.item_group,
               SUM(wo.produced_qty) AS qty
        FROM `tabWork Order` wo {join_item}
        WHERE {where_cond}
        {date_filter}
        GROUP BY wo.production_item, it.item_name, it.stock_uom, it.item_group
        HAVING SUM(wo.produced_qty) > 0
        ORDER BY qty DESC
        LIMIT %s
    """, tuple(params), as_dict=True)

    return {
        "records": rows,
        "total": sum(r.qty for r in rows),
        "mode": "qty"
    }



# --- To Manufacture ---
def _bioman_to_manufacture(limit=500):
    rows = frappe.db.sql(
        """
        SELECT SOI.item_code, SOI.item_name, SOI.uom, I.item_group,
               CASE
                   WHEN (SUM(SOI.qty - SOI.delivered_qty)
                         - IFNULL(FG_Bin_FC.available_qty,0)
                         - IFNULL(FG_Bin_DP.available_qty,0)
                         - IFNULL(SFG_Bin.available_qty,0)) <= 0
                   THEN 0
                   ELSE (SUM(SOI.qty - SOI.delivered_qty)
                         - IFNULL(FG_Bin_FC.available_qty,0)
                         - IFNULL(FG_Bin_DP.available_qty,0)
                         - IFNULL(SFG_Bin.available_qty,0))
               END AS qty
        FROM `tabSales Order` SO
        LEFT JOIN `tabSales Order Item` SOI ON SO.name = SOI.parent
        LEFT JOIN (
            SELECT item_code, SUM(actual_qty) AS available_qty
            FROM `tabBin`
            WHERE warehouse = 'Finished Goods - BSSP'
            GROUP BY item_code
        ) FG_Bin_FC ON FG_Bin_FC.item_code = SOI.item_code
        LEFT JOIN (
            SELECT item_code, SUM(actual_qty) AS available_qty
            FROM `tabBin`
            WHERE warehouse != 'Finished Goods - BSSP'
            GROUP BY item_code
        ) FG_Bin_DP ON FG_Bin_DP.item_code = SOI.item_code
        LEFT JOIN (
            SELECT 
                CASE 
                    WHEN item_code = "10KL (T) - SFG2" THEN "10KL (3P) - FG"
                    WHEN item_code = "3KL (T) (H-4.3')- SFG2" THEN "3KL (3P) (H-4.3')-FG"
                    WHEN item_code = "3KL (T) (H-7')- SFG2" THEN "3KL (3P) (H-7')-FG"
                    WHEN item_code = "5KL (3P) - SFG2" THEN "5KL (3P) - FG"
                    WHEN item_code = "5KL (T) - SFG2" THEN "5KL(S) - FG"
                    ELSE NULL
                END AS fg_item_code,
                SUM(actual_qty) AS available_qty
            FROM `tabBin`
            GROUP BY item_code
        ) SFG_Bin ON SFG_Bin.fg_item_code = SOI.item_code
        LEFT JOIN `tabItem` I ON I.name = SOI.item_code
        WHERE SO.company = 'Bioman Sewage Solutions Private Limited'
          AND SO.billing_status != "Fully Billed"
          AND SO.status NOT IN ('Draft','Cancelled','Closed','Completed','On Hold')
          AND SO.order_type = "Sales"
          AND SO.selling_price_list = "Standard Selling"
          AND I.item_code NOT IN ('HG-1537','Crane Charges','TC - 01')
        GROUP BY SOI.item_code, SOI.item_name, SOI.uom, I.item_group
        HAVING qty > 0
        ORDER BY qty DESC
        LIMIT %s
        """,
        (limit,),
        as_dict=True
    )

    return {"records": rows, "total": sum(r.qty for r in rows), "mode": "qty"}

def _bioman_on_time(limit=500):
    """On-time Work Orders for current fiscal year"""

    today_date   = frappe.utils.getdate(frappe.utils.today())
    fy_start_year = today_date.year if today_date.month >= 4 else today_date.year - 1
    fy_start      = frappe.utils.getdate(f"{fy_start_year}-04-01")
    fy_next_start = frappe.utils.getdate(f"{fy_start_year+1}-04-01")

    return _bioman_status_query(
        "wo.status IN ('Completed','Closed') AND DATE(wo.actual_end_date) <= DATE(wo.creation)",
        limit, fy_start, fy_next_start
    )

 

def _bioman_delayed(limit=500):
    today_date   = frappe.utils.getdate(frappe.utils.today())
    fy_start_year = today_date.year if today_date.month >= 4 else today_date.year - 1
    fy_start      = frappe.utils.getdate(f"{fy_start_year}-04-01")
    fy_next_start = frappe.utils.getdate(f"{fy_start_year+1}-04-01")
    return _bioman_status_query(
        "wo.status IN ('Completed','Closed') AND (DATE(wo.actual_end_date) > DATE(wo.creation) OR wo.actual_end_date IS NULL)",
        limit, fy_start, fy_next_start
    )

# ================================
# DOORTISAN RECORD HELPERS
# ================================
today_date = frappe.utils.getdate(frappe.utils.today())

# -------- Fiscal Dates --------
fy_start_year = today_date.year if today_date.month >= 4 else today_date.year - 1
fy_start      = frappe.utils.getdate(f"{fy_start_year}-04-01")
fy_next_start = frappe.utils.getdate(f"{fy_start_year+1}-04-01")

fiscal_month  = (today_date.month - 4) % 12
q_index       = fiscal_month // 3
q_start_month = [4, 7, 10, 1][q_index]
q_start_year  = fy_start_year if q_index < 3 else fy_start_year + 1
q_start       = frappe.utils.getdate(f"{q_start_year}-{str(q_start_month).zfill(2)}-01")
q_next_start  = frappe.utils.add_months(q_start, 3)

month_start   = frappe.utils.getdate(f"{today_date.year}-{str(today_date.month).zfill(2)}-01")
month_next    = frappe.utils.add_months(month_start, 1)


def _doortisan_ytd(limit=500):
    rows = frappe.db.sql(f"""
        SELECT
            wo.production_item       AS item_code,
            wo.stock_uom              AS uom,
            wo.custom_item_group      AS item_group,
            SUM(wo.produced_qty)      AS qty
        FROM `tabWork Order` wo
        WHERE
            DATE(wo.creation) >= %s
            AND DATE(wo.creation) < %s
            AND wo.fg_warehouse IN ('Finished Goods - DPl')
            AND wo.status NOT IN ('Cancelled','Draft')
            AND wo.company REGEXP 'Doortisan'
        GROUP BY
            wo.production_item, wo.stock_uom, wo.custom_item_group
        HAVING
            qty > 0
        ORDER BY
            qty DESC
        LIMIT %s
    """, (fy_start, fy_next_start, int(limit)), as_dict=True)

    return {
        "records": rows,
        "total": sum((r["qty"] or 0) for r in rows)
    }

def _doortisan_qtd(limit=500):
    rows = frappe.db.sql(f"""
        SELECT
            wo.production_item      AS item_code,
            wo.stock_uom             AS uom,
            wo.custom_item_group     AS item_group,
            SUM(wo.produced_qty)     AS qty
        FROM `tabWork Order` wo
        WHERE
            DATE(wo.creation) >= %s
            AND DATE(wo.creation) < %s
            AND wo.fg_warehouse IN ('Finished Goods - DPl')
            AND wo.status NOT IN ('Cancelled','Draft')
            AND wo.company REGEXP 'Doortisan'
        GROUP BY
            wo.production_item, wo.stock_uom, wo.custom_item_group
        HAVING
            qty > 0
        ORDER BY
            qty DESC
        LIMIT %s
    """, (q_start, q_next_start, int(limit)), as_dict=True)

    return {
        "records": rows,
        "total": sum((r["qty"] or 0) for r in rows)
    }


def _doortisan_mtd(limit=500):
    rows = frappe.db.sql(f"""
        SELECT
            wo.production_item       AS item_code,
            wo.stock_uom             AS uom,
            wo.custom_item_group     AS item_group,
            SUM(wo.produced_qty)     AS qty
        FROM `tabWork Order` wo
        WHERE
            DATE(wo.creation) >= %s
            AND DATE(wo.creation) < %s
            AND wo.fg_warehouse IN ('Finished Goods - DPl')
            AND wo.status NOT IN ('Cancelled','Draft')
            AND wo.company REGEXP 'Doortisan'
        GROUP BY
            wo.production_item, wo.stock_uom, wo.custom_item_group
        HAVING
            qty > 0
        ORDER BY
            qty DESC
        LIMIT %s
    """, (month_start, month_next, int(limit)), as_dict=True)

    return {
        "records": rows,
        "total": sum((r["qty"] or 0) for r in rows)
    }

def _doortisan_today(limit=500):
    today_date = frappe.utils.getdate(frappe.utils.today())

    rows = frappe.db.sql(f"""
        SELECT
            wo.production_item       AS item_code,
            wo.stock_uom             AS uom,
            wo.custom_item_group     AS item_group,
            SUM(wo.produced_qty)     AS qty
        FROM `tabWork Order` wo
        WHERE
            DATE(wo.creation) = %s
            AND wo.fg_warehouse IN ('Finished Goods - DPl')
            AND wo.status NOT IN ('Cancelled','Draft')
            AND wo.company REGEXP 'Doortisan'
        GROUP BY
            wo.production_item, wo.stock_uom, wo.custom_item_group
        HAVING
            qty > 0
        ORDER BY
            qty DESC
        LIMIT %s
    """, (today_date, int(limit)), as_dict=True)

    return {
        "records": rows,
        "total": sum((r["qty"] or 0) for r in rows)
    }

@frappe.whitelist()
def _doortisan_on_time(limit=500, date_field="wo.creation"):
    # allow only safe date fields
    allowed = {"wo.creation", "wo.actual_end_date", "wo.expected_delivery_date", "wo.planned_end_date"}
    df = date_field if date_field in allowed else "wo.creation"

    base_where = """
        AND wo.status NOT IN ('Cancelled','Draft')
        AND wo.company REGEXP 'Doortisan'
        AND wo.fg_warehouse IN ('Finished Goods - DPl')
    """

    rows = frappe.db.sql(f"""
        SELECT
            wo.production_item       AS item_code,
            wo.stock_uom             AS uom,
            wo.custom_item_group     AS item_group,
            SUM(wo.produced_qty)     AS qty
        FROM `tabWork Order` wo
        WHERE
            wo.actual_end_date IS NOT NULL
            AND DATE(wo.actual_end_date) <= DATE(wo.expected_delivery_date)
            AND DATE({df}) >= %s
            AND DATE({df}) < %s
            {base_where}
        GROUP BY
            wo.production_item, wo.stock_uom, wo.custom_item_group
        HAVING SUM(wo.produced_qty) > 0
        ORDER BY qty DESC
        LIMIT %s
    """, (fy_start, fy_next_start, int(limit)), as_dict=True)

    # Cast qty to float to avoid JSON serialization errors
    rows = [{**r, "qty": float(r["qty"])} for r in rows]

    return {
        "records": rows,
        "total": sum(r["qty"] for r in rows)
    }

@frappe.whitelist()
def _doortisan_delayed(limit=500, date_field="wo.creation"):
    # allow only safe date fields
    allowed = {"wo.creation", "wo.actual_end_date", "wo.expected_delivery_date", "wo.planned_end_date"}
    df = date_field if date_field in allowed else "wo.creation"

    base_where = """
        AND wo.status NOT IN ('Cancelled','Draft')
        AND wo.company REGEXP 'Doortisan'
        AND wo.fg_warehouse IN ('Finished Goods - DPl')
    """

    rows = frappe.db.sql(f"""
        SELECT
            wo.production_item       AS item_code,
            wo.stock_uom             AS uom,
            wo.custom_item_group     AS item_group,
            SUM(wo.produced_qty)     AS qty
        FROM `tabWork Order` wo
        WHERE
            ((DATE(wo.actual_end_date) > DATE(wo.expected_delivery_date))
             OR (wo.actual_end_date IS NULL)
             OR (wo.expected_delivery_date IS NULL))
            AND DATE({df}) >= %s
            AND DATE({df}) < %s
            {base_where}
        GROUP BY
            wo.production_item, wo.stock_uom, wo.custom_item_group
        HAVING SUM(wo.produced_qty) > 0
        ORDER BY qty DESC
        LIMIT %s
    """, (fy_start, fy_next_start, int(limit)), as_dict=True)

    # Cast qty to float for JSON safety
    rows = [{**r, "qty": float(r["qty"])} for r in rows]

    return {
        "records": rows,
        "total": sum(r["qty"] for r in rows)
    }

@frappe.whitelist()
def _doortisan_in_progress(limit=500):
    rows = frappe.db.sql(f"""
        SELECT
            wo.production_item       AS item_code,
            wo.stock_uom             AS uom,
            wo.custom_item_group     AS item_group,
            (COALESCE(SUM(wo.qty), 0) - COALESCE(SUM(wo.produced_qty), 0)) AS qty
        FROM `tabWork Order` wo
        WHERE
            wo.status = 'In Process'
            AND wo.fg_warehouse IN ('Finished Goods - DPl')
            AND wo.company REGEXP 'Doortisan'
        GROUP BY
            wo.production_item, wo.stock_uom, wo.custom_item_group
        HAVING qty > 0
        ORDER BY qty DESC
        LIMIT %s
    """, (int(limit),), as_dict=True)

    # Cast qty to float for JSON safety
    rows = [{**r, "qty": float(r["qty"])} for r in rows]

    return {
        "records": rows,
        "total": sum(r["qty"] for r in rows)
    }

@frappe.whitelist()
def _doortisan_pending(limit=500):
    rows = frappe.db.sql(f"""
        SELECT
            wo.production_item       AS item_code,
            wo.stock_uom             AS uom,
            wo.custom_item_group     AS item_group,
            COALESCE(SUM(wo.qty), 0) AS qty
        FROM `tabWork Order` wo
        WHERE
            wo.status = 'Not Started'
            AND wo.fg_warehouse IN ('Finished Goods - DPl')
            AND wo.company REGEXP 'Doortisan'
        GROUP BY
            wo.production_item, wo.stock_uom, wo.custom_item_group
        HAVING qty > 0
        ORDER BY qty DESC
        LIMIT %s
    """, (int(limit),), as_dict=True)

    # Cast qty to float for JSON safety
    rows = [{**r, "qty": float(r["qty"])} for r in rows]

    return {
        "records": rows,
        "total": sum(r["qty"] for r in rows)
    }

@frappe.whitelist()
def _doortisan_overdue(limit=500):
    rows = frappe.db.sql(f"""
        SELECT
            wo.production_item                                AS item_code,
            wo.stock_uom                                      AS uom,
            wo.custom_item_group                              AS item_group,
            (COALESCE(SUM(wo.qty), 0) - COALESCE(SUM(wo.produced_qty), 0)) AS qty
        FROM `tabWork Order` wo
        WHERE
            wo.status IN ('Not Started', 'In Process')
            AND wo.expected_delivery_date < CURDATE()
            AND wo.fg_warehouse IN ('Finished Goods - DPl')
            AND wo.company REGEXP 'Doortisan'
        GROUP BY
            wo.production_item, wo.stock_uom, wo.custom_item_group
        HAVING qty > 0
        ORDER BY qty DESC
        LIMIT %s
    """, (int(limit),), as_dict=True)

    # Cast qty to float for JSON safety
    rows = [{**r, "qty": float(r["qty"])} for r in rows]

    return {
        "records": rows,
        "total": sum(r["qty"] for r in rows)
    }

@frappe.whitelist()
def _doortisan_rework(limit=500, date_field="wo.creation"):
    # allow only safe date fields
    allowed = {"wo.creation", "wo.actual_end_date", "wo.expected_delivery_date", "wo.planned_end_date"}
    df = date_field if date_field in allowed else "wo.creation"

    base_where = """
        AND wo.status NOT IN ('Cancelled','Draft')
        AND wo.company REGEXP 'Doortisan'
        AND wo.fg_warehouse IN ('Finished Goods - DPl')
    """

    rows = frappe.db.sql(f"""
        SELECT
            wo.production_item       AS item_code,
            wo.stock_uom             AS uom,
            wo.custom_item_group     AS item_group,
            COALESCE(SUM(wo.produced_qty), 0) AS qty
        FROM `tabWork Order` wo
        WHERE
            wo.custom_need_rework = 1
            AND DATE({df}) >= %s
            AND DATE({df}) < %s
            {base_where}
        GROUP BY
            wo.production_item, wo.stock_uom, wo.custom_item_group
        HAVING qty > 0
        ORDER BY qty DESC
        LIMIT %s
    """, (fy_start, fy_next_start, int(limit)), as_dict=True)

    # Cast qty to float for JSON safety
    rows = [{**r, "qty": float(r["qty"])} for r in rows]

    return {
        "records": rows,
        "total": sum(r["qty"] for r in rows)
    }

@frappe.whitelist()
def _doortisan_to_manufacture(limit=500):
    rows = frappe.db.sql(f"""
        SELECT
            I.item_code              AS item_code,
            I.item_name              AS item_name,
            I.stock_uom              AS uom,
            I.item_group             AS item_group,
            SUM(SOI.qty - SOI.delivered_qty) AS prod_needed,
            COALESCE(B.actual_qty, 0)        AS actual_stock,
            CASE
                WHEN SUM(SOI.qty - SOI.delivered_qty) <= COALESCE(B.actual_qty, 0)
                    THEN 0
                ELSE SUM(SOI.qty - SOI.delivered_qty) - COALESCE(B.actual_qty, 0)
            END AS qty
        FROM `tabSales Order` SO
        INNER JOIN `tabSales Order Item` SOI ON SO.name = SOI.parent
        INNER JOIN `tabItem` I ON SOI.item_code = I.item_code
        LEFT JOIN (
            SELECT
                item_code,
                SUM(actual_qty) AS actual_qty
            FROM `tabBin`
            WHERE actual_qty > 0
            GROUP BY item_code
        ) B ON SOI.item_code = B.item_code
        WHERE
            SO.company IN ('Doortisan Creations Private Limited',
                           'Homegenie Building Products Private Limited')
            AND I.is_stock_item = 1
            AND I.item_group IN (
                'Teak Shutter','Teak Frame','Teak Border','Teak Window',
                'Flush Door','WPC Shutter','WPC Frame','M Wood Shutter',
                'M Wood Frame','FRP Shutter','FRP Frame','Restricted Item'
            )
            AND SO.billing_status != 'Fully Billed'
            AND SO.status NOT IN ('Draft','Cancelled','Closed','Completed')
            AND SO.order_type = 'Sales'
        GROUP BY SOI.item_code, I.item_name, I.stock_uom, I.item_group, B.actual_qty
        HAVING qty > 0
        ORDER BY I.item_name
        LIMIT %s
    """, (int(limit),), as_dict=True)

    # Cast qty to float for JSON safety
    rows = [{**r, "qty": float(r["qty"])} for r in rows]

    return {
        "records": rows,
        "total": sum(r["qty"] for r in rows)
    }

### TIMBE HELPER ######

today_date = frappe.utils.getdate(frappe.utils.today())

# -------- Fiscal Dates --------
fy_start_year = today_date.year if today_date.month >= 4 else today_date.year - 1
fy_start      = frappe.utils.getdate(f"{fy_start_year}-04-01")
fy_next_start = frappe.utils.getdate(f"{fy_start_year+1}-04-01")

fiscal_month  = (today_date.month - 4) % 12
q_index       = fiscal_month // 3
q_start_month = [4, 7, 10, 1][q_index]
q_start_year  = fy_start_year if q_index < 3 else fy_start_year + 1
q_start       = frappe.utils.getdate(f"{q_start_year}-{str(q_start_month).zfill(2)}-01")
q_next_start  = frappe.utils.add_months(q_start, 3)

month_start   = frappe.utils.getdate(f"{today_date.year}-{str(today_date.month).zfill(2)}-01")
month_next    = frappe.utils.add_months(month_start, 1)


def _timbe_ytd(limit=500):
    rows = frappe.db.sql(f"""
        SELECT
            wo.production_item       AS item_code,
            wo.stock_uom             AS uom,
            wo.custom_item_group     AS item_group,
            SUM(wo.produced_qty)     AS qty
        FROM `tabWork Order` wo
        WHERE
            DATE(wo.creation) >= %s
            AND DATE(wo.creation) < %s
            AND wo.fg_warehouse IN ('Finished Goods - TUWPL')
            AND wo.status NOT IN ('Cancelled','Draft')
            AND wo.company REGEXP 'Timbe Windows'
        GROUP BY
            wo.production_item, wo.stock_uom, wo.custom_item_group
        HAVING qty > 0
        ORDER BY qty DESC
        LIMIT %s
    """, (fy_start, fy_next_start, int(limit)), as_dict=True)

    return {"records": rows, "total": sum((r["qty"] or 0) for r in rows)}


def _timbe_qtd(limit=500):
    rows = frappe.db.sql(f"""
        SELECT
            wo.production_item       AS item_code,
            wo.stock_uom             AS uom,
            wo.custom_item_group     AS item_group,
            SUM(wo.produced_qty)     AS qty
        FROM `tabWork Order` wo
        WHERE
            DATE(wo.creation) >= %s
            AND DATE(wo.creation) < %s
            AND wo.fg_warehouse IN ('Finished Goods - TUWPL')
            AND wo.status NOT IN ('Cancelled','Draft')
            AND wo.company REGEXP 'Timbe Windows'
        GROUP BY
            wo.production_item, wo.stock_uom, wo.custom_item_group
        HAVING qty > 0
        ORDER BY qty DESC
        LIMIT %s
    """, (q_start, q_next_start, int(limit)), as_dict=True)

    return {"records": rows, "total": sum((r["qty"] or 0) for r in rows)}


def _timbe_mtd(limit=500):
    rows = frappe.db.sql(f"""
        SELECT
            wo.production_item       AS item_code,
            wo.stock_uom             AS uom,
            wo.custom_item_group     AS item_group,
            SUM(wo.produced_qty)     AS qty
        FROM `tabWork Order` wo
        WHERE
            DATE(wo.creation) >= %s
            AND DATE(wo.creation) < %s
            AND wo.fg_warehouse IN ('Finished Goods - TUWPL')
            AND wo.status NOT IN ('Cancelled','Draft')
            AND wo.company REGEXP 'Timbe Windows'
        GROUP BY
            wo.production_item, wo.stock_uom, wo.custom_item_group
        HAVING qty > 0
        ORDER BY qty DESC
        LIMIT %s
    """, (month_start, month_next, int(limit)), as_dict=True)

    return {"records": rows, "total": sum((r["qty"] or 0) for r in rows)}


def _timbe_today(limit=500):
    today_date = frappe.utils.getdate(frappe.utils.today())
    rows = frappe.db.sql(f"""
        SELECT
            wo.production_item       AS item_code,
            wo.stock_uom             AS uom,
            wo.custom_item_group     AS item_group,
            SUM(wo.produced_qty)     AS qty
        FROM `tabWork Order` wo
        WHERE
            DATE(wo.creation) = %s
            AND wo.fg_warehouse IN ('Finished Goods - TUWPL')
            AND wo.status NOT IN ('Cancelled','Draft')
            AND wo.company REGEXP 'Timbe Windows'
        GROUP BY
            wo.production_item, wo.stock_uom, wo.custom_item_group
        HAVING qty > 0
        ORDER BY qty DESC
        LIMIT %s
    """, (today_date, int(limit)), as_dict=True)

    return {"records": rows, "total": sum((r["qty"] or 0) for r in rows)}

@frappe.whitelist()
def _timbe_on_time(limit=500):
    rows = frappe.db.sql("""
        SELECT
            wo.production_item   AS item_code,
            wo.stock_uom         AS uom,
            wo.custom_item_group AS item_group,
            SUM(wo.produced_qty) AS qty
        FROM `tabWork Order` wo
        WHERE
            wo.status='Completed'
            AND wo.actual_end_date IS NOT NULL
            AND DATE(wo.actual_end_date) <= DATE(wo.planned_end_date)
            AND wo.docstatus=1
            AND wo.company='Timbe Windows Private Limited'
        GROUP BY wo.production_item, wo.stock_uom, wo.custom_item_group
        HAVING qty > 0
        ORDER BY qty DESC
        LIMIT %s
    """, (int(limit),), as_dict=True)

    rows = [{**r, "qty": float(r["qty"])} for r in rows]
    return {"records": rows, "total": sum(r["qty"] for r in rows)}





@frappe.whitelist()
def _timbe_delayed(limit=500):
    rows = frappe.db.sql("""
        SELECT
            wo.production_item   AS item_code,
            wo.stock_uom         AS uom,
            wo.custom_item_group AS item_group,
            SUM(wo.produced_qty) AS qty
        FROM `tabWork Order` wo
        WHERE
            wo.status='Completed'
            AND DATE(wo.actual_end_date) > DATE(wo.planned_end_date)
            AND wo.docstatus=1
            AND wo.company='Timbe Windows Private Limited'
        GROUP BY wo.production_item, wo.stock_uom, wo.custom_item_group
        HAVING qty > 0
        ORDER BY qty DESC
        LIMIT %s
    """, (int(limit),), as_dict=True)

    rows = [{**r, "qty": float(r["qty"])} for r in rows]
    return {"records": rows, "total": sum(r["qty"] for r in rows)}

@frappe.whitelist()
def _timbe_in_progress(limit=500):
    rows = frappe.db.sql("""
        SELECT
            wo.production_item   AS item_code,
            wo.stock_uom         AS uom,
            wo.custom_item_group AS item_group,
            SUM(wo.produced_qty) AS qty
        FROM `tabWork Order` wo
        WHERE
            wo.status='In Process'
            AND wo.docstatus=1
            AND wo.company='Timbe Windows Private Limited'
        GROUP BY wo.production_item, wo.stock_uom, wo.custom_item_group
        HAVING qty > 0
        ORDER BY qty DESC
        LIMIT %s
    """, (int(limit),), as_dict=True)

    rows = [{**r, "qty": float(r["qty"])} for r in rows]
    return {"records": rows, "total": sum(r["qty"] for r in rows)}

def _timbe_pending(limit=500):
    rows = frappe.db.sql("""
        SELECT
            wo.production_item   AS item_code,
            wo.stock_uom         AS uom,
            wo.custom_item_group AS item_group,
            SUM(wo.produced_qty) AS qty
        FROM `tabWork Order` wo
        WHERE
            wo.status='Not Started'
            AND wo.docstatus=1
            AND wo.company='Timbe Windows Private Limited'
        GROUP BY wo.production_item, wo.stock_uom, wo.custom_item_group
        HAVING qty > 0
        ORDER BY qty DESC
        LIMIT %s
    """, (int(limit),), as_dict=True)

    rows = [{**r, "qty": float(r["qty"])} for r in rows]
    return {"records": rows, "total": sum(r["qty"] for r in rows)}


@frappe.whitelist()
def _timbe_overdue(limit=500):
    rows = frappe.db.sql("""
        SELECT
            wo.production_item   AS item_code,
            wo.stock_uom         AS uom,
            wo.custom_item_group AS item_group,
            SUM(wo.produced_qty) AS qty
        FROM `tabWork Order` wo
        WHERE
            wo.status IN ('Not Started','In Process')
            AND wo.expected_delivery_date < CURDATE()
            AND wo.docstatus=1
            AND wo.company='Timbe Windows Private Limited'
        GROUP BY wo.production_item, wo.stock_uom, wo.custom_item_group
        HAVING qty > 0
        ORDER BY qty DESC
        LIMIT %s
    """, (int(limit),), as_dict=True)

    rows = [{**r, "qty": float(r["qty"])} for r in rows]
    return {"records": rows, "total": sum(r["qty"] for r in rows)}

@frappe.whitelist()
def _timbe_rework(limit=500):
    rows = frappe.db.sql("""
        SELECT
            wo.production_item   AS item_code,
            wo.stock_uom         AS uom,
            wo.custom_item_group AS item_group,
            SUM(wo.produced_qty) AS qty
        FROM `tabWork Order` wo
        WHERE
            IFNULL(wo.custom_need_rework,0)=1
            AND wo.docstatus=1
            AND wo.company='Timbe Windows Private Limited'
        GROUP BY wo.production_item, wo.stock_uom, wo.custom_item_group
        HAVING qty > 0
        ORDER BY qty DESC
        LIMIT %s
    """, (int(limit),), as_dict=True)

    rows = [{**r, "qty": float(r["qty"])} for r in rows]
    return {"records": rows, "total": sum(r["qty"] for r in rows)}

# @frappe.whitelist()
# def _timbe_to_manufacture(limit=500):
#     rows = frappe.db.sql("""
#         SELECT
#             demand.item_code       AS item_code,
#             I.stock_uom            AS uom,
#             I.item_group           AS item_group,
#             # demand.ordered_qty     AS ordered_qty,
#             # COALESCE(B.actual_qty,0) AS actual_stock,
#             CASE
#                 WHEN demand.ordered_qty <= COALESCE(B.actual_qty,0)
#                     THEN 0
#                 ELSE demand.ordered_qty - COALESCE(B.actual_qty,0)
#             END AS to_manufacture
#         FROM (
#             SELECT
#                 SOI.item_code,
#                 SUM(SOI.qty - SOI.delivered_qty) AS ordered_qty
#             FROM `tabSales Order` SO
#             INNER JOIN `tabSales Order Item` SOI ON SO.name = SOI.parent
#             WHERE SO.company REGEXP "Timbe Windows"
#               AND SO.billing_status != %s
#               AND SO.status NOT IN ('Draft','Cancelled','Closed','Completed')
#               AND SO.order_type = %s
#               AND SOI.item_code != %s
#             GROUP BY SOI.item_code
#         ) demand
#         LEFT JOIN (
#             SELECT item_code, SUM(actual_qty) AS actual_qty
#             FROM `tabBin`
#             WHERE warehouse = 'Finished Goods - TUWPL'
#             GROUP BY item_code
#         ) B ON demand.item_code = B.item_code
#         LEFT JOIN `tabItem` I ON demand.item_code = I.item_code
#         WHERE I.is_stock_item = 1
#           AND I.item_name NOT LIKE %s
#           AND (demand.ordered_qty - COALESCE(B.actual_qty,0)) > 0
#         ORDER BY I.item_name
#         LIMIT %s
#     """, ('Fully Billed', 'Sales', 'FT-2x4', '%Installation%', int(limit)), as_dict=True)

#     rows = [
#         {
#             **r,
#             "ordered_qty": float(r["ordered_qty"]),
#             "actual_stock": float(r["actual_stock"]),
#             "to_manufacture": float(r["to_manufacture"])
#         }
#         for r in rows
#     ]

#     return {
#         "records": rows,
#         "total": sum(r["to_manufacture"] for r in rows)
#     }



@frappe.whitelist()
def _timbe_to_manufacture(limit=500):
    rows = frappe.db.sql("""
        SELECT *
        FROM (
            SELECT
                SOI.item_code              AS item_code,
                I.stock_uom                AS uom,
                I.item_group               AS item_group,
                SUM(SOI.qty - SOI.delivered_qty) - COALESCE(B.actual_qty,0) AS qty
            FROM `tabSales Order` SO
            LEFT JOIN `tabSales Order Item` SOI ON SO.name = SOI.parent
            LEFT JOIN (
                SELECT item_code, SUM(actual_qty) AS actual_qty
                FROM `tabBin`
                WHERE warehouse = 'Finished Goods - TUWPL'
                GROUP BY item_code
            ) B ON SOI.item_code = B.item_code
            LEFT JOIN `tabItem` I ON SOI.item_code = I.item_code
            WHERE SO.company REGEXP "Timbe Windows"
              AND I.is_stock_item = 1
              AND SOI.item_name NOT LIKE %s
              AND SO.billing_status != %s
              AND SO.status NOT IN ('Draft', 'Cancelled', 'Closed', 'Completed')
              AND SO.order_type = %s
              AND SOI.item_code != %s
            GROUP BY SOI.item_code, I.item_name, I.stock_uom, I.item_group, B.actual_qty
        ) AS subquery
        WHERE qty > 0
        GROUP BY item_code
        LIMIT %s
    """, ('%Installation%', 'Fully Billed', 'Sales', 'FT-2x4', int(limit)), as_dict=True)

    rows = [
        {
            **r,
            "qty": float(r["qty"])
        }
        for r in rows
    ]

    return {
        "records": rows,
        "total": sum(r["qty"] for r in rows)
    }

