from decimal import Decimal
from fastapi import HTTPException

import tbank_webhook


def test_tbank_amount_matches_expected_rub_checkout():
    tbank_webhook._verify_tbank_payment_amount(
        {"Amount": 99000},
        {"expected_amount": "990.00", "expected_currency": "RUB"},
    )


def test_tbank_wrong_amount_is_rejected():
    try:
        tbank_webhook._verify_tbank_payment_amount(
            {"Amount": 990},
            {"expected_amount": "990.00", "expected_currency": "RUB"},
        )
    except HTTPException as exc:
        assert exc.status_code == 422
        assert exc.detail == "Checkout amount verification failed"
    else:
        raise AssertionError("mismatched amount was accepted")


def test_tbank_wrong_currency_is_rejected():
    try:
        tbank_webhook._verify_tbank_payment_amount(
            {"Amount": 99000},
            {"expected_amount": "990.00", "expected_currency": "USD"},
        )
    except HTTPException as exc:
        assert exc.status_code == 422
        assert exc.detail == "Checkout currency verification failed"
    else:
        raise AssertionError("wrong currency was accepted")


def test_tbank_missing_expected_amount_fails_closed():
    try:
        tbank_webhook._verify_tbank_payment_amount(
            {"Amount": 99000},
            {"expected_amount": None, "expected_currency": "RUB"},
        )
    except HTTPException as exc:
        assert exc.status_code == 422
    else:
        raise AssertionError("missing expected amount was accepted")
