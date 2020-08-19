import numpy
import datetime
from matplotlib import pyplot


def hours_from_time(times):
    """given datetime series from pandas, returns an array
    of floating point numbers between 0 and 24 to indicate the
    moment of the day."""
    return times.hour + times.minute / 60 + times.second / 3600


def extract_days(data, night=datetime.time(3)):
    """Split the data to days at the time provided in night. all areas where
    the enmo is zero are removed."""

    # TODO: use the original accelerations to determine whether the device is worn.
    # enmo might be 0 due to clipping while there was variance in the original
    # accelerations.

    inactive = data['enmo'] == 0
    night_points = data['datetime'].dt.time == night
    boundaries = list(numpy.where(inactive.values[:-1] != inactive.values[1:])[0])

    if inactive[0]:
        boundaries = [0] + boundaries

    boundaries = boundaries + [len(data)]

    result = [[0]]
    for a, b in zip(boundaries[::2], boundaries[1::2]):
        assert data[a + 1:b + 1]['enmo'].mean() == 0
        if night_points[a:b].max():
            result[-1].append(a)
            result.append([b + 1])

    result[-1].append(len(data))

    return [
        data[slice(*j)]
        for i, j in enumerate(result)
        if len(data[slice(*j)]) > 0
    ]


def days_plot(data, measures={'enmo'}, night=datetime.time(3)):
    """separates data into days and plots the measures listed in measures
    'enmo', 'angles and/or 'nonzero', as curves around the y-axis. angles
    are scaled by 180 to be in (-.5, .5) range."""
    days = extract_days(data, night=night)
    pyplot.figure(figsize=(10, 5))
    unknown_measures = ', '.join(map(str, set(measures) - {'nonzero', 'enmo', 'angles'}))
    assert len(unknown_measures) == 0, f"Unknown measures: {unknown_measures}"

    for i, rows in enumerate(days):
        x = hours_from_time(rows['datetime'].dt)

        if 'nonzero' in measures:
            pyplot.plot(x, 0.5 * (rows['enmo'].values > 0) + (1 * i))

        if 'enmo' in measures:
            pyplot.plot(x, rows['enmo'].values + (1 * i))

        if 'angles' in measures:
            pyplot.plot(x, rows['anglex'].values / 180 + (1 * i))
            pyplot.plot(x, rows['angley'].values / 180 + (1 * i))
            pyplot.plot(x, rows['anglez'].values / 180 + (1 * i))

    pyplot.xticks(numpy.arange(25))


def contains_night(day, night=datetime.time(3)):
    """Returns whether the day contains the specified night time,
    in order to filter out days that weren't properly split
    around that night time."""
    return any(day['datetime'].dt.time == night)
