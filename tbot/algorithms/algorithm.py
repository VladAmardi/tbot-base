import pickle
from lib import catch_and_print_exceptions
from tbot.models import Algorithms, Bot, Round, Order
from tbot.dto import Callback
from tbot.exchanges import Exchange


class Algorithm:  # (ABC)
    algorithm: Algorithms = None

    @staticmethod
    def get_callback(method, **kwargs) -> str:
        return pickle.dumps(Callback(
            method=method.__name__,
            params=kwargs
        ), 0).decode()

    def execute_callback(self, callback_str: str, extra_params: {} = None):
        if extra_params is None:
            extra_params = {}
        if not callback_str:
            return None
        callback = pickle.loads(callback_str.encode())
        assert isinstance(callback, Callback)
        e = getattr(self, callback.method)
        # e = callback.method
        assert callable(e)
        return e(**(callback.params | extra_params))

    @staticmethod
    def get_algorithm(bot_id: int):
        bot = Bot.objects.get(id=bot_id)
        for i in Algorithm.__subclasses__():
            if i.algorithm == bot.algorithm:
                return i(bot_id=bot_id)
        assert False

    def get_exchange(self) -> Exchange:
        return Exchange.get_exchange(
            exchange=self.bot.exchange_connection.exchange
        )(connection=self.bot.exchange_connection)

    def __init__(self, bot_id: int):
        super().__init__()
        self.bot = Bot.objects.get(id=bot_id)

    def get_last_round(self) -> Round:
        return Round.objects.filter(bot=self.bot).order_by('-id')[:1][0]

    def new_round(self):
        round = Round(bot=self.bot)
        round.save()
        return round

    def start(self):
        self.bot.status = Bot.Statuses.ON
        self.bot.save()

    @catch_and_print_exceptions(exit_after=False)
    def cancel_order(self, order: Order):
        self.get_exchange().cancel_order(order=order)

    def cancel_open_orders(self):
        from tbot.services import get_active_orders
        for order in get_active_orders(bot_id=self.bot.id):
            # TODO Decide something with this and the same prints
            print("Cancel: " + str(order))
            self.cancel_order(order=order)

    def stop(self, canceled=False):
        self.bot.status = Bot.Statuses.CANCELED if canceled else Bot.Statuses.OFF
        self.bot.save()
        self.cancel_open_orders()

    # noinspection PyMethodMayBeStatic
    def step_test(self, order: Order, **kwargs):
        print(str(order) + "[" + str(order.status) + "]")
