from math import ceil
import pandas
import numpy
import os


def get_sampling_period(fn, column='Timestamp'):
    """Determines the sampling period based
    on the first 100 rows of the CSV-file"""

    if type(fn) is str:
        d = pandas.read_csv(fn, nrows=100, skiprows=10)
    elif type(fn) is pandas.DataFrame:
        d = fn
    else:
        raise ValueError("fn must be dataframe or filename")
    d[column] = pandas.to_datetime(d[column], format='%d-%m-%Y %H:%M:%S.%f')

    sampling_period = numpy.unique(numpy.diff(d[column].values))
    assert len(sampling_period) > 0, "The CSV-file is empty"
    assert len(sampling_period) == 1, (
        f"Different sampling periods: "
        f"{', '.join(map(str, sampling_period ))}")
    return int(sampling_period [0] / 1000000)  # milliseconds


def estimate_lines(fn, encoding='utf-8',
                   nbytes=32 * 1024 ** 2):
    """Estimate the number of lines in a file by
    extrapolating the number of lines in the first
    `nbytes` bytes to the total file size. Lines
    are ended with `'\n'.encode(encoding)`. Useful
    for approximating progress bars."""
    size = os.stat(fn).st_size
    marker = '\n'.encode(encoding)
    with open(fn, 'rb') as f:
        sample = f.read(nbytes)
        n_lines = sample.count(marker)
        return int(ceil(size / len(sample) * n_lines))


def batched(filename, batch_size, acceleration_columns=['Accelerometer X', 'Accelerometer Y', 'Accelerometer Z']):
    """Returns batches of `batch_size` rows from an Actigraph CSV-file."""

    for chunk in pandas.read_csv(filename, chunksize=batch_size, skiprows=10):
        chunk.rename(columns=dict(zip(['Timestamp'] + acceleration_columns, ['datetime', 'accx', 'accy', 'accz'])),
                     inplace=True)
        yield chunk
