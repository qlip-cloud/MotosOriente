frappe.listview_settings['Sales Invoice'] = frappe.listview_settings['Sales Invoice'] || {};

frappe.listview_settings['Sales Invoice'] = {
    
    refresh: function(listview) {
        // triggers once before the list is loaded
        //console.log("loaded", listview);
        listview.page.add_inner_button('Documento de Financiación', () => open_detail_popup());       
    }
}

function open_detail_popup(){

    function search(dialog){

        let dfilters = {
            "compilado": 0,
            "status": ['not in', ["Draft", "Canceled"]]
        };

        if(dialog.layout.fields_dict.numero_de_placa.value)
            dfilters['numero_de_placa'] = dialog.layout.fields_dict.numero_de_placa.value
        
        if(dialog.layout.fields_dict.cliente.value)
            dfilters['customer'] = dialog.layout.fields_dict.cliente.value

        if(Object.keys(dfilters).length > 0){
            frappe.db.get_list('Sales Invoice', { filters:dfilters, fields:['name', 'title', 'status', 'base_grand_total', 'customer', 'numero_de_placa', 'tipo_de_venta']}).then((result)=>{
                
                result.forEach(element => {
                    element.status = frappe._(element.status)
                    return element
                });

                dialog.layout.fields_dict.table_sales_invoice.grid.df.data = result;
                dialog.layout.fields_dict.table_sales_invoice.grid.refresh();

                if(Object.keys(result).length > 0){
                    dialog.layout.fields_dict.table_sales_invoice.df.hidden = 0;
                    dialog.layout.fields_dict.table_sales_invoice.refresh();
                }else{
                    dialog.layout.fields_dict.table_sales_invoice.df.hidden = 1;
                    dialog.layout.fields_dict.table_sales_invoice.refresh();
                }

            });
        }
        
    }

    let naming_series_options = frappe.get_meta("Sales Invoice").fields.find(field => field.fieldname == "naming_series")
    naming_series_options = naming_series_options.options.split("\n").filter((e) => e != null)
    
    let d = new frappe.ui.Dialog({
        title: 'Detalle',
        fields: [
            {
                label: 'Placa',
                fieldname: 'numero_de_placa',
                fieldtype: 'Data',
                reqd:true,
                onchange:function(){
                    search(this);
                }
            },
            {
                label: 'Cliente',
                fieldname: 'cliente',
                fieldtype: 'Link',
                options:"Customer",
                reqd:true,
                onchange:function(){
                    search(this);
                }
            },
            {
                label: 'Cuenta contrapartida',
                fieldname: 'cuenta',
                fieldtype: 'Link',
                options:"Account",
                reqd:true
            },
            {
                label: 'Prefijo de factura',
                fieldname: 'prefijo',
                fieldtype: 'Select',
                options:naming_series_options,
                reqd:true,
            },
            {
                label: 'Términos de pago',
                fieldname: 'payment_terms_template',
                fieldtype: 'Link',
                options:'Payment Terms Template',
                reqd:true,
            },
            {
                label: 'Facturas Generadas',
                fieldname: 'table_sales_invoice',
                fieldtype: 'Table',
                cannot_add_rows: true,
                cannot_delete_rows: true,
                in_place_edit: true,
                hidden:1,
                reqd:true,
                fields: [
                    { fieldname: 'title', fieldtype: 'Link', in_list_view: 1, label: 'Cliente', options:'Customer'},
                    { fieldname: 'status', fieldtype: 'Data', in_list_view: 1, label: 'Estado' },
                    { fieldname: 'base_grand_total', fieldtype: 'Float', in_list_view: 1, label: 'Total'},
                    { fieldname: 'name', fieldtype: 'Link', in_list_view: 1, label: 'Nombre', options:'Sales Invoice'},
                    { fieldname: 'numero_de_placa', fieldtype: 'Data', in_list_view: 1, label: 'Número de Placa'},
                    { fieldname: 'tipo_de_venta', fieldtype: 'Data', in_list_view: 1, label: 'Tipo de Venta'}
                ]
            }
        ],
        size: 'small', // small, large, extra-large 
        primary_action_label: 'Generar Factura',
        primary_action(values) {

            frappe.call({
                method: "qlip_moto_oriente.qlip_moto_oriente.services.generate_invoice.generate_sales_invoice",
                args: {
                    values:values
                },
                callback: function(r) {
                    if(!r.exc) {
                        if(r.message) {
                            
                            let m = [];
                            let flag = false;

                            if(r.message.success_sa_in){
                                m.push(__(`Factura ${r.message.sa_in_name} creada con exito`));
                                flag = true;
                            }
                            if(r.message.success_jo_en){
                                m.push(__(`Asiento ${r.message.jo_en_name} creado con exito`));
                                flag = true;
                            }
                            if(!r.message.success_sa_in)
                                m.push(__("No se ha podido crear factura"));

                            if(!r.message.success_jo_en)
                                m.push(__("No se ha podido crear asiento contable"));

                            frappe.msgprint(m);

                            if(flag)
                                d.hide();

                        } else {
                            frappe.msgprint([__("No se ha podido crear factura"),__("No se ha podido crear asiento contable")]);
                        }
                    }
                }
            });
            
        }
    });

    d.show();
}