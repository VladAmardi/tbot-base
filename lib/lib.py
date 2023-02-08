import sys


def percent_to_float(s: str):
    if s == "" or s is None:
        return 0
    s = str(float(str(s).rstrip("%")))
    i = s.find(".")
    if i == -1:
        return int(s) / 100
    if s.startswith("-"):
        return -percent_to_float(s.lstrip("-"))
    s = s.replace(".", "")
    i -= 2
    if i < 0:
        return float("." + "0" * abs(i) + s)
    else:
        return float(s[:i] + "." + s[i:])


def is_percent(s: str):
    return s.endswith('%')


def print_object(model, file=sys.stdout, key_filter: list | None = None, line_prefix: str = ""):
    assert hasattr(model, '_meta')
    # noinspection PyProtectedMember
    opts = model._meta
    for f in sorted(opts.fields + opts.many_to_many):
        if key_filter is not None and f.name not in key_filter:
            continue
        print('%s%s: %s' % (line_prefix, f.name, f.value_from_object(model)), file=file)
        if hasattr(file, 'flush') and callable(file.flush):
            file.flush()
