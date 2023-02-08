from django.core.management.base import BaseCommand
from lib import boolean_input, is_percent, percent_to_float
from tbot.models import Symbol, User, ExchangesNames, ExchangeConnection, Bot, SettingType
from tbot.exchanges import Exchange
from tbot.algorithms import Algorithm


# https://habr.com/ru/post/415049/
class Command(BaseCommand):
    help = 'Bot management - create bot'

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username=options['username'])
        except User.DoesNotExist:
            print("User does not exist")
            return

        if options['exchange'] not in ExchangesNames.labels:
            print("Exchange does not exist. Available options are: " + (', '.join(ExchangesNames.labels)))
            return

        exchange_name = ExchangesNames.names[ExchangesNames.labels.index(options['exchange'])]
        try:
            exchange_connection = ExchangeConnection.objects.get(exchange=exchange_name, owner=user)
        except ExchangeConnection.DoesNotExist:
            print("User does not have configured connection to exchange")
            return

        symbol_name = str(options['symbol']).upper()
        try:
            symbol = Symbol.objects.get(symbol=symbol_name, exchange=exchange_name)
        except Symbol.DoesNotExist:
            print("Symbol " + symbol_name + " not in DB")
            return

        exchange = Exchange.get_exchange(exchange=exchange_name)(connection=exchange_connection)

        price = exchange.get_asset_price(symbol=symbol.symbol)

        # The limit value of the price up to which the grid of orders is calculated,
        # as well as the risk.
        # When this value is reached, all positions of the round are closed in the red.
        # Specified as (1) a percentage of the current price or as (2) the absolute value of the price.
        # Having reached this price, the loss must be within the risk_target.
        if is_percent(options['price_limit']):
            price_limit_type = SettingType.PERCENT
            price_limit = percent_to_float(options['price_limit'])
            if price_limit >= 1:
                print("--price_limit/-p in percent should be less than 100%")
                return
        else:
            price_limit_type = SettingType.ABSOLUTE
            price_limit = float(options['price_limit'])
            if price_limit >= price:
                print("--price_limit/-p should not be grater than price (" +
                      str(price) + ")")
                return

        # Setting, coefficient by which each subsequent lot size is multiplied.
        lot_multiplier_down = float(options['lot_multiplier_down'])
        if lot_multiplier_down == 0:
            print("--lot_multiplier_down/-lmd should be grater than 0")
            return

        # Setting, coefficient by sum of which and 1 each subsequent step is multiplied
        # step = previous_step * ( 1 + step_delta ).
        step_down_delta = float(options['step_down_delta'])

        # Setting is set by the user.
        # The percentage of profit from the amount involved in the position
        # that the user wants to receive from the position.
        if not is_percent(options['profit_target']):
            print("--profit_target/-pt should be set as percent (ends with %)")
            return
        profit_target = percent_to_float(options['profit_target'])

        # Setting is set by the user.
        # The percentage of the range between the opening price of the last order and the breakeven point of
        # the round when trading up (quote_asset) or down (base_asset), at which the position is closed.
        if not is_percent(options['saver']):
            print("--saver/-sv should be set as percent (ends with %)")
            return
        saver = percent_to_float(options['saver'])

        # First order size (lot_multiplier can be enabled for subsequent orders) - setting,
        # can be set, can be expected automatically.
        # Lot >= min_notional
        lot = float(options['lot'])
        if lot < symbol.min_notional:
            print("--lot/-l should be grater than min_notional (min_notional=" + str(symbol.min_notional) + ")")
            return

        min_step_abs = user.profile.min_step * price

        # Price step (absolute value or percent) between the first and subsequent orders in ascending series,
        # can be set by the user, can be calculated automatically if not set.
        # User.Min_step <= Step <= price_limit
        if is_percent(options['step_up']):
            step_up_type = SettingType.PERCENT
            step_up = percent_to_float(options['step_up'])
            step_up_abs = step_up * price
        else:
            step_up_type = SettingType.ABSOLUTE
            step_up = float(options['step_up'])
            step_up_abs = step_up

        if step_up_abs < min_step_abs:
            print("--step_up/-st_up in absolute value should be grater than min_step_price (step_up_abs=" +
                  str(step_up_abs) + ", min_step_price=" + str(min_step_abs) + ")")
            return

        # Price step (absolute value) between the first and subsequent orders in descending series,
        # can be set by the user, can be calculated automatically if not set.
        # User.Min_step <= Step <= price_limit
        if is_percent(options['step_down']):
            step_down_type = SettingType.PERCENT
            step_down = percent_to_float(options['step_down'])
            step_down_abs = step_down * price
        else:
            step_down_type = SettingType.ABSOLUTE
            step_down = float(options['step_down'])
            step_down_abs = step_down

        if step_down_abs < min_step_abs:
            print("--step_down/-st_down in absolute value should be grater than min_step_price (step_down_abs=" +
                  str(step_down_abs) + ", min_step_price=" + str(min_step_abs) + ")")
            return

        bot = Bot(
            owner=user,
            exchange_connection=exchange_connection,
            symbol=symbol,
            price_limit_type=price_limit_type,
            price_limit=price_limit,
            lot=lot,
            lot_multiplier_down=lot_multiplier_down,
            step_up=step_up,
            step_up_type=step_up_type,
            step_down=step_down,
            step_down_type=step_down_type,
            step_down_delta=step_down_delta,
            profit_target=profit_target,
            saver=saver,
            delay=percent_to_float(options['delay'])
        )

        print("Will be created bot with params:")
        # noinspection PyProtectedMember
        opts = bot._meta
        for f in sorted(opts.fields + opts.many_to_many):
            print('%s: %s' % (f.name, f.value_from_object(bot)))

        if not boolean_input(question="Are you sure? [yN]", default=False):
            print("Canceled.")
            return

        bot.save()
        print("Bot successfully created")

        print("Starting user_data_stream if needed...")
        exchange.user_data_stream_start()

        print("Starting algorithm...")
        Algorithm.get_algorithm(bot_id=bot.id).start()

        print("Done")

    def add_arguments(self, parser):
        parser.add_argument(
            '-u',
            '--username',
            action='store',
            default=False,
            help='User name',
            required=True,
            dest='username'
        )

        parser.add_argument(
            '-e',
            '--exchange',
            action='store',
            default=False,
            help='Exchange name, available options are: ' + (', '.join(ExchangesNames.labels)),
            required=True,
            dest='exchange'
        )

        parser.add_argument(
            '-s',
            '--symbol',
            action='store',
            default=False,
            help='Symbol (eg. BTCUSDT)',
            required=True,
            dest='symbol'
        )

        parser.add_argument(
            '-p',
            '--price_limit',
            action='store',
            default=False,
            help='The limit value of the price up to which the grid of orders is calculated, \
                  as well as the risk. \
                  When this value is reached, all positions of the round are closed in the red. \
                  Specified as (1) a percentage of the current price or as (2) the absolute value of the price. \
                  Having reached this price, the loss must be within the risk_target.',
            required=True,
            dest='price_limit'
        )

        parser.add_argument(
            '-l',
            '--lot',
            action='store',
            default=False,
            help='First order size (lot_multiplier_down can be enabled for subsequent orders in descending series). \
                  Lot >= min_notional \
                  Expressed in quote asset',
            required=True,
            dest='lot'
        )

        parser.add_argument(
            '-lmd',
            '--lot_multiplier_down',
            action='store',
            default=1,
            help='Setting, coefficient by which each subsequent lot size is multiplied in descending series. \
                  [Default=1]',
            required=False,
            dest='lot_multiplier_down'
        )

        parser.add_argument(
            '-st_up',
            '--step_up',
            action='store',
            default=False,
            help='Price step (in absolute value or percent) between the first and subsequent orders \
                  in ascending series. \
                  User.Min_step <= Step <= price_limit',
            required=True,
            dest='step_up'
        )

        parser.add_argument(
            '-st_down',
            '--step_down',
            action='store',
            default=False,
            help='Price step (in absolute value or percent) between the first and subsequent orders \
                  in descending series. \
                  User.Min_step <= Step <= price_limit',
            required=True,
            dest='step_down'
        )

        parser.add_argument(
            '-std',
            '--step_down_delta',
            action='store',
            default=0,
            help='Setting, coefficient by which each subsequent step in descending series is multiplied. \
                  [Default=0] \
                  Not applicable for ascending series.',
            required=False,
            dest='step_down_delta'
        )

        parser.add_argument(
            '-pt',
            '--profit_target',
            action='store',
            default=False,
            help='Setting is set by the user. \
                 The percentage of profit from the amount involved in the position \
                 that the user wants to receive from the position.',
            required=True,
            dest='profit_target'
        )

        parser.add_argument(
            '-sv',
            '--saver',
            action='store',
            default=False,
            help='Setting is set by the user. \
                 The percentage of the range between the opening price of the last order and the breakeven point of \
                 the round when trading up (quote_asset) or down (base_asset), at which the position is closed.',
            required=True,
            dest='saver'
        )

        parser.add_argument(
            '-d',
            '--delay',
            action='store',
            default=0,
            help='Setting is set by the user in percent. \
                 If set, first buy order will be executed after price go down for this value. \
                 if set and price go up, then buy will be executed when price go down from higher value.',
            required=False,
            dest='delay'
        )
