from __future__ import annotations
from .algorithm import Algorithm
from tbot.models import Algorithms, SettingType, Position, Order, Bot
from django.db.models import Sum, F


class DCA1(Algorithm):
    algorithm = Algorithms.DCA1

    def start(self):
        super().start()

    @staticmethod
    def disable_on_cancel(func):
        def decorated(self: DCA1, order: Order, **kwargs):
            if order.status == order.Statuses.CANCELED:
                if order.oco_order is None or order.oco_order.status == order.Statuses.CANCELED:
                    print("Canceling bot, because order " + str(order.id))
                    return self.stop(canceled=True)
            return func(self=self, order=order, **kwargs)

        # Should be here for callback serializer, look Algorithm.get_callback definition
        decorated.__name__ = func.__name__

        return decorated
