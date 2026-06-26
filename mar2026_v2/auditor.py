
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import logging
import sys
import os

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('audit_merge.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class AuditMasterMerger:
    """Clase para merge de CSVs de Oracle Fusion"""

    def __init__(self, csv_folder: str = './archivos_csv',
                 output_folder: str = './output'):
        self.csv_folder = Path(csv_folder)
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)

        self.required_files = {
            'core_invoices': 'core_invoices.csv',
            'payment_schedules': 'payment_schedules.csv',
            'payments_applied': 'payments_applied.csv',
            'distributions': 'distributions.csv',
            'taxes': 'taxes.csv',
            'prepayments_ers': 'prepayments_ers.csv'
        }

    def load_csv(self, key: str, required: bool = True) -> pd.DataFrame:
        """Carga un CSV con mapeo inteligente de columnas"""
        filepath = self.csv_folder / self.required_files[key]
        logger.info(f"📂 Cargando: {filepath}")

        try:
            if not filepath.exists():
                if required:
                    raise FileNotFoundError(f"Archivo requerido no encontrado: {filepath}")
                logger.warning(f"⚠ Archivo opcional no encontrado: {filepath}")
                return pd.DataFrame()

            df = pd.read_csv(
                filepath,
                encoding='utf-8',
                dtype=str,
                na_values=['', 'NULL', 'null', 'None'],
                keep_default_na=True,
                low_memory=False
            )

            # Mapeo específico para core_invoices (basado en diagnóstico real)
            if key == 'core_invoices':
                renames = {}

                # RFC → INCOME_TAX_ID
                if 'INCOME_TAX_ID' in df.columns and 'RFC' not in df.columns:
                    renames['INCOME_TAX_ID'] = 'RFC'
                    logger.info("✓ Renombrando INCOME_TAX_ID -> RFC")

                # UUID → GLOBAL_ATTRIBUTE1
                if 'GLOBAL_ATTRIBUTE1' in df.columns and 'UUID' not in df.columns:
                    renames['GLOBAL_ATTRIBUTE1'] = 'UUID'
                    logger.info("✓ Renombrando GLOBAL_ATTRIBUTE1 -> UUID")

                # EXCHANGE_RATE → TIPO_CAMBIO_FACTURA
                if 'TIPO_CAMBIO_FACTURA' in df.columns and 'EXCHANGE_RATE' not in df.columns:
                    renames['TIPO_CAMBIO_FACTURA'] = 'EXCHANGE_RATE'
                    logger.info("✓ Renombrando TIPO_CAMBIO_FACTURA -> EXCHANGE_RATE")

                if renames:
                    df = df.rename(columns=renames)

                logger.info(f"✓ Columnas mapeadas en core_invoices: {len(df.columns)} columnas")

            # Mapeo para payment_schedules
            elif key == 'payment_schedules':
                renames = {}
                if 'FECHA_VENCIMIENTO' not in df.columns and 'DUE_DATE' in df.columns:
                    renames['DUE_DATE'] = 'FECHA_VENCIMIENTO'
                if 'SALDO_USD' not in df.columns and 'AMOUNT_REMAINING' in df.columns:
                    renames['AMOUNT_REMAINING'] = 'SALDO_USD'
                if 'IMPORTE_BRUTO_USD' not in df.columns and 'GROSS_AMOUNT' in df.columns:
                    renames['GROSS_AMOUNT'] = 'IMPORTE_BRUTO_USD'
                if renames:
                    df = df.rename(columns=renames)

            # Mapeo para payments_applied
            elif key == 'payments_applied':
                renames = {}
                if 'NUM_PAGO' not in df.columns and 'CHECK_NUMBER' in df.columns:
                    renames['CHECK_NUMBER'] = 'NUM_PAGO'
                if 'BANCO_CUENTA' not in df.columns and 'BANK_ACCOUNT_NAME' in df.columns:
                    renames['BANK_ACCOUNT_NAME'] = 'BANCO_CUENTA'
                if 'FECHA_APLICACION' not in df.columns and 'ACCOUNTING_DATE' in df.columns:
                    renames['ACCOUNTING_DATE'] = 'FECHA_APLICACION'
                if 'IMPORTE_PAGO_USD' not in df.columns and 'AMOUNT' in df.columns:
                    renames['AMOUNT'] = 'IMPORTE_PAGO_USD'
                if 'TIPO_CAMBIO_PAGO' not in df.columns and 'EXCHANGE_RATE' in df.columns:
                    renames['EXCHANGE_RATE'] = 'TIPO_CAMBIO_PAGO'
                if renames:
                    df = df.rename(columns=renames)

            # Mapeo para distributions
            elif key == 'distributions':
                renames = {}
                if 'CUENTA_CONTABLE_GASTO' not in df.columns and 'CONCATENATED_SEGMENTS' in df.columns:
                    renames['CONCATENATED_SEGMENTS'] = 'CUENTA_CONTABLE_GASTO'
                if 'CC_DEPARTAMENTO' not in df.columns and 'SEGMENT2' in df.columns:
                    renames['SEGMENT2'] = 'CC_DEPARTAMENTO'
                if 'IMPORTE_DISTRIBUCION_USD' not in df.columns and 'AMOUNT' in df.columns:
                    renames['AMOUNT'] = 'IMPORTE_DISTRIBUCION_USD'
                if renames:
                    df = df.rename(columns=renames)

            # Mapeo para taxes
            elif key == 'taxes':
                renames = {}
                if 'TIPO_IMPUESTO' not in df.columns and 'TAX_TYPE_CODE' in df.columns:
                    renames['TAX_TYPE_CODE'] = 'TIPO_IMPUESTO'
                if 'IMPUESTO_USD' not in df.columns and 'TAX_AMT' in df.columns:
                    renames['TAX_AMT'] = 'IMPUESTO_USD'
                if 'IMPUESTO_MXN' not in df.columns and 'TAX_AMT_FUNCL_CURR' in df.columns:
                    renames['TAX_AMT_FUNCL_CURR'] = 'IMPUESTO_MXN'
                if renames:
                    df = df.rename(columns=renames)

            # Mapeo para prepayments_ers
            elif key == 'prepayments_ers':
                renames = {}
                if 'ADELANTO_USD' not in df.columns and 'INVOICE_AMOUNT' in df.columns:
                    renames['INVOICE_AMOUNT'] = 'ADELANTO_USD'
                if 'FECHA_APLICACION' not in df.columns and 'ACCOUNTING_DATE' in df.columns:
                    renames['ACCOUNTING_DATE'] = 'FECHA_APLICACION'
                if 'ORDEN_COMPRA' not in df.columns and 'SEGMENT1' in df.columns:
                    renames['SEGMENT1'] = 'ORDEN_COMPRA'
                if renames:
                    df = df.rename(columns=renames)

            logger.info(f"✓ Cargado {key}: {len(df)} filas, {len(df.columns)} columnas")
            return df

        except Exception as e:
            if required:
                logger.error(f"❌ Error cargando {key}: {e}")
                raise
            logger.warning(f"⚠ Error opcional en {key}: {e}")
            return pd.DataFrame()

    def convert_numeric(self, df: pd.DataFrame, columns: list) -> pd.DataFrame:
        """Convierte columnas a numérico"""
        for col in columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df

    def convert_dates(self, df: pd.DataFrame, columns: list) -> pd.DataFrame:
        """Convierte columnas a datetime (maneja formato ISO con timezone)"""
        for col in columns:
            if col in df.columns:
                # Intentar formato ISO con timezone primero
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce', utc=True)
                    # Convertir a timezone naive para consistencia
                    df[col] = df[col].dt.tz_localize(None)
                except:
                    # Fallback a formatos estándar
                    df[col] = pd.to_datetime(df[col], errors='coerce',
                                             format='%Y-%m-%d %H:%M:%S')
                    if df[col].isna().all():
                        df[col] = pd.to_datetime(df[col], errors='coerce',
                                                 format='%Y-%m-%d')
        return df

    def merge_all(self) -> pd.DataFrame:
        """Proceso principal de merge - 1 fila por factura-pago"""
        logger.info("🚀 Iniciando proceso de merge...")

        # Cargar CSVs
        core = self.load_csv('core_invoices', required=True)
        if core.empty:
            logger.error("❌ No hay datos base (core_invoices). Deteniendo proceso.")
            return pd.DataFrame()

        schedules = self.load_csv('payment_schedules', required=False)
        payments = self.load_csv('payments_applied', required=False)
        distributions = self.load_csv('distributions', required=False)
        taxes = self.load_csv('taxes', required=False)
        prepayments = self.load_csv('prepayments_ers', required=False)

        # ============================================================
        # PASO 1: Convertir tipos de datos en TODOS los dataframes
        # ============================================================
        numeric_cols_core = ['INVOICE_AMOUNT', 'TOTAL_TAX_AMOUNT', 'EXCHANGE_RATE',
                             'TIPO_CAMBIO_FACTURA', 'IMPORTE_BRUTO_USD']
        core = self.convert_numeric(core, numeric_cols_core)
        core = self.convert_dates(core, ['FECHA', 'TERMS_DATE'])

        # Payment Schedules
        if not schedules.empty:
            sched_numeric = ['IMPORTE_BRUTO_USD', 'SALDO_USD', 'SALDO_MXN', 'IMPORTE_BRUTO_MXN']
            schedules = self.convert_numeric(schedules, sched_numeric)
            schedules = self.convert_dates(schedules, ['FECHA_VENCIMIENTO'])

        # Payments Applied
        if not payments.empty:
            pay_numeric = ['IMPORTE_PAGO_USD', 'IMPORTE_PAGO_MXN', 'TIPO_CAMBIO_PAGO']
            payments = self.convert_numeric(payments, pay_numeric)
            payments = self.convert_dates(payments, ['FECHA_APLICACION'])

        # Distributions
        if not distributions.empty:
            dist_numeric = ['IMPORTE_DISTRIBUCION_USD']
            distributions = self.convert_numeric(distributions, dist_numeric)

        # Taxes
        if not taxes.empty:
            tax_numeric = ['IMPUESTO_USD', 'IMPUESTO_MXN']
            taxes = self.convert_numeric(taxes, tax_numeric)

            # Clasificar impuestos si no existe TIPO_IMPUESTO
            if 'TIPO_IMPUESTO' not in taxes.columns and 'TAX_TYPE_CODE' in taxes.columns:
                def clasificar_impuesto(tax_code):
                    if pd.isna(tax_code):
                        return 'OTRO'
                    tax_upper = str(tax_code).upper()
                    if 'IVA' in tax_upper and 'RET' not in tax_upper:
                        return 'IVA'
                    elif 'RET_IVA' in tax_upper or ('RET' in tax_upper and 'IVA' in tax_upper):
                        return 'RETENCION_IVA'
                    elif 'RET_ISR' in tax_upper and '4' not in tax_upper:
                        return 'RETENCION_ISR'
                    elif 'ISR_4' in tax_upper or ('4' in tax_upper and 'ISR' in tax_upper):
                        return 'RETENCION_ISR_4'
                    else:
                        return 'OTRO'

                taxes['TIPO_IMPUESTO'] = taxes['TAX_TYPE_CODE'].apply(clasificar_impuesto)
                logger.info("✓ Clasificación de impuestos creada desde TAX_TYPE_CODE")

        # Prepayments
        if not prepayments.empty:
            prep_numeric = ['ADELANTO_USD']
            prepayments = self.convert_numeric(prepayments, prep_numeric)
            prepayments = self.convert_dates(prepayments, ['FECHA_APLICACION'])

        # ============================================================
        # PASO 2: Merge Core + Payment Schedules (1 fila por invoice)
        # ============================================================
        if not schedules.empty:
            # Agregar sufijos para claridad
            result = core.merge(schedules, on='INVOICE_ID', how='left', suffixes=('', '_SCHED'))
            logger.info(f"✓ Merge con schedules: {len(result)} filas")
        else:
            result = core.copy()

        # ============================================================
        # PASO 3: Merge con Payments Applied (EXPANDIR a 1 fila por pago)
        # ============================================================
        if not payments.empty:
            # NO AGREGAR pagos - mantener 1 fila por pago
            # Usar left join para mantener facturas sin pago también
            result = result.merge(payments, on='INVOICE_ID', how='left', suffixes=('', '_PAY'))
            logger.info(f"✓ Merge con payments (expandido): {len(result)} filas")

            # Si una factura tiene múltiples pagos, ahora tendrá múltiples filas
            # Las facturas sin pago tendrán NULL en columnas de pago
        else:
            logger.warning("⚠ No hay pagos aplicados disponibles")

        # ============================================================
        # PASO 4: Merge con Distributions (AGREGAR por invoice)
        # ============================================================
        if not distributions.empty:
            # AGREGAR distributions por INVOICE_ID (no expandir)
            dist_agg = distributions.groupby('INVOICE_ID').agg({
                'CUENTA_CONTABLE_GASTO': lambda x: ' | '.join(x.dropna().astype(str).unique()[:3]),
                'CC_DEPARTAMENTO': lambda x: ' | '.join(x.dropna().astype(str).unique()[:3]),
                'IMPORTE_DISTRIBUCION_USD': 'sum',
                'DESCRIPTION': 'first'
            }).reset_index()
            result = result.merge(dist_agg, on='INVOICE_ID', how='left')
            logger.info(f"✓ Merge con distributions (agregado): {len(result)} filas")

        # ============================================================
        # PASO 5: Merge con Taxes (PIVOTEAR por invoice)
        # ============================================================
        if not taxes.empty and 'TIPO_IMPUESTO' in taxes.columns and 'IMPUESTO_MXN' in taxes.columns:
            taxes_pivot = taxes.pivot_table(
                index='INVOICE_ID',
                columns='TIPO_IMPUESTO',
                values='IMPUESTO_MXN',
                aggfunc='sum',
                fill_value=0
            ).reset_index()
            tax_cols = {c: f'{c}_MXN' if c != 'INVOICE_ID' else c for c in taxes_pivot.columns}
            taxes_pivot = taxes_pivot.rename(columns=tax_cols)
            result = result.merge(taxes_pivot, on='INVOICE_ID', how='left')
            logger.info(f"✓ Merge con taxes (pivotado): {len(result)} filas")
        else:
            logger.warning("⚠ No se pudo pivotear taxes")

        # ============================================================
        # PASO 6: Merge con Prepayments/ERS
        # ============================================================
        if not prepayments.empty:
            prep_cols = prepayments.columns.tolist()

            # Separar prepayments y ERS
            if 'TIPO_ORIGEN' in prep_cols:
                prep_df = prepayments[prepayments['TIPO_ORIGEN'] == 'PREPAYMENT'].copy()
                ers_df = prepayments[prepayments['TIPO_ORIGEN'] == 'ERS'].copy()
            else:
                prep_df = prepayments.copy()
                ers_df = pd.DataFrame()

            # Prepayments por INVOICE_ID (AGREGAR)
            if not prep_df.empty and 'INVOICE_ID' in prep_df.columns:
                prep_agg = prep_df.groupby('INVOICE_ID').agg({
                    'ADELANTO_USD': 'sum'
                }).reset_index()
                result = result.merge(prep_agg, on='INVOICE_ID', how='left')

            # ERS por ORDEN_COMPRA
            if not ers_df.empty and 'ORDEN_COMPRA' in result.columns and 'ORDEN_COMPRA' in ers_df.columns:
                ers_col = None
                for col in ['ERS', 'SOURCE_TRANSACTION_NUM']:
                    if col in ers_df.columns:
                        ers_col = col
                        break

                if ers_col:
                    ers_agg = ers_df.groupby('ORDEN_COMPRA').agg({
                        ers_col: lambda x: ' | '.join(x.dropna().astype(str).unique())
                    }).reset_index()
                    ers_agg = ers_agg.rename(columns={ers_col: 'ERS'})
                    result = result.merge(ers_agg, on='ORDEN_COMPRA', how='left')

            logger.info(f"✓ Merge con prepayments/ERS: {len(result)} filas")

        # ============================================================
        # PASO 7: Calcular campos derivados
        # ============================================================
        # ============================================================
        # PASO 7: Calcular campos derivados con lógica de moneda
        # ============================================================
        logger.info("🔧 Calculando campos derivados con lógica de moneda...")

        # ============================================================
        # 7.1: Identificar columna de moneda de la factura
        # ============================================================
        currency_col = None
        for col in ['MONEDA', 'INVOICE_CURRENCY_CODE', 'CURRENCY_CODE']:
            if col in result.columns:
                currency_col = col
                logger.info(f"✓ Columna de moneda encontrada: {col}")
                break

        if not currency_col:
            logger.warning("⚠ No hay columna de moneda, asumiendo todos en MXN")
            result['CURRENCY'] = 'MXN'
        else:
            result['CURRENCY'] = result[currency_col].fillna('MXN').astype(str).str.upper()

        # ============================================================
        # 7.2: Identificar tipo de cambio
        # ============================================================
        fx_candidates = ['EXCHANGE_RATE', 'TIPO_CAMBIO_FACTURA', 'TIPO_CAMBIO', 'CURRENCY_CONVERSION_RATE']
        fx_col = None
        for col in fx_candidates:
            if col in result.columns and result[col].notna().any():
                fx_col = col
                break

        if fx_col:
            result['FX_RATE'] = pd.to_numeric(result[fx_col], errors='coerce').fillna(1.0)
        else:
            result['FX_RATE'] = 1.0
            logger.warning("⚠ Sin tipo de cambio disponible, usando FX_RATE = 1.0")

        # ============================================================
        # 7.3: Función helper para convertir montos por moneda
        # ============================================================
        def calcular_montos_por_moneda(df, col_usd, col_mxn, col_original, fx_col='FX_RATE', currency_col='CURRENCY'):
            """
            Calcula montos en USD y MXN según la moneda original de la transacción.

            Regla de negocio:
            - Si moneda = 'MXN': USD = 0, MXN = valor original
            - Si moneda = 'USD': USD = valor original, MXN = USD * FX_RATE
            - Si moneda = otra: tratar como USD para consistencia
            """
            original = pd.to_numeric(df[col_original], errors='coerce').fillna(0)
            fx = pd.to_numeric(df[fx_col], errors='coerce').fillna(1.0) if fx_col in df.columns else 1.0
            currency = df[currency_col].str.upper() if currency_col in df.columns else pd.Series('MXN', index=df.index)

            # Inicializar columnas
            df[col_usd] = 0.0
            df[col_mxn] = 0.0

            # Casos por moneda
            mask_mxn = currency == 'MXN'
            mask_usd = currency == 'USD'
            mask_other = ~mask_mxn & ~mask_usd

            # MXN: USD = 0, MXN = original
            df.loc[mask_mxn, col_usd] = 0.0
            df.loc[mask_mxn, col_mxn] = original[mask_mxn]

            # USD: USD = original, MXN = original * FX
            df.loc[mask_usd, col_usd] = original[mask_usd]
            df.loc[mask_usd, col_mxn] = original[mask_usd] * fx[mask_usd]

            # Otras monedas: tratar como USD (convertir a ambas)
            df.loc[mask_other, col_usd] = original[mask_other]
            df.loc[mask_other, col_mxn] = original[mask_other] * fx[mask_other]

            return df

        # ============================================================
        # 7.4: Calcular SUBTOTAL por moneda
        # ============================================================
        if 'INVOICE_AMOUNT' in result.columns and 'TOTAL_TAX_AMOUNT' in result.columns:
            # Calcular subtotal bruto en moneda original
            result['SUBTOTAL_ORIGINAL'] = (
                    pd.to_numeric(result['INVOICE_AMOUNT'], errors='coerce').fillna(0) -
                    pd.to_numeric(result['TOTAL_TAX_AMOUNT'], errors='coerce').fillna(0)
            )

            # Aplicar lógica de moneda
            result = calcular_montos_por_moneda(
                result, 'SUBTOTAL_USD', 'SUBTOTAL_MXN', 'SUBTOTAL_ORIGINAL',
                fx_col='FX_RATE', currency_col='CURRENCY'
            )
            logger.info(
                f"✓ SUBTOTAL calculado: USD=${result['SUBTOTAL_USD'].sum():,.2f}, MXN=${result['SUBTOTAL_MXN'].sum():,.2f}")
        else:
            result['SUBTOTAL_USD'] = 0.0
            result['SUBTOTAL_MXN'] = 0.0

        # ============================================================
        # 7.5: Calcular fechas
        # ============================================================
        if 'FECHA' in result.columns:
            fecha_dt = pd.to_datetime(result['FECHA'], errors='coerce')
            result['SEMANA'] = fecha_dt.dt.isocalendar().week.astype('Int64')
            result['MES'] = fecha_dt.dt.to_period('M').astype(str)
        else:
            result['SEMANA'] = pd.NA
            result['MES'] = pd.NA

        # ============================================================
        # 7.6: Calcular fechas de pago
        # ============================================================
        if 'FECHA_APLICACION' in result.columns:
            result['FECHA_PAGO'] = result['FECHA_APLICACION']
            fecha_pago_dt = pd.to_datetime(result['FECHA_PAGO'], errors='coerce')
            result['SEMANA_PAGO'] = fecha_pago_dt.dt.isocalendar().week.astype('Int64')
            result['MES_PAGO'] = fecha_pago_dt.dt.to_period('M').astype(str)
        else:
            result['FECHA_PAGO'] = pd.NA
            result['SEMANA_PAGO'] = pd.NA
            result['MES_PAGO'] = pd.NA

        # ============================================================
        # 7.7: Calcular IMPORTE_BRUTO por moneda
        # ============================================================
        if 'IMPORTE_BRUTO_USD' in result.columns:
            # Esta columna ya viene desde Fusion como "USD" pero puede ser engañoso
            # Verificar si la factura es MXN para corregir
            original_bruto = pd.to_numeric(result['IMPORTE_BRUTO_USD'], errors='coerce').fillna(0)

            mask_mxn = result['CURRENCY'] == 'MXN'
            mask_usd = result['CURRENCY'] == 'USD'

            # Resetear columnas
            result['IMPORTE_BRUTO_USD'] = 0.0
            result['IMPORTE_MXN'] = 0.0

            # MXN: USD = 0, MXN = original
            result.loc[mask_mxn, 'IMPORTE_MXN'] = original_bruto[mask_mxn]

            # USD: USD = original, MXN = original * FX
            result.loc[mask_usd, 'IMPORTE_BRUTO_USD'] = original_bruto[mask_usd]
            result.loc[mask_usd, 'IMPORTE_MXN'] = original_bruto[mask_usd] * result['FX_RATE'][mask_usd]

            logger.info(
                f"✓ IMPORTE_BRUTO calculado: USD=${result['IMPORTE_BRUTO_USD'].sum():,.2f}, MXN=${result['IMPORTE_MXN'].sum():,.2f}")
        else:
            result['IMPORTE_BRUTO_USD'] = 0.0
            result['IMPORTE_MXN'] = 0.0

        # ============================================================
        # 7.8: Calcular SALDO por moneda (CRÍTICO)
        # ============================================================
        if 'SALDO_USD' in result.columns:
            original_saldo = pd.to_numeric(result['SALDO_USD'], errors='coerce').fillna(0)

            mask_mxn = result['CURRENCY'] == 'MXN'
            mask_usd = result['CURRENCY'] == 'USD'

            # Resetear columnas
            result['SALDO_USD'] = 0.0
            result['SALDO_MXN_CALC'] = 0.0

            # MXN: USD = 0, MXN = original
            result.loc[mask_mxn, 'SALDO_MXN_CALC'] = original_saldo[mask_mxn]

            # USD: USD = original, MXN = original * FX
            result.loc[mask_usd, 'SALDO_USD'] = original_saldo[mask_usd]
            result.loc[mask_usd, 'SALDO_MXN_CALC'] = original_saldo[mask_usd] * result['FX_RATE'][mask_usd]

            logger.info(
                f"✓ SALDO calculado: USD=${result['SALDO_USD'].sum():,.2f}, MXN=${result['SALDO_MXN_CALC'].sum():,.2f}")
        else:
            result['SALDO_USD'] = 0.0
            result['SALDO_MXN_CALC'] = 0.0

        # ============================================================
        # 7.9: Calcular ADELANTO por moneda
        # ============================================================
        if 'ADELANTO_USD' in result.columns:
            original_adelanto = pd.to_numeric(result['ADELANTO_USD'], errors='coerce').fillna(0)

            # Para adelantos, usar la moneda de la factura original
            mask_mxn = result['CURRENCY'] == 'MXN'
            mask_usd = result['CURRENCY'] == 'USD'

            result['ADELANTO_USD'] = 0.0
            result['ADELANTO_MXN'] = 0.0

            result.loc[mask_mxn, 'ADELANTO_MXN'] = original_adelanto[mask_mxn]
            result.loc[mask_usd, 'ADELANTO_USD'] = original_adelanto[mask_usd]
            result.loc[mask_usd, 'ADELANTO_MXN'] = original_adelanto[mask_usd] * result['FX_RATE'][mask_usd]
        else:
            result['ADELANTO_USD'] = 0.0
            result['ADELANTO_MXN'] = 0.0

        # ============================================================
        # 7.10: Calcular IMPORTE_DISTRIBUCION por moneda
        # ============================================================
        if 'IMPORTE_DISTRIBUCION_USD' in result.columns:
            original_dist = pd.to_numeric(result['IMPORTE_DISTRIBUCION_USD'], errors='coerce').fillna(0)

            mask_mxn = result['CURRENCY'] == 'MXN'
            mask_usd = result['CURRENCY'] == 'USD'

            result['IMPORTE_DISTRIBUCION_USD'] = 0.0
            result['IMPORTE_DISTRIBUCION_MXN'] = 0.0

            result.loc[mask_mxn, 'IMPORTE_DISTRIBUCION_MXN'] = original_dist[mask_mxn]
            result.loc[mask_usd, 'IMPORTE_DISTRIBUCION_USD'] = original_dist[mask_usd]
            result.loc[mask_usd, 'IMPORTE_DISTRIBUCION_MXN'] = original_dist[mask_usd] * result['FX_RATE'][mask_usd]
        else:
            result['IMPORTE_DISTRIBUCION_USD'] = 0.0
            result['IMPORTE_DISTRIBUCION_MXN'] = 0.0

        # ============================================================
        # 7.11: Calcular IMPORTE_PAGO por moneda (lógica especial)
        # ============================================================
        if 'IMPORTE_PAGO_USD' in result.columns:
            original_pago = pd.to_numeric(result['IMPORTE_PAGO_USD'], errors='coerce').fillna(0)

            # Los pagos pueden tener su propia moneda (TIPO_CAMBIO_PAGO)
            # Verificar si existe columna de moneda de pago
            payment_currency_col = None
            for col in ['MONEDA_PAGO', 'PAYMENT_CURRENCY_CODE', 'CURRENCY_CODE_PAY']:
                if col in result.columns:
                    payment_currency_col = col
                    break

            if payment_currency_col:
                payment_currency = result[payment_currency_col].fillna('MXN').astype(str).str.upper()
            else:
                # Si no hay moneda de pago, usar la moneda de la factura
                payment_currency = result['CURRENCY']

            # Tipo de cambio del pago (puede ser diferente al de la factura)
            if 'TIPO_CAMBIO_PAGO' in result.columns:
                payment_fx = pd.to_numeric(result['TIPO_CAMBIO_PAGO'], errors='coerce').fillna(result['FX_RATE'])
            else:
                payment_fx = result['FX_RATE']

            mask_payment_mxn = payment_currency == 'MXN'
            mask_payment_usd = payment_currency == 'USD'

            result['IMPORTE_PAGO_USD'] = 0.0
            result['IMPORTE_PAGO_MXN'] = 0.0

            result.loc[mask_payment_mxn, 'IMPORTE_PAGO_MXN'] = original_pago[mask_payment_mxn]
            result.loc[mask_payment_usd, 'IMPORTE_PAGO_USD'] = original_pago[mask_payment_usd]
            result.loc[mask_payment_usd, 'IMPORTE_PAGO_MXN'] = original_pago[mask_payment_usd] * payment_fx[
                mask_payment_usd]

            logger.info(
                f"✓ IMPORTE_PAGO calculado: USD=${result['IMPORTE_PAGO_USD'].sum():,.2f}, MXN=${result['IMPORTE_PAGO_MXN'].sum():,.2f}")
        else:
            result['IMPORTE_PAGO_USD'] = 0.0
            result['IMPORTE_PAGO_MXN'] = 0.0

        logger.info("✓ Campos derivados calculados con lógica de moneda")

        # ============================================================
        # PASO 7.12: Mapeo de ESTATUS (Antes de columnas finales)
        # ============================================================
        logger.info("🔧 Mapeando campo ESTATUS...")

        if 'ESTATUS' in result.columns:
            def mapear_estatus(valor):
                if pd.isna(valor):
                    return 'NO VALIDADO'
                valor_upper = str(valor).upper().strip()
                if valor_upper == 'NEVER APPROVED':
                    return 'NO VALIDADO'
                elif valor_upper == 'CANCELLED':
                    return 'CANCELADO'
                else:
                    return 'VALIDADO'

            result['ESTATUS'] = result['ESTATUS'].apply(mapear_estatus)

            # Contar distribución de estatus
            estatus_counts = result['ESTATUS'].value_counts()
            logger.info(f"✓ ESTATUS mapeado: {dict(estatus_counts)}")
        else:
            logger.warning("⚠ Columna ESTATUS no encontrada")

        # ============================================================
        # PASO 8: Columnas finales
        # ============================================================
        final_columns = [
            'EMPRESA', 'NUM_PROV', 'PROVEEDOR', 'RFC', 'FACTURA', 'ERS',
            'CUENTA_CONTABLE_GASTO', 'CC_DEPARTAMENTO', 'TIPO', 'UUID',
            'FECHA', 'SEMANA', 'MES', 'MONEDA', 'FECHA_PAGO', 'SEMANA_PAGO',
            'MES_PAGO', 'NUM_PAGO', 'DESCRIPTION', 'BANCO_CUENTA',
            'FECHA_APLICACION', 'ADELANTO_USD', 'ADELANTO_MXN',
            'IMPORTE_PAGO_USD', 'IMPORTE_PAGO_MXN', 'SUBTOTAL_USD', 'SUBTOTAL_MXN',
            'IVA_MXN', 'RETENCION_IVA_MXN', 'RETENCION_ISR_MXN', 'RETENCION_ISR_4_MXN',
            'IMPORTE_BRUTO_USD', 'IMPORTE_MXN', 'SALDO_USD', 'SALDO_MXN_CALC',
            'TIPO_CAMBIO_FACTURA', 'TIPO_CAMBIO_PAGO', 'ORIGEN', 'ESTATUS'
        ]

        available = [c for c in final_columns if c in result.columns]
        missing = [c for c in final_columns if c not in result.columns]

        for col in missing:
            result[col] = np.nan
            logger.warning(f"⚠ Columna no encontrada (se creó como NaN): {col}")

        result = result[final_columns].copy()

        logger.info(f"✅ Reporte final: {len(result)} filas x {len(result.columns)} columnas")
        return result

    def export_report(self, df: pd.DataFrame, filename: str = None) -> str:
        """Exporta a Excel"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'AuditMasterReport_{timestamp}.xlsx'

        output_path = self.output_folder / filename

        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Auditoría', index=False)

                # Metadatos
                metadata = pd.DataFrame({
                    'Campo': df.columns.tolist(),
                    'Tipo_Dato': df.dtypes.astype(str).tolist(),
                    'Registros_Nulos': df.isnull().sum().tolist(),
                    'Valores_Únicos': [df[c].nunique(dropna=False) for c in df.columns]
                })
                metadata.to_excel(writer, sheet_name='Metadatos', index=False)

                # Resumen
                summary = pd.DataFrame({
                    'Métrica': [
                        'Total Facturas', 'Total Proveedores', 'Monto Total USD',
                        'Monto Total MXN', 'Facturas con Pago', 'Facturas Pendientes',
                        'Fecha Proceso', 'Rango de Fechas'
                    ],
                    'Valor': [
                        len(df),
                        df['PROVEEDOR'].nunique(),
                        f"${df['IMPORTE_BRUTO_USD'].sum():,.2f}",
                        f"${df['IMPORTE_MXN'].sum():,.2f}",
                        df['NUM_PAGO'].notna().sum(),
                        (df['SALDO_USD'] > 0).sum(),
                        datetime.now().strftime('%Y-%m-%d %H:%M'),
                        f"{df['FECHA'].min()} a {df['FECHA'].max()}" if 'FECHA' in df and df[
                            'FECHA'].notna().any() else 'N/A'
                    ]
                })
                summary.to_excel(writer, sheet_name='Resumen', index=False)

            logger.info(f"📁 Reporte exportado: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"❌ Error exportando reporte: {e}")
            raise


def main():
    """Función principal"""
    try:
        merger = AuditMasterMerger(
            csv_folder='./archivos_csv',
            output_folder='./output'
        )
        df_final = merger.merge_all()

        if df_final.empty:
            logger.error("❌ No se generaron datos para el reporte")
            sys.exit(1)

        output_file = merger.export_report(df_final)
        print(f"\n✅ ¡Proceso completado!\n📄 Reporte: {output_file}")

    except Exception as e:
        logger.exception("❌ Error crítico en el proceso")
        sys.exit(1)


if __name__ == '__main__':
    main()