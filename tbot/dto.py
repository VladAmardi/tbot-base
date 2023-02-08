from dataclasses import dataclass


class ExchangeConnectionWorkerCommands:
    START = 'START'
    STOP = 'STOP'


@dataclass
class ExchangeConnectionWorkerCommand:
    exchange_connection_id: int
    command: str = ""


@dataclass
class Callback:
    params: {}
    method: str | None = None
