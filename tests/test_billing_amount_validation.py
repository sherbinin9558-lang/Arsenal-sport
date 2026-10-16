from decimal import Decimal

import pytest
from fastapi import HTTPException

import tbank_webhook


def test_yookassa_amount_and_currency_match():
    assert tbank_webhook._verify_yookassa_payment_amount(
        {"amount": {"value": "990.00", "currency": "RUB"}},
        {"expected_amount": "990.00", "expected_currency": "RUB"},
    ) is None


@pytest.mark.parametrize(
    ("payment", "checkout", "message"),
    [
        ({"amount": {"value": "9.90", "currency": "RUB"}}, {"expected_amount": "990.00", "expected_currency": "RUB"}, "amount"),
        ({"amount": {"value": "990.00", "currency": "USD"}}, {"expected_amount": "990.00", "expected_currency": "RUB"}, "currency"),
        ({"amount": {"value": "990.00", "currency": "RUB"}}, {"expected_amount": None, "expected_currency": "RUB"}, "amount"),
        ({"amount": {"value": "NaN", "currency": "RUB"}}, {"expected_amount": "990.00", "expected_currency": "RUB"}, "amount"),
    ],
)
def test_yookassa_amount_verification_fails_closed(payment, checkout, message):
    with pytest.raises(HTTPException) as exc:
        tbank_webhook._verify_yookassa_payment_amount(payment, checkout)
    assert exc.value.status_code == 422
    assert message in exc.value.detail.lower()
