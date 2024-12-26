import json
import frappe
from frappe.utils import flt
from datetime import datetime
from frappe.utils import add_to_date, getdate, now, get_time, nowdate
from six import string_types, iteritems
from erpnext.accounts.party import get_party_account

@frappe.whitelist(allow_guest=True)
def exec():
    query = """SELECT psh.name,
                      psh.parent, 
                      psh.payment_term, 
                      psh.due_date, 
                      psh.invoice_portion, 
                      psh.payment_amount, 
                      psh.outstanding, 
                      psh.paid_amount, 
                      fi.gle_entry_total_without_outstanding
                FROM `tabPayment Schedule` as psh, 
                    (
                        SELECT si.name,
                        IF(si.disable_rounded_total = 0, si.rounded_total, si.grand_total) AS sales_invoice_total,
                        si.total_advance,
                        (	
                            SELECT SUM(gle.credit) 
                            FROM `tabGL Entry` AS gle 
                            WHERE gle.against_voucher = si.name 
                            AND gle.is_cancelled = 0 
                            AND gle.voucher_type in ('Payment Entry', 'Journal Entry')
                        ) AS gle_entry_total,
                       (	
                            SELECT SUM(gle.credit) 
                            FROM `tabGL Entry` AS gle 
                            WHERE gle.against_voucher = si.name 
                            AND gle.is_cancelled = 0 
                            AND gle.voucher_type in ('Payment Entry', 'Journal Entry') 
                            AND gle.voucher_no not in (	SELECT reference_name 
                                                        FROM `tabSales Invoice Advance` AS sia 
                                                        WHERE sia.parent = gle.against_voucher)
                        ) AS gle_entry_total_without_outstanding,
                        (IF(si.disable_rounded_total = 0, si.rounded_total, si.grand_total) - si.total_advance) AS si_total_after_outstanding,
                        si.outstanding_amount,
                        (IF(si.disable_rounded_total = 0, si.rounded_total, si.grand_total) - si.total_advance - si.outstanding_amount - IF(si.write_off_amount <> 0, si.write_off_amount, 0)) AS payed_calculated,
                        (
                            (
                                SELECT SUM(gle.credit) 
                                FROM `tabGL Entry` AS gle WHERE gle.against_voucher = si.name 
                                AND gle.is_cancelled = 0 
                                AND gle.voucher_type in ('Payment Entry', 'Journal Entry') 
                                AND gle.voucher_no not in (SELECT reference_name FROM `tabSales Invoice Advance` AS sia WHERE sia.parent = gle.against_voucher)) - (IF(si.disable_rounded_total = 0, si.rounded_total, si.grand_total) - si.total_advance - si.outstanding_amount - IF(si.write_off_amount <> 0, si.write_off_amount, 0))) AS payed_dif
                        FROM `tabSales Invoice` AS si
                        WHERE si.name LIKE 'FVT%' 
                        AND si.outstanding_amount > 0
                        HAVING sales_invoice_total > si.total_advance
                        AND payed_dif = 0
                    ) as fi
                    WHERE psh.parent = fi.name
                    ORDER BY psh.parent, psh.due_date
                    
                """
    rows = frappe.db.sql(query, as_dict = 1)

    parent = None
    amount = 0

    for row in rows:

        if row.parent != parent:
            parent = row.parent
            amount = row.gle_entry_total_without_outstanding
        
        if row.payment_amount <= amount and row.paid_amount == 0:
            row.paid_amount = row.payment_amount
            amount -= row.payment_amount
            row.outstanding = 0
            
        if row.payment_amount > amount and row.paid_amount == 0:
            row.paid_amount = amount
            row.outstanding = row.payment_amount - amount
            amount -= amount
        
        row.gle_entry_total_without_outstanding = amount

        frappe.db.set_value('Payment Schedule', row.name, {
            'outstanding': row.outstanding,
            'paid_amount': row.paid_amount
        })

    frappe.db.commit()

    return rows