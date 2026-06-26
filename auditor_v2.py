import pandas as pd
import numpy as np
import os


def generar_reporte_auditoria_v8():
    print("🚀 Consolidando Reporte Final con todas las columnas (v8)...")

    files = {
        'inv': 'archivos_csv/XX_RO_FACTURAS_REP.csv',
        'tax': 'archivos_csv/XX_RO_IMPUESTOS_REP.csv',
        'pag': 'archivos_csv/XX_RO_PAGOS_REP.csv',
        'req': 'archivos_csv/XX_RO_FACTURA_REQUI_REP.csv'
    }

    dfs = {}
    for key, path in files.items():
        if os.path.exists(path):
            df = pd.read_csv(path, low_memory=False)
            df.columns = df.columns.str.strip().str.upper()
            dfs[key] = df
        else:
            print(f"⚠️ No se encontró {path}, se generarán datos vacíos para esa sección.")
            dfs[key] = pd.DataFrame()

    # 1. Procesamiento de Impuestos y Retenciones (Lógica SA-2820)
    df_tax_pivot = pd.DataFrame()
    if not dfs['tax'].empty:
        def clasificar_exacto(row):
            codigo = str(row.get('CODIGO_IMPUESTO', '')).upper()
            tipo = str(row.get('TIPO_LINEA', '')).upper()
            amt = row.get('TAX_AMT', 0)

            # IVA Acreditale
            if 'IVA' in codigo and 'RET' not in codigo: return 'IVA'
            # Retenciones (AWT o códigos con RET)
            if 'RET' in codigo or tipo == 'AWT':
                if '4' in codigo or row.get('TAX_RATE') == 4: return 'RET_ISR_4'
                if 'ISR' in codigo: return 'RET_ISR'
                return 'RET_IVA'
            return 'OTROS_TAX'

        dfs['tax']['CAT'] = dfs['tax'].apply(clasificar_exacto, axis=1)
        df_tax_pivot = dfs['tax'].pivot_table(index='INVOICE_ID', columns='CAT', values='TAX_AMT',
                                              aggfunc='sum').fillna(0).reset_index()

    # 2. Merge de todas las fuentes
    df = dfs['inv']
    if df.empty: return print("❌ Error: Archivo de facturas vacío.")

    if not df_tax_pivot.empty: df = pd.merge(df, df_tax_pivot, on='INVOICE_ID', how='left')
    if not dfs['pag'].empty: df = pd.merge(df, dfs['pag'], on='INVOICE_ID', how='left')
    if not dfs['req'].empty: df = pd.merge(df, dfs['req'], on='INVOICE_ID', how='left')

    # 3. Preparación de Columnas y Cálculos
    # Asegurar que todas las columnas monetarias existan
    cols_monetarias = ['IMPORTE', 'IMPORTE_PAGO', 'IVA', 'RET_IVA', 'RET_ISR', 'RET_ISR_4', 'ADELANTO_APLICADO',
                       'TC_PAGO', 'TC_FACTURA']
    for c in cols_monetarias:
        df[c] = df.get(c, 0.0).fillna(0.0 if 'TC' not in c else 1.0)

    # Cálculo del Subtotal (Total - Impuestos - Retenciones)
    df['SUBTOTAL'] = df['IMPORTE'] - df['IVA'] - df['RET_IVA'] - df['RET_ISR'] - df['RET_ISR_4']
    df['SALDO'] = df['IMPORTE'] - df['IMPORTE_PAGO']

    # Conversiones MXN (Usando TC_PAGO como base para reporte de auditoría)
    tc = df['TC_PAGO'].replace(0, 1.0)
    for c in ['SUBTOTAL', 'IVA', 'RET_IVA', 'RET_ISR', 'RET_ISR_4', 'IMPORTE', 'SALDO', 'ADELANTO_APLICADO',
              'IMPORTE_PAGO']:
        df[f'{c} MXN'] = df[c] * tc

    # 4. Fechas y Tiempos
    for col_f, pref in [('FECHA', ''), ('FECHA_PAGO', '_PAGO')]:
        if col_f in df.columns:
            f_dt = pd.to_datetime(df[col_f], errors='coerce')
            df[f'SEMANA{pref}'] = f_dt.dt.isocalendar().week
            df[f'MES{pref}'] = f_dt.dt.month_name()

    # 5. Mapeo de Estatus (Lógica NEVER APPROVED)
    if 'ESTATUS_APROBACION' in df.columns:
        df['ESTATUS_APROBACION'] = df['ESTATUS_APROBACION'].apply(
            lambda x: 'NO VALIDADO' if str(x).strip().upper() == 'NEVER APPROVED' else 'VALIDADO'
        )

    # Mapeo de Estatus de Pago (IA.PAYMENT_STATUS_FLAG)
    if 'ESTATUS_PAGO' in df.columns:
        df['ESTATUS'] = df['ESTATUS_PAGO'].map({'Y': 'PAGADO', 'P': 'PARCIAL', 'N': 'PENDIENTE'}).fillna('PENDIENTE')
    else:
        df['ESTATUS'] = 'PENDIENTE'

    # 6. Reordenamiento Final según tu lista exacta
    columnas_finales = [
        'EMPRESA', 'NUM_PROV', 'PROVEEDOR', 'RFC', 'FACTURA', 'ERS', 'REQUISITION_NUMBER',
        'CUENTA_GASTO', 'CUENTA_BALANCE', 'UUID', 'FECHA', 'SEMANA', 'MES', 'MONEDA',
        'FECHA_PAGO', 'SEMANA_PAGO', 'MES_PAGO', 'NUM_PAGO', 'DESCRIPTION', 'BANCO_CUENTA',
        'FECHA_APLICACION', 'ADELANTO_APLICADO', 'ADELANTO_APLICADO MXN', 'IMPORTE_PAGO',
        'IMPORTE_PAGO MXN', 'SUBTOTAL', 'SUBTOTAL MXN', 'IVA', 'IVA MXN',
        'RET_IVA', 'RET_ISR', 'RET_ISR_4', 'IMPORTE', 'IMPORTE MXN', 'SALDO', 'SALDO MXN',
        'TC_PAGO', 'ORIGEN', 'ESTATUS'
    ]

    # Reindexar asegura que si falta alguna columna en el SQL, el Excel no falle y la ponga vacía
    df_reporte = df.reindex(columns=columnas_finales)

    output = "Reporte_Maestro_Auditoria_V8_FINAL.xlsx"
    df_reporte.to_excel(output, index=False)
    print(f"✅ ¡Proceso Completo! Reporte generado: {output}")


if __name__ == "__main__":
    generar_reporte_auditoria_v8()