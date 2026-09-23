import graphene
from django.core.exceptions import ValidationError

from ....checkout.actions import call_checkout_event
from ....checkout.error_codes import CheckoutErrorCode
from ....checkout.utils import is_desired_delivery_date_valid
from ....webhook.event_types import WebhookEventAsyncType
from ...core import ResolveInfo
from ...core.context import SyncWebhookControlContext
from ...core.descriptions import ADDED_IN_324
from ...core.doc_category import DOC_CATEGORY_CHECKOUT
from ...core.mutations import BaseMutation
from ...core.scalars import Date
from ...core.types import CheckoutError
from ...core.utils import WebhookEventInfo
from ...plugins.dataloaders import get_plugin_manager_promise
from ..types import Checkout


class CheckoutDesiredDeliveryDateUpdate(BaseMutation):
    checkout = graphene.Field(Checkout, description="An updated checkout.")

    class Arguments:
        id = graphene.ID(
            description="The checkout's ID.",
            required=True,
        )
        desired_delivery_date = Date(
            description=(
                "The desired delivery date. Must be a date between tomorrow "
                "and 30 days from now, calculated in UTC. Pass `null` to "
                "clear a previously set date." + ADDED_IN_324
            ),
            required=False,
        )

    class Meta:
        description = (
            "Updates the desired delivery date of the checkout." + ADDED_IN_324
        )
        doc_category = DOC_CATEGORY_CHECKOUT
        error_type_class = CheckoutError
        error_type_field = "checkout_errors"
        webhook_events_info = [
            WebhookEventInfo(
                type=WebhookEventAsyncType.CHECKOUT_UPDATED,
                description="A checkout was updated.",
            )
        ]

    @classmethod
    def clean_desired_delivery_date(cls, desired_delivery_date):
        if desired_delivery_date is None:
            return
        if not is_desired_delivery_date_valid(desired_delivery_date):
            raise ValidationError(
                {
                    "desired_delivery_date": ValidationError(
                        "Desired delivery date must be between tomorrow and "
                        "30 days from now (calculated in UTC).",
                        code=(
                            CheckoutErrorCode.DESIRED_DELIVERY_DATE_OUT_OF_RANGE.value
                        ),
                    )
                }
            )

    @classmethod
    def perform_mutation(  # type: ignore[override]
        cls,
        _root,
        info: ResolveInfo,
        /,
        *,
        id=None,
        desired_delivery_date=None,
    ):
        checkout = cls.get_node_or_error(info, id, only_type=Checkout)
        cls.clean_desired_delivery_date(desired_delivery_date)
        checkout.desired_delivery_date = desired_delivery_date
        cls.clean_instance(info, checkout)
        checkout.save(update_fields=["desired_delivery_date", "last_change"])
        manager = get_plugin_manager_promise(info.context).get()
        call_checkout_event(
            manager,
            event_name=WebhookEventAsyncType.CHECKOUT_UPDATED,
            checkout=checkout,
        )
        return CheckoutDesiredDeliveryDateUpdate(
            checkout=SyncWebhookControlContext(node=checkout)
        )
