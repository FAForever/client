class ModelTransaction:
    """
    Allows model classes to postpone side effects of a model update (such as
    emitting signals) until after the model is in a consistent state.
    """
    def __init__(self):
        self._signals = []

    def emit(self, *args):
        self._signals.append(args)

    def finalize(self):
        for s in self._signals:
            s[0].emit(*s[1:])
        self._signals = []


# An easy way for a function to create a transaction if it's called without one
# and finalize it once it's done, and otherwise use a supplied transaction.
#
# In order to use it, a function has to define a _transaction argument as its
# last, and should not accept another transaction instance. The transaction
# argument will be added to kwargs if any were defined and _transaction was not
# among them, or if there are no kwargs and the last arg is not a transaction.

def transactional(fn):
    def trans_fn(*args, **kwargs):
        top_transaction = None

        # _transaction is last, so if kwargs are non-empty, it's in them
        if kwargs:
            if "_transaction" not in kwargs:
                top_transaction = ModelTransaction()
                kwargs["_transaction"] = top_transaction
        else:
            if not args or not isinstance(args[-1], ModelTransaction):
                top_transaction = ModelTransaction()
                args = args + (top_transaction,)

        ret = fn(*args, **kwargs)
        if top_transaction is not None:
            top_transaction.finalize()
        return ret
    return trans_fn
