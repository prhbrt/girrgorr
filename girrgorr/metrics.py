import numpy


def separate_time_windows(xyz, window_size, sampling_period):
    """Reshape the first dimension of xyz into
    two dimensions, the first iterating over
    different windows, the second over the samples
    in the window (and the third over the x, y and
    z-components). Samples that don't fill a full
        window are dropped."""
    # size of one window
    dim1 = window_size * 1000 // sampling_period
    # number of windows
    dim0 = len(xyz) // dim1
    # the last window might be cut of if it's not the
    # same size as the others.
    return xyz[:dim1 * dim0].reshape(dim0, dim1, -1)


def windowed_angles(xyz):
    """Calculate the angles for all directions, where
    `anglex = atan(x, sqrt(y**2 + z**2))` and similar
    for angley and anglez. Returns the mean over these
    angles w.r.t. dimension 1. These three angles only
    represent the direction of the acceleration, not the
    magnitude."""

    # Vectorized version of:
    # atan2(x, sqrt(y**2 + z**2))
    # atan2(y, sqrt(x**2 + z**2))
    # atan2(z, sqrt(x**2 + y**2))
    
    angles = numpy.arctan2(
        xyz,
        numpy.sqrt(
            xyz[:, :, [1, 2, 0]] ** 2 +  # y, z, x respectively
            xyz[:, :, [2, 0, 1]] ** 2  # z, x, y respectively
        )
    ) * 180 / numpy.pi
    anglex, angley, anglez = angles.mean(1).T

    return anglex, angley, anglez


def enmo(xyz):
    """For each window, calculates the ENMO value."""
    en = numpy.sqrt(numpy.sum(xyz ** 2, axis=2))
    return numpy.clip(en - 1, 0, None).mean(axis=1)


def en(xyz):
    """For each window, calculates the EN value."""
    return numpy.sqrt(numpy.sum(xyz ** 2, axis=2)).mean(axis=1)
