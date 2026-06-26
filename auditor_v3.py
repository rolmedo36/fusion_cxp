import pandas as pd
import numpy as np
import os


def generar_reporte_auditoria_v9():
    print("🚀 Consolidando Reporte Maestro Final (v9)...")

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
            dfs[key] = pd.DataFrame()

    # 1. Impuestos y Retenciones
    df_tax_pivot = pd.DataFrame()
    if not dfs['tax'].empty:
        def clasificar(row):
            cod = str(row.get('CODIGO_IMPUESTO', '')).upper()
            tipo = str(row.get('TIPO_LINEA', '')).upper()
            if 'IVA' in cod and 'RET' not in cod: return 'IVA'
            if 'RET' in cod or tipo == 'AWT':
                if '4' in cod or row.get('TAX_RATE') == 4: return 'RET_ISR_4'
                return 'RET_ISR' if 'ISR' in cod else 'RET_IVA'
            return 'OTROS_TAX'

        dfs['tax']['CAT'] = dfs['tax'].apply(clasificar, axis=1)
        df_tax_pivot = dfs['tax'].pivot_table(index='INVOICE_ID', columns='CAT', values='TAX_AMT',
                                              aggfunc='sum').fillna(0).reset_index()

    # 2. Merge Maestro
    df = dfs['inv']
    if df.empty: return print("❌ Facturas no encontradas.")
    for key in ['tax', 'pag', 'req']:
        if not dfs[key].empty:
            df = pd.merge(df, df_tax_pivot if key == 'tax' else dfs[key], on='INVOICE_ID', how='left')

    # 3. Cálculos y Conversiones
    cols_mon = ['IMPORTE', 'IMPORTE_PAGO', 'IVA', 'RET_IVA', 'RET_ISR', 'RET_ISR_4', 'ADELANTO_APLICADO']
    for c in cols_mon: df[c] = df.get(c, 0.0).fillna(0.0)

    # Subtotal matemático: Total - IVA - Suma de Retenciones (que vienen negativas)
    df['SUBTOTAL'] = df['IMPORTE'] - df['IVA'] - df['RET_IVA'] - df['RET_ISR'] - df['RET_ISR_4']
    df['SALDO'] = df['IMPORTE'] - df['IMPORTE_PAGO']

    tc = df.get('TC_PAGO', 1.0).fillna(1.0).replace(0, 1.0)
    for c in ['SUBTOTAL', 'IVA', 'IMPORTE', 'SALDO', 'IMPORTE_PAGO', 'ADELANTO_APLICADO']:
        df[f'{c} MXN'] = df[c] * tc

    # 4. Tiempos y Mapeos
    for col_f, pref in [('FECHA', ''), ('FECHA_PAGO', '_PAGO')]:
        if col_f in df.columns:
            f_dt = pd.to_datetime(df[col_f], errors='coerce')
            df[f'SEMANA{pref}'] = f_dt.dt.isocalendar().week
            df[f'MES{pref}'] = f_dt.dt.month_name()

    if 'ESTATUS_APROBACION' in df.columns:
        df['ESTATUS_APROBACION'] = df['ESTATUS_APROBACION'].apply(
            lambda x: 'NO VALIDADO' if str(x).upper() == 'NEVER APPROVED' else 'VALIDADO')

    df['ESTATUS'] = df.get('ESTATUS_PAGO', 'N').map({'Y': 'PAGADO', 'P': 'PARCIAL', 'N': 'PENDIENTE'}).fillna(
        'PENDIENTE')

    # 5. Lista Definitiva de Columnas
    columnas_finales = [
        'EMPRESA', 'NUM_PROV', 'PROVEEDOR', 'RFC', 'FACTURA', 'ERS', 'REQUISITION_NUMBER',
        'CUENTA_GASTO', 'CUENTA_BALANCE', 'UUID', 'FECHA', 'SEMANA', 'MES', 'MONEDA',
        'FECHA_PAGO', 'SEMANA_PAGO', 'MES_PAGO', 'NUM_PAGO', 'DESCRIPTION', 'BANCO_CUENTA',
        'FECHA_APLICACION', 'ADELANTO_APLICADO', 'ADELANTO_APLICADO MXN', 'IMPORTE_PAGO',
        'IMPORTE_PAGO MXN', 'SUBTOTAL', 'SUBTOTAL MXN', 'IVA', 'IVA MXN',
        'RET_IVA', 'RET_ISR', 'RET_ISR_4', 'IMPORTE', 'IMPORTE MXN', 'SALDO', 'SALDO MXN',
        'TC_PAGO', 'ORIGEN', 'ESTATUS'
    ]

    df_reporte = df.reindex(columns=columnas_finales)
    df_reporte.to_excel("Reporte_Auditoria_V9_Contabilidad.xlsx", index=False)
    print("✅ Reporte V9 generado con Cuenta de Gasto detallada.")


if __name__ == "__main__":
    generar_reporte_auditoria_v9()