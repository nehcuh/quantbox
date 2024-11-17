"""
Data validation module for the Remote Data Fetcher
远程数据获取器数据验证模块
"""

import logging
from typing import Dict, List, Any, Optional, Set
import pandas as pd
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of data validation"""
    is_valid: bool
    missing_fields: Set[str]
    invalid_records: List[Dict[str, Any]]
    error_messages: List[str]

class DataValidator:
    """Data validator for fetched data"""

    def __init__(
        self,
        required_fields: Dict[str, List[str]],
        allow_missing: bool = False,
        validate_types: bool = True
    ):
        self.required_fields = required_fields
        self.allow_missing = allow_missing
        self.validate_types = validate_types

    def validate_dataframe(
        self,
        df: pd.DataFrame,
        data_type: str
    ) -> ValidationResult:
        """
        Validate a pandas DataFrame against defined requirements
        验证pandas DataFrame是否符合定义的要求

        Args:
            df: DataFrame to validate
            data_type: Type of data (e.g., 'trade_dates', 'holdings')

        Returns:
            ValidationResult object containing validation results
        """
        if data_type not in self.required_fields:
            return ValidationResult(
                is_valid=True,
                missing_fields=set(),
                invalid_records=[],
                error_messages=[f"No validation rules defined for {data_type}"]
            )

        required = set(self.required_fields[data_type])
        missing_fields = required - set(df.columns)
        invalid_records = []
        error_messages = []

        # Check required fields
        if missing_fields and not self.allow_missing:
            error_messages.append(
                f"Missing required fields: {', '.join(missing_fields)}"
            )
            return ValidationResult(
                is_valid=False,
                missing_fields=missing_fields,
                invalid_records=[],
                error_messages=error_messages
            )

        # Check for null values in required fields
        present_required = required - missing_fields
        null_counts = df[list(present_required)].isnull().sum()
        fields_with_nulls = null_counts[null_counts > 0]
        if not fields_with_nulls.empty:
            for field, count in fields_with_nulls.items():
                error_messages.append(
                    f"Field '{field}' contains {count} null values"
                )

        # Validate data types
        if self.validate_types:
            invalid_records.extend(self._validate_types(df, data_type))

        # Validate specific data types
        if data_type == 'trade_dates':
            invalid_records.extend(self._validate_trade_dates(df))
        elif data_type == 'future_daily':
            invalid_records.extend(self._validate_future_daily(df))

        is_valid = (
            len(missing_fields) == 0 and
            len(invalid_records) == 0 and
            len(error_messages) == 0
        )

        return ValidationResult(
            is_valid=is_valid,
            missing_fields=missing_fields,
            invalid_records=invalid_records,
            error_messages=error_messages
        )

    def _validate_types(
        self,
        df: pd.DataFrame,
        data_type: str
    ) -> List[Dict[str, Any]]:
        """Validate data types of fields"""
        invalid_records = []
        
        # Define expected types for different fields
        type_rules = {
            'date': (np.datetime64, pd.Timestamp),
            'symbol': str,
            'exchange': str,
            'open': (float, np.float64),
            'high': (float, np.float64),
            'low': (float, np.float64),
            'close': (float, np.float64),
            'volume': (int, np.int64),
            'amount': (float, np.float64)
        }

        for field in df.columns:
            if field in type_rules:
                expected_type = type_rules[field]
                mask = ~df[field].apply(
                    lambda x: isinstance(x, expected_type)
                )
                if mask.any():
                    invalid_records.extend(
                        df[mask].to_dict('records')
                    )

        return invalid_records

    def _validate_trade_dates(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Validate trade dates data"""
        invalid_records = []
        
        if 'date' in df.columns:
            # Check date format and validity
            try:
                pd.to_datetime(df['date'])
            except Exception as e:
                invalid_records.extend(
                    df[~pd.to_datetime(df['date'], errors='coerce')
                    .notna()].to_dict('records')
                )

        return invalid_records

    def _validate_future_daily(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Validate future daily data"""
        invalid_records = []
        
        # Check price relationships
        if all(field in df.columns for field in ['open', 'high', 'low', 'close']):
            # High should be >= Low
            invalid_high_low = df['high'] < df['low']
            if invalid_high_low.any():
                invalid_records.extend(
                    df[invalid_high_low].to_dict('records')
                )

            # High should be >= Open and Close
            invalid_high = (df['high'] < df['open']) | (df['high'] < df['close'])
            if invalid_high.any():
                invalid_records.extend(
                    df[invalid_high].to_dict('records')
                )

            # Low should be <= Open and Close
            invalid_low = (df['low'] > df['open']) | (df['low'] > df['close'])
            if invalid_low.any():
                invalid_records.extend(
                    df[invalid_low].to_dict('records')
                )

        # Check volume and amount
        if 'volume' in df.columns:
            invalid_volume = df['volume'] < 0
            if invalid_volume.any():
                invalid_records.extend(
                    df[invalid_volume].to_dict('records')
                )

        if 'amount' in df.columns:
            invalid_amount = df['amount'] < 0
            if invalid_amount.any():
                invalid_records.extend(
                    df[invalid_amount].to_dict('records')
                )

        return invalid_records
