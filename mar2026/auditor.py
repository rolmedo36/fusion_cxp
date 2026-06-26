import pandas as pd
import numpy as np
import os


def generar_reporte_auditoria_final():
    print("🚀 Generando Reporte Maestro de Auditoría ESGARI (v10)...")

    # 1. Configuración de archivos
    files = {
        'inv': '../archivos_csv/XX_RO_FACTURAS_REP.csv',
        'tax': '../archivos_csv/XX_RO_IMPUESTOS_REP.csv',
        'pag': '../archivos_csv/XX_RO_PAGOS_REP.csv',
        'req': '../archivos_csv/XX_RO_FACTURA_REQUI_REP.csv'
    }

    dfs = {}
    for key, path in files.items():
        if os.path.exists(path):
            # Leemos con dtype str para no perder ceros a la izquierda en cuentas
            df = pd.read_csv(path, low_memory=False)
            df.columns = df.columns.str.strip().str.upper()
            dfs[key] = df
            print(f"✅ Cargado: {key} ({len(df)} registros)")
        else:
            print(f"⚠️ No se encontró: {path}")
            dfs[key] = pd.DataFrame()

    # 2. Procesar Impuestos y Retenciones (Lógica de Factura SA-2820)
    df_tax_pivot = pd.DataFrame()
    if not dfs['tax'].empty:
        def clasificar_impuestos(row):
            cod = str(row.get('CODIGO_IMPUESTO', '')).upper()
            tipo = str(row.get('TIPO_LINEA', '')).upper()
            amt = row.get('TAX_AMT', 0)
            # IVA
            if 'IVA' in cod and 'RET' not in cod: return 'IVA'
            # Retenciones
            if 'RET' in cod or tipo == 'AWT':
                if '4' in cod or row.get('TAX_RATE') == 4: return 'RET_ISR_4'
                if 'ISR' in cod: return 'RET_ISR'
                return 'RET_IVA'
            return 'OTROS_TAX'

        dfs['tax']['CAT'] = dfs['tax'].apply(clasificar_impuestos, axis=1)
        df_tax_pivot = dfs['tax'].pivot_table(
            index='INVOICE_ID', columns='CAT', values='TAX_AMT', aggfunc='sum'
        ).fillna(0).reset_index()

    # 3. Consolidación de Datos (Merge)
    df_master = dfs['inv']
    if df_master.empty: return print("❌ Error: No hay datos de facturas.")

    if not df_tax_pivot.empty:
        df_master = pd.merge(df_master, df_tax_pivot, on='INVOICE_ID', how='left')
    if not dfs['pag'].empty:
        df_master = pd.merge(df_master, dfs['pag'], on='INVOICE_ID', how='left')
    if not dfs['req'].empty:
        df_master = pd.merge(df_master, dfs['req'], on='INVOICE_ID', how='left')

    # 4. Cálculos Financieros y Conversiones
    # Asegurar columnas numéricas
    cols_mon = ['IMPORTE', 'IMPORTE_PAGO', 'IVA', 'RET_IVA', 'RET_ISR', 'RET_ISR_4', 'ADELANTO_APLICADO']
    for c in cols_mon:
        df_master[c] = pd.to_numeric(df_master.get(c, 0), errors='coerce').fillna(0)

    # Subtotal: Importe - IVA - Retenciones (que vienen negativas en Oracle)
    df_master['SUBTOTAL'] = df_master['IMPORTE'] - df_master['IVA'] - df_master['RET_IVA'] - df_master['RET_ISR'] - \
                            df_master['RET_ISR_4']
    df_master['SALDO'] = df_master['IMPORTE'] - df_master['IMPORTE_PAGO']

    # Tipo de Cambio (Priorizar Pago, si no existe 1.0)
    tc = pd.to_numeric(df_master.get('TC_PAGO', 1.0), errors='coerce').fillna(1.0).replace(0, 1.0)

    for c in ['SUBTOTAL', 'IVA', 'RET_IVA', 'RET_ISR', 'RET_ISR_4', 'IMPORTE', 'SALDO', 'IMPORTE_PAGO',
              'ADELANTO_APLICADO']:
        df_master[f'{c} MXN'] = df_master[c] * tc

    # 5. Fechas y Mapeos de Auditoría
    for col_f, pref in [('FECHA', ''), ('FECHA_PAGO', '_PAGO')]:
        if col_f in df_master.columns:
            f_dt = pd.to_datetime(df_master[col_f], errors='coerce')
            df_master[f'SEMANA{pref}'] = f_dt.dt.isocalendar().week
            df_master[f'MES{pref}'] = f_dt.dt.month_name()

    # Estatus de Aprobación
    if 'ESTATUS_APROBACION' in df_master.columns:
        df_master['ESTATUS_APROBACION'] = df_master['ESTATUS_APROBACION'].apply(
            lambda x: 'NO VALIDADO' if str(x).strip().upper() == 'NEVER APPROVED' else 'VALIDADO'
        )

    # Estatus de Pago
    map_pago = {'Y': 'PAGADO', 'P': 'PARCIAL', 'N': 'PENDIENTE'}
    # Nos aseguramos de obtener la columna como Serie, si no existe, creamos una de 'N'
    estatus_serie = pd.Series(df_master.get('ESTATUS_PAGO', 'N'))

    # Si por alguna razón es un valor único, lo convertimos a Serie del tamaño del DataFrame
    if not isinstance(estatus_serie, pd.Series) or len(estatus_serie) != len(df_master):
        estatus_serie = pd.Series(['N'] * len(df_master))

    df_master['ESTATUS'] = estatus_serie.map(map_pago).fillna('PENDIENTE')

    # 6. Orden de Columnas según requerimiento de Auditoría
    columnas_finales = [
        'EMPRESA', 'NUM_PROV', 'PROVEEDOR', 'RFC', 'FACTURA', 'ERS', 'REQUISITION_NUMBER',
        'CUENTA_GASTO', 'CUENTA_BALANCE', 'UUID', 'FECHA', 'SEMANA', 'MES', 'MONEDA',
        'FECHA_PAGO', 'SEMANA_PAGO', 'MES_PAGO', 'NUM_PAGO', 'DESCRIPTION', 'BANCO_CUENTA',
        'FECHA_APLICACION', 'ADELANTO_APLICADO', 'ADELANTO_APLICADO MXN', 'IMPORTE_PAGO',
        'IMPORTE_PAGO MXN', 'SUBTOTAL', 'SUBTOTAL MXN', 'IVA', 'IVA MXN',
        'RET_IVA', 'RET_ISR', 'RET_ISR_4', 'IMPORTE', 'IMPORTE MXN', 'SALDO', 'SALDO MXN',
        'TC_PAGO', 'ORIGEN', 'ESTATUS'
    ]

    df_reporte = df_master.reindex(columns=columnas_finales)

    # 7. Exportación
    nombre_archivo = "Reporte_Auditoria_Fusion_ESGARI_FINAL.xlsx"
    df_reporte.to_excel(nombre_archivo, index=False)
    print(f"✅ ¡Éxito Total! El reporte se ha generado: {nombre_archivo}")


if __name__ == "__main__":
    generar_reporte_auditoria_final()