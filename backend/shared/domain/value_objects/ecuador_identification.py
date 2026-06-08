from __future__ import annotations

"""Shared validators for Ecuadorian civil and tax identifiers."""


def is_valid_province_code(value: str) -> bool:
    if not value.isdigit() or len(value) != 2:
        return False
    province = int(value)
    return 1 <= province <= 24


def modulo10(base: str, check_digit: str) -> bool:
    if not base.isdigit() or not check_digit.isdigit() or len(base) != 9:
        return False
    coef = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    total = sum((v - 9 if v >= 10 else v) for v in (int(base[i]) * coef[i] for i in range(9)))
    expected = 0 if total % 10 == 0 else 10 - total % 10
    return expected == int(check_digit)


def modulo11_public(base: str, check_digit: str) -> bool:
    if not base.isdigit() or not check_digit.isdigit() or len(base) != 8:
        return False
    coef = [3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(int(base[i]) * coef[i] for i in range(8))
    remainder = total % 11
    expected = 0 if remainder == 0 else 11 - remainder
    return expected == int(check_digit)


def modulo11_legal(base: str, check_digit: str) -> bool:
    if not base.isdigit() or not check_digit.isdigit() or len(base) != 9:
        return False
    coef = [4, 3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(int(base[i]) * coef[i] for i in range(9))
    remainder = total % 11
    expected = 0 if remainder == 0 else 11 - remainder
    return expected == int(check_digit)


def is_valid_cedula(value: str) -> bool:
    value = (value or "").strip()
    if not value.isdigit() or len(value) != 10:
        return False
    if not is_valid_province_code(value[:2]):
        return False
    if int(value[2]) >= 6:
        return False
    return modulo10(value[:9], value[9])


def is_valid_ruc(value: str) -> bool:
    value = (value or "").strip()
    if not value.isdigit() or len(value) != 13:
        return False
    if not is_valid_province_code(value[:2]):
        return False

    third_digit = int(value[2])
    if third_digit < 6:
        return is_valid_cedula(value[:10]) and value[10:] == "001"
    if third_digit == 6:
        return modulo11_public(value[:8], value[8]) and value[9:] == "0001"
    if third_digit == 9:
        return modulo11_legal(value[:9], value[9]) and value[10:] == "001"
    return False
