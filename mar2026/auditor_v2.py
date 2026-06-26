import pandas as pd
import numpy as np
import os


def generar_reporte_auditoria_esgari_COMPLETO_V30():
    print("🚀 Restaurando todos los campos (Semana, Mes, Pagos) y formatos (v30)...")
    path = '../archivos_csv/'

    # 1. CARGA DE ARCHIVOS
    archivos = {
        'inv': 'XX_RO_FACTURAS_REP.csv', 'tax': 'XX_RO_IMPUESTOS_REP.csv',
        'pag': 'XX_RO_PAGOS_REP.csv', 'req': 'XX_RO_FACTURA_REQUI_REP.csv',
        'plan': 'XX_RO_PLAN_CUENTAS_REP.csv'
    }

    dfs = {}
    for key, nombre in archivos.items():
        fpath = f'{path}{nombre}'
        if os.path.exists(fpath):
            dfs[key] = pd.read_csv(fpath, low_memory=False).rename(columns=lambda x: x.strip().upper())
            if 'INVOICE_ID' in dfs[key].columns:
                dfs[key]['INVOICE_ID'] = dfs[key]['INVOICE_ID'].astype(str)
        else:
            dfs[key] = pd.DataFrame()

    if dfs['inv'].empty: return print("❌ Error: Sin archivo base de facturas.")

    # 2. PROCESAMIENTO DE CUENTAS
    def extraer_cta(c):
        partes = str(c).split('-')
        return partes[4] if len(partes) >= 5 else ""

    dfs['inv']['CTA_NUM'] = dfs['inv']['CUENTA_GASTO'].apply(extraer_cta).astype(str)
    if not dfs['plan'].empty:
        dfs['plan']['CUENTA_NUM'] = dfs['plan']['CUENTA_NUM'].astype(str)
        dfs['inv'] = pd.merge(dfs['inv'], dfs['plan'], left_on='CTA_NUM', right_on='CUENTA_NUM', how='left')
        dfs['inv']['CUENTA_GASTO_FULL'] = dfs['inv']['CTA_NUM'] + " - " + dfs['inv']['CUENTA_DESCRIPCION'].fillna(
            "DESC NO ENCONTRADA")
    else:
        dfs['inv']['CUENTA_GASTO_FULL'] = dfs['inv']['CUENTA_GASTO']

    # 3. UNIÓN DE OTROS DATOS (TAX, PAGOS, REQ)
    if not dfs['tax'].empty:
        def clasificar_tax(row):
            cod, tipo = str(row.get('CODIGO_IMPUESTO', '')).upper(), str(row.get('TIPO_LINEA', '')).upper()
            if 'IVA' in cod and 'RET' not in cod: return 'IVA'
            if 'RET' in cod or tipo == 'AWT':
                if '4' in cod or row.get('TAX_RATE') == 4: return 'RET_ISR_4'
                return 'RET_ISR' if 'ISR' in cod else 'RET_IVA'
            return 'OTROS'

        dfs['tax']['CAT'] = dfs['tax'].apply(clasificar_tax, axis=1)
        tax_p = dfs['tax'].pivot_table(index='INVOICE_ID', columns='CAT', values='TAX_AMT', aggfunc='sum').fillna(
            0).reset_index()
        dfs['inv'] = pd.merge(dfs['inv'], tax_p, on='INVOICE_ID', how='left')

    if not dfs['pag'].empty:
        dfs['inv'] = pd.merge(dfs['inv'], dfs['pag'].drop_duplicates(subset=['INVOICE_ID']), on='INVOICE_ID',
                              how='left')
    if not dfs['req'].empty:
        dfs['inv'] = pd.merge(dfs['inv'], dfs['req'].drop_duplicates(subset=['INVOICE_ID']), on='INVOICE_ID',
                              how='left')

    # 4. MAPEOS DE ESTATUS
    if 'ESTATUS_APROBACION' in dfs['inv'].columns:
        dfs['inv']['ESTATUS_APROBACION'] = dfs['inv']['ESTATUS_APROBACION'].apply(
            lambda x: 'NO VALIDADO' if str(x).strip().upper() == 'NEVER APPROVED' else 'VALIDADO'
        )
    map_pago = {'Y': 'PAGADO', 'P': 'PARCIAL', 'N': 'PENDIENTE'}
    dfs['inv']['ESTATUS'] = dfs['inv'].get('ESTATUS_PAGO', 'N').map(map_pago).fillna('PENDIENTE')

    # 5. TRATAMIENTO DE FECHAS, SEMANAS Y MESES
    meses_es = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
                7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}

    # Procesamos Factura y Pago
    for f_col, pref in [('FECHA', ''), ('FECHA_PAGO', '_PAGO')]:
        if f_col in dfs['inv'].columns:
            # Convertir a datetime nativo
            dt_serie = pd.to_datetime(dfs['inv'][f_col], errors='coerce')
            # Extraer Semana y Mes (Campos solicitados)
            dfs['inv'][f'SEMANA{pref}'] = dt_serie.dt.isocalendar().week
            dfs['inv'][f'MES{pref}'] = dt_serie.dt.month.map(meses_es)
            # Guardar como fecha limpia para Excel
            dfs['inv'][f_col] = dt_serie.dt.tz_localize(None)

    # 6. CÁLCULOS MONETARIOS
    cols_money = ['IMPORTE', 'IVA', 'RET_IVA', 'RET_ISR', 'RET_ISR_4', 'IMPORTE_PAGO', 'ADELANTO_APLICADO']
    for c in cols_money:
        dfs['inv'][c] = pd.to_numeric(dfs['inv'].get(c, 0), errors='coerce').fillna(0)

    dfs['inv']['SUBTOTAL'] = dfs['inv']['IMPORTE'] - dfs['inv'].get('IVA', 0) - dfs['inv'].get('RET_IVA', 0) - dfs[
        'inv'].get('RET_ISR', 0) - dfs['inv'].get('RET_ISR_4', 0)
    dfs['inv']['SALDO'] = dfs['inv']['IMPORTE'] - dfs['inv'].get('IMPORTE_PAGO', 0)

    tc = pd.to_numeric(dfs['inv'].get('TC_PAGO', 1.0), errors='coerce').fillna(1.0).replace(0, 1.0)
    for c in ['SUBTOTAL', 'IVA', 'IMPORTE', 'SALDO', 'IMPORTE_PAGO', 'ADELANTO_APLICADO']:
        dfs['inv'][f'{c}_MXN'] = dfs['inv'].get(c, 0) * tc

    # 7. EXPORTACIÓN CON TODAS LAS COLUMNAS DE LAS CAPTURAS
    columnas_finales = [
        'EMPRESA', 'NUM_PROV', 'PROVEEDOR', 'RFC', 'FACTURA', 'ERS', 'REQUISITION_NUMBER',
        'CUENTA_GASTO_FULL', 'CUENTA_BALANCE', 'UUID', 'FECHA', 'SEMANA', 'MES', 'MONEDA',
        'FECHA_PAGO', 'SEMANA_PAGO', 'MES_PAGO', 'NUM_PAGO', 'DESCRIPTION', 'BANCO_CUENTA',
        'FECHA_APLICACION', 'ADELANTO_APLICADO', 'ADELANTO_APLICADO_MXN', 'IMPORTE_PAGO',
        'IMPORTE_PAGO_MXN', 'SUBTOTAL', 'SUBTOTAL_MXN', 'IVA', 'IVA_MXN', 'RET_IVA',
        'RET_ISR', 'RET_ISR_4', 'IMPORTE', 'IMPORTE_MXN', 'SALDO', 'SALDO_MXN',
        'TC_PAGO', 'ORIGEN', 'ESTATUS_APROBACION', 'ESTATUS'
    ]

    df_final = dfs['inv'].reindex(columns=columnas_finales)
    df_final.rename(columns={'CUENTA_GASTO_FULL': 'CUENTA_GASTO'}, inplace=True)

    output_file = "REPORTE_AUDITORIA_MASTER_V30.xlsx"
    writer = pd.ExcelWriter(output_file, engine='xlsxwriter', datetime_format='dd/mm/yyyy')
    df_final.to_excel(writer, index=False, sheet_name='Auditoria')

    workbook = writer.book
    worksheet = writer.sheets['Auditoria']

    # Formatos
    fmt_money = workbook.add_format({'num_format': '$#,##0.00'})
    fmt_date = workbook.add_format({'num_format': 'dd/mm/yyyy', 'align': 'center'})
    fmt_hdr = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})

    for i, col in enumerate(df_final.columns):
        worksheet.write(0, i, col, fmt_hdr)
        if any(x in col for x in ['IMPORTE', 'SUBTOTAL', 'IVA', 'RET_', 'SALDO', 'ADELANTO']):
            worksheet.set_column(i, i, 16, fmt_money)
        elif any(x in col for x in ['FECHA']):
            worksheet.set_column(i, i, 14, fmt_date)
        else:
            worksheet.set_column(i, i, 22)

    writer.close()
    print(f"✅ ¡Todo recuperado! Reporte V30 generado con Semana, Mes, Pagos y Formatos.")


if __name__ == "__main__":
    generar_reporte_auditoria_esgari_COMPLETO_V30()