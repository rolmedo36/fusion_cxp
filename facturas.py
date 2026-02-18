import pandas as pd
import os


def generar_reporte_auditoria_cxp():
    print("🚀 Iniciando consolidación de reporte para Auditoría...")

    # 1. Definición de archivos (Nombres exactos de tus CSV)
    path_inv = 'archivos_csv/XX_RO_FACTURAS_REP.csv'
    path_tax = 'archivos_csv/XX_RO_IMPUESTOS_REP.csv'
    path_req = 'archivos_csv/XX_RO_FACTURA_REQUI_REP.csv'
    output_excel = "Reporte_CXP_Auditoria_Final.xlsx"

    # 2. Carga y Normalización
    try:
        df_inv = pd.read_csv(path_inv)
        df_tax = pd.read_csv(path_tax)
        df_req = pd.read_csv(path_req)

        for d in [df_inv, df_tax, df_req]:
            d.columns = d.columns.str.strip().str.upper()
    except Exception as e:
        print(f"❌ Error al cargar archivos: {e}")
        return

    # 3. Clasificación de Impuestos por TAX_RATE
    def clasificar_impuesto(row):
        rate = row.get('TAX_RATE', 0)
        amount = row.get('TAX_AMT', 0)
        if rate in [16, 8] and amount > 0:
            return f'IVA_{int(rate)}'
        elif rate == 4:
            return 'RET_ISR_4'
        elif amount < 0:
            if rate == 10: return 'RET_ISR_10'
            return 'RET_IVA'
        return 'OTROS_IMPUESTOS'

    df_tax['TIPO_IMPUESTO'] = df_tax.apply(clasificar_impuesto, axis=1)

    # 4. Pivote de Impuestos (Una fila por Factura)
    df_tax_pivot = df_tax.pivot_table(
        index='INVOICE_ID',
        columns='TIPO_IMPUESTO',
        values='TAX_AMT',
        aggfunc='sum'
    ).fillna(0).reset_index()

    # 5. Uniones (Merges)
    df_final = pd.merge(df_inv, df_tax_pivot, on='INVOICE_ID', how='left')
    df_final = pd.merge(df_final, df_req, on='INVOICE_ID', how='left')

    # 6. Lógica de Auditoría y Cálculos
    # Traducir estatus de pago
    estatus_dict = {'Y': 'PAGADO', 'P': 'PARCIAL', 'N': 'PENDIENTE'}
    if 'ESTATUS_PAGO' in df_final.columns:
        df_final['ESTATUS_PAGO'] = df_final['ESTATUS_PAGO'].map(estatus_dict).fillna('DESCONOCIDO')

    # Columnas de impuestos esperadas para asegurar el cálculo
    cols_imp = ['IVA_16', 'IVA_8', 'RET_IVA', 'RET_ISR_4', 'RET_ISR_10', 'OTROS_IMPUESTOS']
    for col in cols_imp:
        if col not in df_final.columns: df_final[col] = 0.0
        df_final[col] = df_final[col].fillna(0.0)

    # Cálculo Neto a Pagar (Total + montos negativos de retenciones)
    df_final['TOTAL_FACTURA'] = pd.to_numeric(df_final['TOTAL_FACTURA'], errors='coerce').fillna(0)
    df_final['NETO_A_PAGAR'] = df_final['TOTAL_FACTURA']

    # Sumamos las retenciones (que ya vienen negativas del query) para obtener el neto
    cols_a_restar = ['RET_IVA', 'RET_ISR_4', 'RET_ISR_10']
    for col in cols_a_restar:
        df_final['NETO_A_PAGAR'] += df_final[col]

    # Alerta de UUID faltante
    if 'UUID' in df_final.columns:
        df_final['VALIDACION_UUID'] = df_final['UUID'].apply(
            lambda x: 'OK' if pd.notnull(x) and str(x).strip() != '' else '⚠️ FALTA UUID'
        )

    # 7. Reordenar Columnas para Sentido Contable
    cols_orden = [
        'FECHA_FACTURA', 'ESTATUS_PAGO', 'NOMBRE_PROVEEDOR', 'RFC_PROVEEDOR',
        'FACTURA', 'UUID', 'REQUISITION_NUMBER', 'TOTAL_FACTURA', 'NETO_A_PAGAR',
        'IVA_16', 'RET_IVA', 'RET_ISR_4', 'VALIDACION_UUID', 'USUARIO_CAPTURA'
    ]

    # Seleccionar solo columnas existentes
    df_export = df_final[[c for c in cols_orden if c in df_final.columns]]

    # 8. Exportación Final
    try:
        df_export.to_excel(output_excel, index=False)
        print(f"✅ Reporte de Auditoría generado exitosamente: {output_excel}")
    except Exception as e:
        print(f"❌ Error al guardar Excel: {e}")


if __name__ == "__main__":
    generar_reporte_auditoria_cxp()