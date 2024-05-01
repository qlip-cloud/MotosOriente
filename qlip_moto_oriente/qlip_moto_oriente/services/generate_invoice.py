import json
import frappe
from frappe.utils import flt
from datetime import datetime
from frappe.utils import add_to_date, getdate, now, get_time, nowdate
from six import string_types, iteritems
from erpnext.accounts.party import get_party_account

@frappe.whitelist()
def generate_sales_invoice(values):
  
  r ={
    'success_sa_in':False,
    'sa_in_name':'',
    'success_jo_en':False,
    'jo_en_name':''
  }

  items = []

  journal_account = []

  if isinstance(values, string_types):
    values = json.loads(values)
  
  customer = frappe.get_doc('Customer', values.get('cliente'))
  company = frappe.defaults.get_user_default('Company')
  price_list, price_list_currency = frappe.db.get_values("Price List", {"selling": 1}, ['name', 'currency'])[0]

  sales_team_is_equal = False
  last_sales_teams_name = []
  cl_referido_is_equal = False
  last_cl_referido = ''

  for sales_invoice in values.get('table_sales_invoice'):
    sal_in = frappe.get_doc('Sales Invoice', sales_invoice.get('name'))

    for team in sal_in.sales_team:
      if len(last_sales_teams_name) ==s 0:
        last_sales_teams_name.append(team)
        sales_team_is_equal = True
      if len(last_sales_teams_name) > 0:
        if last_sales_teams_name[0].sales_person != team.sales_person or last_sales_teams_name[0].allocated_percentage != team.allocated_percentage:
          sales_team_is_equal = False

    if not last_cl_referido:
      if sal_in.cl_referido:
        cl_referido_is_equal = True
        last_cl_referido = sal_in.cl_referido
    else:
      if last_cl_referido != sal_in.cl_referido:
        cl_referido_is_equal = False

    item = {
      'item_code':'',
      'item_name':sal_in.tipo_de_venta,
      'rate':sal_in.grand_total
    }

    if sal_in.tipo_de_venta == 'Motocicleta':
      item['item_code'] = 'MOTOCICLETA'

    if sal_in.tipo_de_venta == 'Mostrador':
      item['item_code'] = 'MOSTRADOR'

    if sal_in.tipo_de_venta == 'Servicio Mantenimiento':
      item['item_code'] = 'SERVICIO MANTENIMIENTO'

    items.append(item)
    
    journal_account.append({
            'account': sal_in.debit_to,
            'credit_in_account_currency': sal_in.grand_total,
            'party_type': 'Customer',
            'party': customer.name,
            'reference_type': 'Sales Invoice',
	          'reference_name': sal_in.name
          })
  
  si = {
    'doctype': 'Sales Invoice',
    'company': company,
    'customer': customer.name,
    'numero_de_placa':values.get('numero_de_placa'),
    'tipo_de_venta':'Motocicleta',
    'title': customer.customer_name,
    'naming_series': values.get('prefijo'),
    'customer_name':customer.customer_name,
    'tax_id':customer.tax_id,
    'posting_date': getdate(datetime.now()),
    'posting_time': get_time(datetime.now()),
    'items':items,
    "status":"Draft",
    "compilado": 1,
    "taxes":[],
    'selling_price_list': price_list,
    'price_list_currency': price_list_currency,
    'plc_conversion_rate': 1.0,
    'payment_terms_template':values.get('payment_terms_template'),
    'sales_team': last_sales_teams_name if sales_team_is_equal else [],
    'cl_referido': last_cl_referido if cl_referido_is_equal else ''
  }
  
  try:

    si = frappe.get_doc(si)
    si.set_missing_values(True)
    si.calculate_taxes_and_totals()
    si.cl_valor_consolidado = si.grand_total
    si.insert()
    frappe.flags.in_import = False

    r['success_sa_in'] = True
    r['sa_in_name'] = si.name

  except frappe.exceptions.DuplicateEntryError as ex:
    print(ex)
    frappe.log_error(message=frappe.get_traceback(), title="qlip_moto_oriente")
    frappe.db.rollback()
  except frappe.exceptions.UniqueValidationError as ex:
    print(ex)
    frappe.log_error(message=frappe.get_traceback(), title="qlip_moto_oriente")
    frappe.db.rollback()
  except Exception as ex:
    print(ex)
    frappe.log_error(message=frappe.get_traceback(), title="qlip_moto_oriente")
    frappe.db.rollback()
  
  #ASIENTO

  
  if r['success_sa_in'] :

    try:

      je = frappe.new_doc('Journal Entry')
      je.posting_date = nowdate()
      je.voucher_type = 'Journal Entry'
      je.status = 'Submitted'
      je.docstatus = 1

      total = 0

      for ja in journal_account:
          total += ja.get('credit_in_account_currency')
          #ja['reference_name'] = r['sa_in_name']
          je.append('accounts', ja)

      je.append('accounts', {
        'account': values.get('cuenta'),
        'debit_in_account_currency': total,
        'party_type': 'Customer',
        'party': customer.name
        #'reference_type': 'Sales Invoice',
        #'reference_name': r['sa_in_name']
      })

      je.flags.ignore_mandatory = True
      je.save()


      r['success_jo_en'] = True
      r['jo_en_name'] = je.name

    except Exception as ex:
      print(ex)
      r['success_jo_en'] = False
      r['success_sa_in'] = False
      frappe.log_error(message=frappe.get_traceback(), title="qlip_moto_oriente")
      frappe.db.rollback()

  return r
	
