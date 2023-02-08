from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from db.fields import EnumField


class ExchangesNames(models.TextChoices):
    BINANCE = 'BINANCE'
    BINANCETEST = 'BINANCETEST'
    FAKE = 'FAKE'


class SettingType(models.TextChoices):
    PERCENT = 'PERCENT'
    ABSOLUTE = 'ABSOLUTE'


class Algorithms(models.TextChoices):
    DCA1 = 'DCA1'
    DCA2 = 'DCA2'


class Symbol(models.Model):
    exchange = EnumField(choices=ExchangesNames.choices, default=ExchangesNames.BINANCE)

    # For example, BTC
    base_asset = models.CharField(max_length=16)

    # For example, USDT
    quote_asset = models.CharField(max_length=16)

    # For example, BTCUSDT
    symbol = models.CharField(max_length=32)

    # Minimum order size expressed in quote_asset
    # https://binance-docs.github.io/apidocs/spot/en/#filters
    # MIN_NOTIONAL
    min_notional = models.FloatField(null=True, blank=True, default=None)

    # Minimum and maximum prices for order
    # https://binance-docs.github.io/apidocs/spot/en/#filters
    # PRICE_FILTER
    min_price = models.FloatField(null=True, blank=True, default=None)
    max_price = models.FloatField(null=True, blank=True, default=None)

    # defines the intervals that a price/stopPrice can be increased/decreased by; disabled on tickSize == 0
    # https://binance-docs.github.io/apidocs/spot/en/#filters
    # PRICE_FILTER
    tick_size = models.FloatField(null=True, blank=True, default=None)

    # Defines the intervals that a quantity/icebergQty can be increased/decreased by.
    # https://binance-docs.github.io/apidocs/spot/en/#filters
    # LOT_SIZE
    step_size = models.FloatField(null=True, blank=True, default=None)

    # defines the minimum quantity/icebergQty allowed
    # https://binance-docs.github.io/apidocs/spot/en/#filters
    # LOT_SIZE
    min_qty = models.FloatField(null=True, blank=True, default=None)

    # Current price of Base_asset, expressed in quote_asset
    price = models.FloatField(null=True, blank=True, default=None)

    # True if symbol matches the following parameters:
    # - Symbol_status = TRADING. Can also take values LISTED/DELISTED/HOLD/etc.
    # - ocoAllowed = true
    # - isSpotTradingAllowed = true
    enabled = models.BooleanField(null=True, blank=True, default=None)

    multiplier_up = models.FloatField(null=True, blank=True, default=None)
    multiplier_down = models.FloatField(null=True, blank=True, default=None)
    multiplier_avg_price_minutes = models.FloatField(null=True, blank=True, default=None)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['exchange', 'base_asset', 'quote_asset'],
                name='exchange_and_base_and_quote_assets'
            ),
            models.UniqueConstraint(
                fields=['exchange', 'symbol'],
                name='exchange_and_symbol'
            )
        ]


# https://simpleisbetterthancomplex.com/tutorial/2016/07/22/how-to-extend-django-user-model.html
# users = User.objects.all().select_related('profile')
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # System setting.
    # In the future, set for the user, now (temporary) is set 0.1% of the price.
    # tick_size <= Min_step
    min_step = models.FloatField(default=0.001)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


class ExchangeConnection(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    exchange = EnumField(choices=ExchangesNames.choices, default=ExchangesNames.BINANCE)
    API_key = models.TextField()
    API_secret = models.TextField()
    commission = models.FloatField(default=0.001)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['owner', 'exchange'], name='owner_and_exchange')
        ]


class Bot(models.Model):
    # User, own the bot instance
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    exchange_connection = models.ForeignKey(ExchangeConnection, on_delete=models.CASCADE)

    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE)

    # The limit value of the price up to which the grid of orders is calculated, as well as the risk.
    # When this value is reached, all positions of the round are closed in the red.
    # Specified as (1) a percentage of the current price or as (2) the absolute value of the price.
    # Having reached this price, the loss must be within the risk_target.
    price_limit_type = EnumField(choices=SettingType.choices, default=SettingType.PERCENT)
    price_limit = models.FloatField(null=True, blank=True, default=None)

    # First order size (lot_multiplier can be enabled for subsequent orders) - setting,
    # can be set, can be expected automatically.
    # Lot >= min_notional && Lot <= balance_allowance
    # Expressed in quote asset
    lot = models.FloatField(null=True, blank=True, default=None)

    # Setting, coefficient by which each subsequent lot size is multiplied in descending series.
    lot_multiplier_down = models.FloatField(default=1)

    # Price step (absolute value) between the first and subsequent orders in ascending series,
    # can be set by the user, can be calculated automatically if not set.
    # User.Min_step <= Step <= price_limit
    step_up = models.FloatField(null=True, blank=True, default=None)
    step_up_type = EnumField(choices=SettingType.choices, default=SettingType.ABSOLUTE)

    # Price step (absolute value) between the first and subsequent orders in descending series,
    # can be set by the user, can be calculated automatically if not set.
    # User.Min_step <= Step <= price_limit
    step_down = models.FloatField(null=True, blank=True, default=None)
    step_down_type = EnumField(choices=SettingType.choices, default=SettingType.ABSOLUTE)

    # Setting, coefficient by which each subsequent step is multiplied.
    step_down_delta = models.FloatField(null=True, blank=True, default=None)

    # Setting is set by the user.
    # The percentage of profit from the amount involved in the position
    # that the user wants to receive from the position.
    profit_target = models.FloatField(null=True, blank=True, default=None)

    # Setting is set by the user.
    # The percentage of the range between the opening price of the last order and the breakeven point of the round
    # when trading up (quote_asset) or down (base_asset), at which the position is closed.
    saver = models.FloatField(null=True, blank=True, default=None)

    # In DCA1 algorithm, "lot" and "step" will be calculated from risk_target and profit_limit
    algorithm = EnumField(choices=Algorithms.choices, default=Algorithms.DCA1)

    class Statuses(models.TextChoices):
        ON = 'ON'
        OFF = 'OFF'
        ERROR = 'ERROR'
        CANCELED = 'CANCELED'
        DONE = 'DONE'

    status = EnumField(choices=Statuses.choices, default=Statuses.OFF)

    # Setting is set by the user in percent.
    # If set, first buy order will be executed after price go down for this value.
    # if set and price go up, then buy will be executed when price go down from higher value.
    delay = models.FloatField(null=False, blank=False, default=0)


class Round(models.Model):
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE)


class Position(models.Model):
    round = models.ForeignKey(Round, on_delete=models.CASCADE)


class Order(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    position = models.ForeignKey(Position, on_delete=models.CASCADE)

    class Statuses(models.TextChoices):
        NEW = 'NEW'             # Means, that is not placed on exchange
        ACTIVE = 'ACTIVE'       # Means, that is placed on exchange
        FILLED = 'FILLED'
        CANCELED = 'CANCELED'
        EXPIRED = 'EXPIRED'
        ERROR = 'ERROR'

    status = EnumField(choices=Statuses.choices, default=Statuses.NEW)

    # https://binance-docs.github.io/apidocs/spot/en/#new-order-trade
    class Types(models.TextChoices):
        # Type and after it - Additional mandatory parameters of exchange
        LIMIT = 'LIMIT'  # timeInForce, quantity, price
        MARKET = 'MARKET'  # quantity or quoteOrderQty
        STOP_LOSS = 'STOP_LOSS'  # quantity, stopPrice or trailingDelta
        STOP_LOSS_LIMIT = 'STOP_LOSS_LIMIT'  # timeInForce, quantity, price, stopPrice or trailingDelta
        TAKE_PROFIT = 'TAKE_PROFIT'  # quantity, stopPrice or trailingDelta
        TAKE_PROFIT_LIMIT = 'TAKE_PROFIT_LIMIT'  # timeInForce, quantity, price, stopPrice or trailingDelta
        LIMIT_MAKER = 'LIMIT_MAKER'  # quantity, price
        #    LIMIT_MAKER are LIMIT orders that will be rejected if they would immediately match and trade as a taker.

    type = EnumField(choices=Types.choices, null=True, blank=True, default=None)

    class Sides(models.TextChoices):
        SELL = 'SELL'
        BUY = 'BUY'

    side = EnumField(choices=Sides.choices, null=True, blank=True, default=None)

    quote_quantity = models.FloatField(null=True, blank=True, default=None)
    quantity = models.FloatField(null=True, blank=True, default=None)
    price = models.FloatField(null=True, blank=True, default=None)
    stop_price = models.FloatField(null=True, blank=True, default=None)
    callback = models.TextField(default="")
    position_key = models.CharField(max_length=128, null=True, blank=True, default=None)

    class Meta:
        index_together = [
            ['position', 'position_key'],
        ]

    class CallbackStatuses(models.TextChoices):
        WAITING = 'WAITING'
        STARTED = 'STARTED'
        DONE = 'DONE'
        CANCELED = 'CANCELED'
        OCO_CANCELED = 'OCO_CANCELED'
        ERROR = 'ERROR'

    callback_status = EnumField(choices=CallbackStatuses.choices, default=CallbackStatuses.WAITING)
    callback_at = models.DateTimeField(auto_now=False, null=True, blank=True, default=None)

    result_quote_asset_quantity = models.FloatField(null=True, blank=True, default=None)
    oco_order = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, default=None)

    result_filled_quantity = models.FloatField(null=True, blank=True, default=None)
