from django.utils import timezone
import traceback
import sys
from datetime import datetime
from .exchanges import Exchange
from .models import ExchangeConnection, Bot, Order, Position
from .algorithms import Algorithm


def get_exchange(exchange_connection: ExchangeConnection) -> Exchange:
    return Exchange.get_exchange(exchange=exchange_connection.exchange)(connection=exchange_connection)


def get_bots_by_connection_id(exchange_connection_id):
    return Bot.objects.filter(exchange_connection_id=exchange_connection_id).all()


def get_exchange_connection(id):
    return ExchangeConnection.objects.get(id=id)


def get_active_exchange_connections():
    return ExchangeConnection.objects.filter(
        bot__round__position__in=Position.objects.filter(order__status__in=[Order.Statuses.ACTIVE, Order.Statuses.NEW])
    ).distinct()


def get_active_orders(bot_id=id):
    return Order.objects.filter(position__round__bot_id=bot_id, status=Order.Statuses.ACTIVE)


def execute_order_callback(order: Order):
    def _execute_callback(_order: Order):
        if _order.callback_status == _order.CallbackStatuses.WAITING:
            _order.callback_at = datetime.now(tz=timezone.utc)
            if _order.callback == "":
                _order.callback_status = _order.CallbackStatuses.DONE
            else:
                _order.callback_status = _order.CallbackStatuses.STARTED
                _order.save(update_fields=['callback_at', 'callback_status', 'updated_at'])
                try:
                    Algorithm.get_algorithm(
                        bot_id=int(_order.position.round.bot_id)
                    ).execute_callback(
                        callback_str=_order.callback,
                        extra_params={'order': _order}
                    )
                    _order.callback_status = _order.CallbackStatuses.DONE
                    _order.save(update_fields=['callback_status', 'updated_at'])
                except BaseException as e:
                    # TODO Should it be printed here? How to mark it for routing in logs?
                    print(e, file=sys.stderr)
                    traceback.print_exc(file=sys.stderr)
                    _order.callback_status = _order.CallbackStatuses.ERROR
                    _order.save(update_fields=['callback_status', 'updated_at'])

    if order.oco_order is not None:
        if order.oco_order.status == order.Statuses.ACTIVE:
            # Skip both
            pass
        else:
            # Call
            if order.oco_order.status == order.Statuses.ACTIVE:
                order_active = order
                order_pass = order.oco_order
            else:
                order_active = order.oco_order
                order_pass = order

            order_pass.callback_status = order.CallbackStatuses.OCO_CANCELED
            order_pass.save()

            _execute_callback(_order=order_active)
    else:
        _execute_callback(_order=order)
