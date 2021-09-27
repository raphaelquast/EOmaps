from itertools import tee

def pairwise(iterable, pairs=2):
    """
    a generator to return n consecutive values from an iterable, e.g.:

        pairs = 2
        s -> (s0,s1), (s1,s2), (s2, s3), ...

        pairs = 3
        s -> (s0, s1, s2), (s1, s2, s3), (s2, s3, s4), ...

    adapted from https://docs.python.org/3.7/library/itertools.html
    """
    x = tee(iterable, pairs)
    for n, n_iter in enumerate(x[1:]):
        [next(n_iter, None) for i in range(n + 1)]
    return zip(*x)
