import pandas as pd
df = pd.read_csv("archivos_csv/payments_ers_rep.csv")

print(f"📊 Total registros: {len(df)}")
print(f"\n📊 Distribución por TIPO_ORIGEN:")
print(df['TIPO_ORIGEN'].value_counts())

print(f"\n🔍 Muestra de PREPAYMENT:")
prepago = df[df['TIPO_ORIGEN'] == 'PREPAYMENT']
print(prepago[['INVOICE_ID', 'FACTURA_ADELANTO', 'ADELANTO_USD', 'ADELANTO_MXN', 'MONEDA']].head(10))

print(f"\n📊 PREPAYMENT con ADELANTO_MXN:", prepago['ADELANTO_MXN'].notna().sum())
print(f"📊 PREPAYMENT sin ADELANTO_MXN:", prepago['ADELANTO_MXN'].isna().sum())

print(f"\n🔍 Muestra de ERS:")
print(df[df['TIPO_ORIGEN'] == 'ERS'][['INVOICE_ID', 'ERS', 'ORDEN_COMPRA', 'MONEDA']].head(5))