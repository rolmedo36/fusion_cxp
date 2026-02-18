import pandas as pd
import numpy as np
import os

def generar_reporte_auditoria_total():
    print("🚀 Iniciando consolidación final del Reporte de Auditoría...")

    # 1. Configuración de archivos de entrada
    files = {
        'inv': 'archivos_csv/XX_RO_FACTURAS_REP.csv',
        'tax': 'archivos_csv/XX_RO_IMPUESTOS_REP.csv',
        'pag': 'archivos_csv/XX_RO_PAGOS_REP.csv',
        'req': 'archivos_csv/XX_RO_FACTURA_REQUI_REP.csv'
    }

    dfs = {}
    for key, path in files.items():
        if os.path.exists(path):
            # Leemos con low_memory=False para evitar advertencias en UUIDs o ERS largos
            df = pd.read_csv(path, low_memory=False)
            df.columns = df.columns.str.strip().str.upper()
            dfs[key] = df
            print(f"✅ Cargado: {key} ({len(df)} registros)")
        else:
            print(f"⚠️ No se encontró: {path}. Se procesará con datos vacíos.")
            dfs[key] = pd.DataFrame()

    # 2. Procesar Impuestos (Pivote por Categoría)
    df_tax_pivot = pd.DataFrame()
    if not dfs['tax'].empty:
        def clasificar_impuestos_mx(row):
            rate = row.get('TAX_RATE', 0)
            amt = row.get('TAX_AMT', 0)
            # IVA 16% o 8%
            if rate in [16, 8] and amt > 0: return 'IVA'
            # Retención ISR 4% (Fletes)
            if rate == 4: return 'RET_ISR_4'
            # Retenciones (Montos negativos comúnmente)
            if amt < 0:
                if rate == 10: return 'RET_ISR'
                return 'RET_IVA'
            return 'OTROS_TAX'

        dfs['tax']['CAT'] = dfs['tax'].apply(clasificar_impuestos_mx, axis=1)
        df_tax_pivot = dfs['tax'].pivot_table(
            index='INVOICE_ID',
            columns='CAT',
            values='TAX_AMT',
            aggfunc='sum'
        ).fillna(0).reset_index()

    # 3. Consolidación de Datos (Merge)
    # Partimos de la tabla de Facturas que ya trae EMPRESA, ERS y Cuentas
    df_master = dfs['inv']

    # Unimos Impuestos
    if not df_tax_pivot.empty:
        df_master = pd.merge(df_master, df_tax_pivot, on='INVOICE_ID', how='left')

    # Unimos Pagos
    if not dfs['pag'].empty:
        # Nota: Si una factura tiene múltiples pagos, este merge los traerá todos
        df_master = pd.merge(df_master, dfs['pag'], on='INVOICE_ID', how='left')

    # Unimos Requisiciones
    if not dfs['req'].empty:
        df_master = pd.merge(df_master, dfs['req'], on='INVOICE_ID', how='left')

    # 4. Cálculos Automáticos
    # Tipo de Cambio del Pago (si no hay, asumimos 1.0 para MXN)
    tc_pago = df_master.get('TC_PAGO', 1.0).fillna(1.0)

    # Procesar Fechas, Semanas y Meses (Factura y Pago)
    for col_f, pref in [('FECHA', ''), ('FECHA_PAGO', '_PAGO')]:
        if col_f in df_master.columns:
            f_dt = pd.to_datetime(df_master[col_f], errors='coerce')
            df_master[f'SEMANA{pref}'] = f_dt.dt.isocalendar().week
            df_master[f'MES{pref}'] = f_dt.dt.month_name()

    # Cálculos Financieros
    df_master['IVA'] = df_master.get('IVA', 0).fillna(0)
    df_master['SUBTOTAL'] = df_master.get('IMPORTE', 0) - df_master['IVA']
    df_master['SALDO'] = df_master.get('IMPORTE', 0) - df_master.get('IMPORTE_PAGO', 0).fillna(0)

    # Conversiones a MXN
    cols_monetarias = ['SUBTOTAL', 'IVA', 'IMPORTE', 'IMPORTE_PAGO', 'SALDO', 'ADELANTO_APLICADO']
    for c in cols_monetarias:
        if c in df_master.columns:
            df_master[f'{c} MXN'] = df_master[c] * tc_pago

    # Traducir Estatus de pago
    if 'ESTATUS' in df_master.columns:
        map_est = {'Y': 'PAGADO', 'P': 'PARCIAL', 'N': 'PENDIENTE'}
        df_master['ESTATUS'] = df_master['ESTATUS'].map(map_est).fillna('PENDIENTE')

    # 5. Selección y Ordenamiento de Columnas Final (Orden de Auditoría)
    columnas_finales = [
        'EMPRESA', 'NUM_PROV', 'PROVEEDOR', 'RFC', 'FACTURA', 'ERS', 'REQUISITION_NUMBER',
        'CUENTA_GASTO', 'CUENTA_BALANCE', 'UUID', 'FECHA', 'SEMANA', 'MES', 'MONEDA',
        'FECHA_PAGO', 'SEMANA_PAGO', 'MES_PAGO', 'NUM_PAGO', 'DESCRIPTION', 'BANCO_CUENTA',
        'FECHA_APLICACION', 'ADELANTO_APLICADO', 'ADELANTO_APLICADO MXN', 'IMPORTE_PAGO',
        'IMPORTE_PAGO MXN', 'SUBTOTAL', 'SUBTOTAL MXN', 'IVA', 'IVA MXN',
        'RET_IVA', 'RET_ISR', 'RET_ISR_4', 'IMPORTE', 'IMPORTE MXN', 'SALDO', 'SALDO MXN',
        'TC_PAGO', 'ORIGEN', 'ESTATUS'
    ]

    # Reindexar para asegurar que el Excel tenga todas las columnas aunque estén vacías
    df_reporte = df_master.reindex(columns=columnas_finales)

    # 6. Exportación a Excel
    nombre_salida = "Reporte_Maestro_Auditoria_Fusion.xlsx"

    # Usamos XlsxWriter para poder dar formato si fuera necesario
    try:
        df_reporte.to_excel(nombre_salida, index=False, engine='xlsxwriter')
        print(f"\n✅ ¡Éxito! El reporte se ha generado correctamente: {nombre_salida}")
    except Exception as e:
        print(f"\n❌ Error al guardar el Excel: {e}")


if __name__ == "__main__":
    generar_reporte_auditoria_total()