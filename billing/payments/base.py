"""Payment provider contract. Concrete providers implement create_invoice()."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Invoice:
    """The provider's response to a create-invoice request."""
    pay_url: str          # where the user goes to pay
    provider_ref: str     # provider-side id (used to look up the payment on callback)
    raw: dict             # full provider payload (audit)


class PaymentProvider(ABC):
    name = "base"

    @abstractmethod
    def create_invoice(self, payment) -> Invoice:
        """Create a payment invoice. `payment` is a Payment instance (not yet paid)."""
