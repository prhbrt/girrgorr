from . import metrics as metric_functions
from . import actigraph

from math import ceil
import pandas
from tqdm.auto import tqdm


def get_metrics(filename,
                window_size=5, batch_size=1000,
                reader=actigraph, progressbar=False,
                metrics=['anglex', 'angley', 'anglez', 'enmo']
                ):
    """Calculates these metrics for every `window_size`
    seconds in the CSV-file:
     - x, y and z-angles, the angles the acceleration
       goes away from on yz, xz and yz-planes, and
     - ENMO-metric (Euclidean norm minus one (clipped at 0))
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
    sampling_period = reader.get_sampling_period(filename)
    rows_in_batch = window_size * batch_size * 1000 // sampling_period

    if progressbar:
        def progressbar(x):
            expected_rows = int(ceil(reader.estimate_lines(filename) / rows_in_batch))
            return tqdm(x, total=expected_rows)
    else:
        def progressbar(x):
            return x

    samples_in_a_window = window_size * 1000 // sampling_period
    result = []
    # read the CSV file in batches of `rows_in_batch` rows.
    for chunk in progressbar(reader.batched(filename, batch_size=rows_in_batch)):
        xyz = chunk[['accx', 'accy', 'accz']].values
        xyz = metric_functions.seperate_time_windows(xyz, window_size, sampling_period)

        dataframe = {
            'datetime': chunk['datetime'].values[::samples_in_a_window],

            # for debugging
            'accx': xyz[:, 0, 0],
            'accy': xyz[:, 0, 1],
            'accz': xyz[:, 0, 2],
        }
        if 'angles' in metrics:
            anglex, angley, anglez = metric_functions.windowed_angles(xyz)
            dataframe.update({
                'anglex': anglex,
                'angley': angley,
                'anglez': anglez
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
    result['datetime'] = pandas.to_datetime(result['datetime'])
    return result
