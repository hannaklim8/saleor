import datetime

import pytest
from django.utils import timezone

from .....checkout.error_codes import CheckoutErrorCode
from ....core.utils import to_global_id_or_none
from ....tests.utils import get_graphql_content

CHECKOUT_DESIRED_DELIVERY_DATE_UPDATE_MUTATION = """
    mutation checkoutDesiredDeliveryDateUpdate($id: ID!, $desiredDeliveryDate: Date) {
        checkoutDesiredDeliveryDateUpdate(
            id: $id, desiredDeliveryDate: $desiredDeliveryDate
        ) {
            checkout {
                id
                desiredDeliveryDate
            }
            errors {
                field
                message
                code
            }
        }
    }
"""


def test_checkout_desired_delivery_date_update_valid_date(
    user_api_client, checkout_with_item
):
    # given
    checkout = checkout_with_item
    previous_last_change = checkout.last_change
    desired_delivery_date = timezone.now().date() + datetime.timedelta(days=5)
    variables = {
        "id": to_global_id_or_none(checkout),
        "desiredDeliveryDate": desired_delivery_date.isoformat(),
    }

    # when
    response = user_api_client.post_graphql(
        CHECKOUT_DESIRED_DELIVERY_DATE_UPDATE_MUTATION, variables
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["checkoutDesiredDeliveryDateUpdate"]
    assert len(data["errors"]) == 0
    checkout.refresh_from_db()
    assert checkout.desired_delivery_date == desired_delivery_date
    assert data["checkout"]["desiredDeliveryDate"] == desired_delivery_date.isoformat()
    assert checkout.last_change != previous_last_change


@pytest.mark.parametrize(
    ("_case", "days_from_today"),
    [
        ("tomorrow", 1),
        ("thirty_days_from_now", 30),
    ],
)
def test_checkout_desired_delivery_date_update_boundary_dates(
    _case, days_from_today, user_api_client, checkout_with_item
):
    # given
    checkout = checkout_with_item
    desired_delivery_date = timezone.now().date() + datetime.timedelta(
        days=days_from_today
    )
    variables = {
        "id": to_global_id_or_none(checkout),
        "desiredDeliveryDate": desired_delivery_date.isoformat(),
    }

    # when
    response = user_api_client.post_graphql(
        CHECKOUT_DESIRED_DELIVERY_DATE_UPDATE_MUTATION, variables
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["checkoutDesiredDeliveryDateUpdate"]
    assert len(data["errors"]) == 0
    checkout.refresh_from_db()
    assert checkout.desired_delivery_date == desired_delivery_date


@pytest.mark.parametrize(
    ("_case", "days_from_today"),
    [
        ("today", 0),
        ("yesterday", -1),
        ("thirty_one_days_from_now", 31),
    ],
)
def test_checkout_desired_delivery_date_update_out_of_range(
    _case, days_from_today, user_api_client, checkout_with_item
):
    # given
    checkout = checkout_with_item
    checkout.desired_delivery_date = None
    checkout.save(update_fields=["desired_delivery_date"])
    assert checkout.desired_delivery_date is None
    invalid_date = timezone.now().date() + datetime.timedelta(days=days_from_today)
    variables = {
        "id": to_global_id_or_none(checkout),
        "desiredDeliveryDate": invalid_date.isoformat(),
    }

    # when
    response = user_api_client.post_graphql(
        CHECKOUT_DESIRED_DELIVERY_DATE_UPDATE_MUTATION, variables
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["checkoutDesiredDeliveryDateUpdate"]
    assert len(data["errors"]) == 1
    assert data["errors"][0]["field"] == "desiredDeliveryDate"
    assert (
        data["errors"][0]["code"]
        == CheckoutErrorCode.DESIRED_DELIVERY_DATE_OUT_OF_RANGE.name
    )
    assert not data["checkout"]
    checkout.refresh_from_db()
    assert checkout.desired_delivery_date is None


def test_checkout_desired_delivery_date_update_clear_with_null(
    user_api_client, checkout_with_item
):
    # given
    checkout = checkout_with_item
    previous_desired_delivery_date = timezone.now().date() + datetime.timedelta(
        days=5
    )
    checkout.desired_delivery_date = previous_desired_delivery_date
    checkout.save(update_fields=["desired_delivery_date"])
    assert checkout.desired_delivery_date == previous_desired_delivery_date
    variables = {
        "id": to_global_id_or_none(checkout),
        "desiredDeliveryDate": None,
    }

    # when
    response = user_api_client.post_graphql(
        CHECKOUT_DESIRED_DELIVERY_DATE_UPDATE_MUTATION, variables
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["checkoutDesiredDeliveryDateUpdate"]
    assert len(data["errors"]) == 0
    checkout.refresh_from_db()
    assert checkout.desired_delivery_date is None
    assert data["checkout"]["desiredDeliveryDate"] is None


def test_checkout_desired_delivery_date_update_overwrites_previous_value(
    user_api_client, checkout_with_item
):
    # given
    checkout = checkout_with_item
    previous_desired_delivery_date = timezone.now().date() + datetime.timedelta(
        days=3
    )
    checkout.desired_delivery_date = previous_desired_delivery_date
    checkout.save(update_fields=["desired_delivery_date"])
    assert checkout.desired_delivery_date == previous_desired_delivery_date
    new_desired_delivery_date = timezone.now().date() + datetime.timedelta(days=10)
    variables = {
        "id": to_global_id_or_none(checkout),
        "desiredDeliveryDate": new_desired_delivery_date.isoformat(),
    }

    # when
    response = user_api_client.post_graphql(
        CHECKOUT_DESIRED_DELIVERY_DATE_UPDATE_MUTATION, variables
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["checkoutDesiredDeliveryDateUpdate"]
    assert len(data["errors"]) == 0
    checkout.refresh_from_db()
    assert checkout.desired_delivery_date == new_desired_delivery_date
    assert (
        data["checkout"]["desiredDeliveryDate"]
        == new_desired_delivery_date.isoformat()
    )


def test_checkout_desired_delivery_date_update_omitted_field_clears_existing_value(
    user_api_client, checkout_with_item
):
    """Omitting the argument behaves like passing `null`.

    This is a single-purpose mutation with nothing else to update, so there is
    no "leave unchanged" case to distinguish from clearing the value.
    """
    # given
    checkout = checkout_with_item
    previous_desired_delivery_date = timezone.now().date() + datetime.timedelta(
        days=5
    )
    checkout.desired_delivery_date = previous_desired_delivery_date
    checkout.save(update_fields=["desired_delivery_date"])
    assert checkout.desired_delivery_date == previous_desired_delivery_date
    query = """
        mutation checkoutDesiredDeliveryDateUpdate($id: ID!) {
            checkoutDesiredDeliveryDateUpdate(id: $id) {
                checkout {
                    id
                    desiredDeliveryDate
                }
                errors {
                    field
                    message
                    code
                }
            }
        }
    """
    variables = {"id": to_global_id_or_none(checkout)}

    # when
    response = user_api_client.post_graphql(query, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["checkoutDesiredDeliveryDateUpdate"]
    assert len(data["errors"]) == 0
    checkout.refresh_from_db()
    assert checkout.desired_delivery_date is None
    assert data["checkout"]["desiredDeliveryDate"] is None


@pytest.mark.parametrize(
    ("_case", "client_fixture"),
    [
        ("Unauthenticated user is allowed", "api_client"),
        ("Authenticated unprivileged user (non-staff) is allowed", "user_api_client"),
        ("Staff user without any permission is allowed", "staff_api_client"),
    ],
)
def test_checkout_desired_delivery_date_update_requires_no_authorization(
    request, _case, client_fixture, checkout_with_item
):
    """The mutation is public, like other single-field checkout update mutations."""
    # given
    client = request.getfixturevalue(client_fixture)
    checkout = checkout_with_item
    desired_delivery_date = timezone.now().date() + datetime.timedelta(days=5)
    variables = {
        "id": to_global_id_or_none(checkout),
        "desiredDeliveryDate": desired_delivery_date.isoformat(),
    }

    # when
    response = client.post_graphql(
        CHECKOUT_DESIRED_DELIVERY_DATE_UPDATE_MUTATION, variables
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["checkoutDesiredDeliveryDateUpdate"]
    assert len(data["errors"]) == 0
    checkout.refresh_from_db()
    assert checkout.desired_delivery_date == desired_delivery_date
