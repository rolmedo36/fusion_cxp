import pandas as pd
import os


def procesar_reporte_cxp_historico():
    print("🚀 Iniciando consolidación con búsqueda de tasas históricas...")

    # Carga de archivos
    df_flujo = pd.read_csv('archivos_csv/XX_RO_CXP_MODEL_REP.csv')
    df_pagos = pd.read_csv('archivos_csv/XX_RO_PAGOS_MODEL_REP.csv')
    df_tasa = pd.read_csv('archivos_csv/XX_RO_RATES_MODEL_REP.csv')

    # Normalización de columnas
    for df in [df_flujo, df_pagos, df_tasa]:
        df.columns = df.columns.str.strip().str.upper()

    # --- PREPARACIÓN DE TASAS ---
    # Aseguramos que la columna de fecha de tasa sea string YYYY-MM-DD para el match
    # Buscamos la columna de fecha en el archivo de tasas (probablemente FECHA_TASA o CONVERSION_DATE)
    col_fecha_tasa = [c for c in df_tasa.columns if 'FECHA' in c or 'DATE' in c][0]
    df_tasa[col_fecha_tasa] = df_tasa[col_fecha_tasa].str.slice(0, 10)

    # Buscamos la columna de la tasa numérica
    col_valor_tasa = [c for c in df_tasa.columns if 'RATE' in c or 'TASA' in c and 'FECHA' not in c][0]

    # Creamos un diccionario simple para búsqueda rápida: { '2025-01-15': 17.50 }
    dict_tasas = df_tasa.set_index(col_fecha_tasa)[col_valor_tasa].to_dict()

    # --- PREPARACIÓN DE FACTURAS Y PAGOS ---
    # Limpieza de fechas en los archivos principales (tomar solo los primeros 10 caracteres YYYY-MM-DD)
    if 'INVOICE_DATE' in df_flujo.columns:
        df_flujo['FECHA_LIMPIA_INV'] = df_flujo['INVOICE_DATE'].str.slice(0, 10)

    if 'ACCOUNTING_DATE' in df_pagos.columns:
        df_pagos['FECHA_LIMPIA_PAG'] = df_pagos['ACCOUNTING_DATE'].str.slice(0, 10)

    # 1. Unir Facturas con Pagos
    df_final = pd.merge(df_flujo, df_pagos, on='INVOICE_ID', how='left', suffixes=('', '_PAGO'))

    # --- EL MATCH DE TASAS ---

    # 2. Match tasa para la fecha de la FACTURA
    df_final['TASA_FECHA_FACTURA'] = df_final['FECHA_LIMPIA_INV'].map(dict_tasas)

    # 3. Match tasa para la fecha del PAGO
    df_final['TASA_FECHA_PAGO'] = df_final['FECHA_LIMPIA_PAG'].map(dict_tasas)

    # 4. Cálculos de conversión
    # Importe Factura en MXN (usando tasa del día de factura)
    df_final['INVOICE_AMOUNT'] = pd.to_numeric(df_final['INVOICE_AMOUNT'], errors='coerce').fillna(0)

    df_final['IMPORTE_FACTURA_MXN'] = df_final.apply(
        lambda x: x['INVOICE_AMOUNT'] * x['TASA_FECHA_FACTURA']
        if str(x['INVOICE_CURRENCY_CODE']).upper() == 'USD' and pd.notnull(x['TASA_FECHA_FACTURA'])
        else x['INVOICE_AMOUNT'], axis=1
    )

    # Importe Pago en MXN (usando tasa del día de pago)
    if 'AMOUNT' in df_final.columns:  # 'AMOUNT' es el nombre técnico en pagos
        df_final['AMOUNT'] = pd.to_numeric(df_final['AMOUNT'], errors='coerce').fillna(0)
        df_final['IMPORTE_PAGO_MXN'] = df_final.apply(
            lambda x: x['AMOUNT'] * x['TASA_FECHA_PAGO']
            if str(x['INVOICE_CURRENCY_CODE']).upper() == 'USD' and pd.notnull(x['TASA_FECHA_PAGO'])
            else x['AMOUNT'], axis=1
        )

    # 5. Guardar
    output_excel = "Reporte_CXP_Tasas_Historicas.xlsx"
    df_final.drop(columns=['FECHA_LIMPIA_INV', 'FECHA_LIMPIA_PAG'], inplace=True, errors='ignore')
    df_final.to_excel(output_excel, index=False)

    print(f"✅ Reporte generado con tasas históricas por movimiento: {output_excel}")


if __name__ == "__main__":
    procesar_reporte_cxp_historico()