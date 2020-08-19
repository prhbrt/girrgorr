from . import metrics as metric_functions
from . import actigraph

from math import ceil
import pandas
from tqdm.auto import tqdm

import numpy


def fill_head_and_tail_nan(x):
    """Fill the leading and trailing nans with the neasest non-nan value.

    [nan, nan, 5, 6, 4, nan] -> [5, 5, 5, 6, 4, 4]
    """
    idx = numpy.where(~numpy.isnan(x[:, 0]))[0]
    assert len(idx) > 0, "All values were nan"
    x[:idx[0]] = x[idx[0]]
    x[idx[-1]:] = x[idx[-1]]

    return x


def padded(it, padding):
    """
    Yield tuples of two items, once for every item in it. The first item is the original value of it.

    The second is the original item prepended and appended with the last respectively first `padding`
    elements from the previous respectively next item in it. This allows you to apply rolling window
    operations without boundary effects.

    The first and last item are prepended respectively appended with nans.
    
    For example, assume `it` yields 3 items, 3 slightly larger items will be yielded by `padded(...)`.
    This example assume `padding=2`. Note that the items can have different lengths. n stands for nan.
    
    input iterator:
        [. . . . .]
                  [. . . . . . .]
                                [. . . . . . . . . . .]
    output iterator:            
    [n n . . . . . . .]
              [. . . . . . . . . . .]
                            [. . . . . . . . . . . . . n n]
    
    
    :param it: iterator over pandas.DataFrames or numpy.ndarrays (not mixed)
    :param padding: elements to pre/append.
    :return: yields tuples of unpadded and padded items.
    """

    # In case there will only be one chunk, the loop is avoided and only next_chunk
    # padded with nans is yieled in the last statement of the function.
    next_chunk = chunk = next(it)

    # Create the nd-array or dataframe that will be pre- and appended to the
    # first and last chunk respectively. Also define the function to use for
    # concatenation.
    prepend = append = numpy.nan * numpy.zeros((padding,) + chunk.shape[1:])
    if type(chunk) == numpy.ndarray:
        concat = numpy.concatenate
    elif type(chunk) == pandas.DataFrame:
        concat = pandas.concat
        prepend = append = pandas.DataFrame(prepend, columns=chunk.columns)
    else:
        raise ValueError(f"Unsupported iterator result: {type(chunk)}")

    # pre-read the next chunk, then yield the chunk and the padded version using the start of
    # the
    for next_chunk in it:
        # If the next_chunk is smaller than the padding, we already need to pad some nans
        # mostly this value will be zero.
        assert len(chunk) >= padding, (
            f"Non-last element of it is smaller than the padding, this is not allowed "
            f"for practical reasons to avoid needing to preload more than one frame: {len(chunk)}"
        )
        nan_append = max(0, padding - len(next_chunk))

        yield chunk, concat([prepend, chunk, next_chunk[:padding], append[:nan_append]])
        prepend = chunk[-padding:]
        append = append[nan_append:]
        chunk = next_chunk

    yield next_chunk, concat([prepend, next_chunk, append])


def get_metrics(filename,
                window_size=5, batch_size=1000,
                reader=actigraph, progressbar=False,
                metrics=['angles', 'en', 'enmo'],
                high_pass_frequency_angles=0.2,
                ):
    """Calculates these metrics for every `window_size`
    seconds in the CSV-file:
     - x, y and z-angles, the angles the acceleration
       goes away from on yz, xz and yz-planes, and
     - ENMO-metric (Euclidean norm minus one (clipped at 0))
     - EN (Euclidean norm)
    averaged for each window. These are returned as a
    pandas DataFrame. `batch_size` determines the number of
    windows read into memory for vectorized computation, and
    is a trade off between memory-consumption, speed and
    progress bar resolution. The progressbar is only an
    estimate, but accurate when rows have similar sizes in
    bytes across the CSV. If the last window is smaller
    then `window_size` seconds, it's dropped. The first 100
    rows are used to determine the sampling period. Uniform
    sampling is assumed from here on, but not asserted since
    this would require slow datetime parsing."""

    unknown_metrics = set(metrics) - {'angles', 'enmo', 'en'}
    assert len(unknown_metrics) == 0, f"Unknown metrics: {unknown_metrics}"

    sampling_period = reader.get_sampling_period(filename)
    rows_in_batch = window_size * batch_size * 1000 // sampling_period

    if progressbar:
        def progressbar(x):
            expected_rows = int(ceil(reader.estimate_lines(filename) / rows_in_batch))
            return tqdm(x, total=expected_rows, leave=False, desc=filename.split('/')[-1])
    else:
        def progressbar(x):
            return x

    median_window_size = round(1000 / sampling_period / high_pass_frequency_angles)
    padding = median_window_size // 2
    median_window_size = 2 * padding + 1  # ensure the window is odd


    samples_in_a_window = window_size * 1000 // sampling_period
    result = []

    # read the CSV file in batches of `rows_in_batch` rows.
    for chunk, padded_chunk in padded(
            iter(progressbar(reader.batched(filename, batch_size=rows_in_batch))),
            padding=padding
    ):
        if sampling_period * len(chunk) < window_size * 1000:
            # not enough samples to create one window
            break

        xyz = chunk[['accx', 'accy', 'accz']].values
#         for column in ('accx', 'accy', 'accz'):
#             xyz = chunk[column]

        xyz = metric_functions.separate_time_windows(xyz, window_size, sampling_period)

        dataframe = {
            'datetime': chunk['datetime'].values[::samples_in_a_window],

            # # for debugging
            # 'accx': xyz[:, 0, 0],
            # 'accy': xyz[:, 0, 1],
            # 'accz': xyz[:, 0, 2],
        }

        if 'angles' in metrics:
            xyz_rolling_median = padded_chunk[['accx', 'accy', 'accz']].rolling(median_window_size,
                                                                                center=True).median().values
            nan_area = median_window_size // 2
            xyz_rolling_median = xyz_rolling_median[nan_area:-nan_area]
            xyz_rolling_median = fill_head_and_tail_nan(xyz_rolling_median.copy())
            xyz_rolling_median = metric_functions.separate_time_windows(xyz_rolling_median, window_size,
                                                                        sampling_period)

            anglex, angley, anglez = metric_functions.windowed_angles(xyz_rolling_median)

            dataframe.update({
                'anglex': anglex,
                'angley': angley,
                'anglez': anglez
            })

        if 'en' in metrics:
            dataframe.update({
                'en': metric_functions.en(xyz)
            })

        if 'enmo' in metrics:
            dataframe.update({
                'enmo': metric_functions.enmo(xyz)
            })

        # dictionary of list to list of dictionaries
        result.extend(
            dict(zip(dataframe.keys(), x))
            for x in zip(*dataframe.values())
        )

    result = pandas.DataFrame(result)
    # result['datetime'] = pandas.to_datetime(result['datetime'], format='%d-%m-%Y %H:%M:%S.%f')
    return result
