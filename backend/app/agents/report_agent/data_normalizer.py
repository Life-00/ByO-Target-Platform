"""
Data Normalizer
Data normalization and unit conversion utilities
"""

import logging
from typing import Dict, Any, List

import pandas as pd
import pint

logger = logging.getLogger(__name__)


class DataNormalizer:
    """데이터 정규화 및 단위 변환 도구"""

    # pint 단위 레지스트리
    ureg = pint.UnitRegistry()
    ureg.define("dalton = atomic_mass_unit")

    @staticmethod
    async def normalize_units(
        data: Dict[str, Any],
        from_unit: str,
        to_unit: str
    ) -> Dict[str, Any]:
        """
        데이터 단위 변환

        Args:
            data: 변환할 데이터 {"value": 100, "unit": "kg"}
            from_unit: 원본 단위 (예: "kg")
            to_unit: 목표 단위 (예: "g")

        Returns:
            변환된 데이터 {"value": 100000, "unit": "g"}
        """
        try:
            if "value" not in data:
                raise ValueError("Data must contain 'value' key")

            value = data["value"]
            original_unit = from_unit or data.get("unit", "")

            if not original_unit:
                raise ValueError("Unit must be specified")

            # pint로 변환
            quantity = value * DataNormalizer.ureg(original_unit)
            converted = quantity.to(to_unit)

            result = {
                "original_value": value,
                "original_unit": original_unit,
                "converted_value": float(converted.magnitude),
                "converted_unit": str(converted.units),
                "conversion_successful": True
            }

            logger.info(f"[DataNormalizer] Converted: {value}{original_unit} → {converted}")
            return result

        except pint.errors.DimensionalityError as e:
            logger.warning(f"[DataNormalizer] Unit mismatch: {str(e)}")
            return {
                "original_value": value,
                "original_unit": original_unit,
                "error": f"Cannot convert {original_unit} to {to_unit}",
                "conversion_successful": False
            }

        except Exception as e:
            logger.error(f"[DataNormalizer] Error normalizing units: {str(e)}")
            raise

    @staticmethod
    async def standardize_table(df: pd.DataFrame) -> pd.DataFrame:
        """
        표 데이터 정규화

        Args:
            df: Pandas DataFrame

        Returns:
            정규화된 DataFrame
        """
        try:
            # 1. 컬럼명 정규화 (공백 제거, 소문자)
            df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

            # 2. 결측값 처리
            df = df.dropna(how='all')  # 완전 빈 행 제거

            # 3. 데이터 타입 추론
            for col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col], errors='ignore')
                except:
                    pass

            # 4. 중복 제거
            df = df.drop_duplicates()

            logger.info(f"[DataNormalizer] Standardized table: {df.shape[0]} rows, {df.shape[1]} cols")
            return df

        except Exception as e:
            logger.error(f"[DataNormalizer] Error standardizing table: {str(e)}")
            raise

    @staticmethod
    async def handle_unit_mismatch(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        변환 불가능한 단위 처리

        Args:
            data: 변환할 데이터

        Returns:
            처리 결과
        """
        try:
            value = data.get("value")
            from_unit = data.get("from_unit")
            to_unit = data.get("to_unit")

            logger.warning(
                f"[DataNormalizer] Unit mismatch: {value}{from_unit} → {to_unit}. "
                f"Attempting alternative conversion..."
            )

            # 일반적인 단위 변환 규칙
            conversion_rules = {
                ("celsius", "kelvin"): lambda v: v + 273.15,
                ("fahrenheit", "celsius"): lambda v: (v - 32) * 5 / 9,
                ("kg", "lbs"): lambda v: v * 2.20462,
                ("m", "ft"): lambda v: v * 3.28084,
                ("l", "gallon"): lambda v: v * 0.264172,
            }

            key = (from_unit.lower(), to_unit.lower())
            if key in conversion_rules:
                converted_value = conversion_rules[key](value)
                return {
                    "success": True,
                    "original_value": value,
                    "converted_value": converted_value,
                    "from_unit": from_unit,
                    "to_unit": to_unit,
                    "method": "custom_rule"
                }

            return {
                "success": False,
                "error": f"No conversion rule for {from_unit} → {to_unit}",
                "original_value": value
            }

        except Exception as e:
            logger.error(f"[DataNormalizer] Error handling unit mismatch: {str(e)}")
            raise

    @staticmethod
    async def merge_tables(tables: List[pd.DataFrame]) -> pd.DataFrame:
        """
        여러 표를 병합

        Args:
            tables: DataFrame 리스트

        Returns:
            병합된 DataFrame
        """
        try:
            if not tables:
                return pd.DataFrame()

            merged = tables[0]
            for table in tables[1:]:
                # 공통 컬럼으로 merge (또는 concat)
                common_cols = set(merged.columns) & set(table.columns)
                if common_cols:
                    merged = pd.merge(merged, table, on=list(common_cols), how="outer")
                else:
                    merged = pd.concat([merged, table], axis=0, ignore_index=True)

            logger.info(f"[DataNormalizer] Merged {len(tables)} tables")
            return merged

        except Exception as e:
            logger.error(f"[DataNormalizer] Error merging tables: {str(e)}")
            raise
