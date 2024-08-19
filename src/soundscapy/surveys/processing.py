"""
Soundscape survey data processing module.

This module contains functions for processing and analyzing soundscape survey data,
including ISO coordinate calculations, data quality checks, and SSM metrics.

Notes
-----
The functions in this module are designed to be fairly general and can be used with any dataset in a similar format to
the ISD. The key to this is using a simple dataframe/sheet with the following columns:
    Index columns: e.g. LocationID, RecordID, GroupID, SessionID
    Perceptual attributes: PAQ1, PAQ2, ..., PAQ8
    Independent variables: e.g. Laeq, N5, Sharpness, etc.

The key functions of this module are designed to clean/validate datasets, calculate ISO coordinate values or SSM metrics,
filter on index columns. Functions and operations which are specific to a particular dataset are located in their own
modules under `soundscape.databases`.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger
from scipy import optimize

from soundscapy.surveys.survey_utils import EQUAL_ANGLES, PAQ_IDS, return_paqs

np.set_printoptions(legacy="1.25")


@dataclass
class ISOCoordinates:
    """Dataclass for storing ISO coordinates."""

    pleasant: float
    eventful: float


@dataclass
class SSMMetrics:
    """Dataclass for storing Structural Summary Method (SSM) metrics."""

    amplitude: float
    angle: float
    elevation: float
    displacement: float
    r_squared: float

    def table(self) -> pd.Series:
        return pd.Series(
            {
                "amplitude": self.amplitude,
                "angle": self.angle,
                "elevation": self.elevation,
                "displacement": self.displacement,
                "r_squared": self.r_squared,
            }
        )


def calculate_iso_coords(
    results_df: pd.DataFrame,
    val_range: Tuple[int, int] = (5, 1),
    angles: Tuple[int, ...] = EQUAL_ANGLES,
) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate the projected ISOPleasant and ISOEventful coordinates.

    Parameters
    ----------
    results_df : pd.DataFrame
        DataFrame containing PAQ data.
    val_range : Tuple[int, int], optional
        (max, min) range of original PAQ responses, by default (5, 1)
    angles : Tuple[int, ...], optional
        Angles for each PAQ in degrees, by default EQUAL_ANGLES

    Returns
    -------
    Tuple[pd.Series, pd.Series]
        ISOPleasant and ISOEventful coordinate values

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({
    ...     'PAQ1': [4, 2], 'PAQ2': [3, 5], 'PAQ3': [2, 4], 'PAQ4': [1, 3],
    ...     'PAQ5': [5, 1], 'PAQ6': [3, 2], 'PAQ7': [4, 3], 'PAQ8': [2, 5]
    ... })
    >>> iso_pleasant, iso_eventful = calculate_iso_coords(df)
    >>> iso_pleasant.round(2)
    0   -0.03
    1    0.47
    dtype: float64
    >>> iso_eventful.round(2)
    0   -0.28
    1    0.18
    dtype: float64
    """
    scale = max(val_range) - min(val_range)

    paq_df = return_paqs(results_df, incl_ids=False)

    iso_pleasant = paq_df.apply(lambda row: _adj_iso_pl(row, angles, scale), axis=1)
    iso_eventful = paq_df.apply(lambda row: _adj_iso_ev(row, angles, scale), axis=1)

    logger.info(f"Calculated ISO coordinates for {len(results_df)} samples")
    return iso_pleasant, iso_eventful


def _adj_iso_pl(values: pd.Series, angles: Tuple[int, ...], scale: float) -> float:
    """
    Calculate the adjusted ISOPleasant value.

    This is an internal function used by calculate_iso_coords.

    Parameters
    ----------
    values : pd.Series
        PAQ values for a single sample
    angles : Tuple[int, ...]
        Angles for each PAQ in degrees
    scale : float
        Scale factor for normalization

    Returns
    -------
    float
        Adjusted ISOPleasant value
    """
    iso_pl = np.sum(
        [np.cos(np.deg2rad(angle)) * value for angle, value in zip(angles, values)]
    )
    return iso_pl / (
        scale / 2 * np.sum(np.abs([np.cos(np.deg2rad(angle)) for angle in angles]))
    )


def _adj_iso_ev(values: pd.Series, angles: Tuple[int, ...], scale: float) -> float:
    """
    Calculate the adjusted ISOEventful value.

    This is an internal function used by calculate_iso_coords.

    Parameters
    ----------
    values : pd.Series
        PAQ values for a single sample
    angles : Tuple[int, ...]
        Angles for each PAQ in degrees
    scale : float
        Scale factor for normalization

    Returns
    -------
    float
        Adjusted ISOEventful value
    """
    iso_ev = np.sum(
        [np.sin(np.deg2rad(angle)) * value for angle, value in zip(angles, values)]
    )
    return iso_ev / (
        scale / 2 * np.sum(np.abs([np.sin(np.deg2rad(angle)) for angle in angles]))
    )


def add_iso_coords(
    data: pd.DataFrame,
    val_range: Tuple[int, int] = (1, 5),
    names: Tuple[str, str] = ("ISOPleasant", "ISOEventful"),
    overwrite: bool = False,
    angles: Tuple[int, ...] = EQUAL_ANGLES,
) -> pd.DataFrame:
    """
    Calculate and add ISO coordinates as new columns in the DataFrame.

    Parameters
    ----------
    data : pd.DataFrame
        Input DataFrame containing PAQ data
    val_range : Tuple[int, int], optional
        (min, max) range of original PAQ responses, by default (1, 5)
    names : Tuple[str, str], optional
        Names for new coordinate columns, by default ("ISOPleasant", "ISOEventful")
    overwrite : bool, optional
        Whether to overwrite existing ISO coordinate columns, by default False
    angles : Tuple[int, ...], optional
        Angles for each PAQ in degrees, by default EQUAL_ANGLES

    Returns
    -------
    pd.DataFrame
        DataFrame with new ISO coordinate columns added

    Raises
    ------
    Warning
        If ISO coordinate columns already exist and overwrite is False

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({
    ...     'PAQ1': [4, 2], 'PAQ2': [3, 5], 'PAQ3': [2, 4], 'PAQ4': [1, 3],
    ...     'PAQ5': [5, 1], 'PAQ6': [3, 2], 'PAQ7': [4, 3], 'PAQ8': [2, 5]
    ... })
    >>> df_with_iso = add_iso_coords(df)
    >>> df_with_iso[['ISOPleasant', 'ISOEventful']].round(2)
       ISOPleasant  ISOEventful
    0        -0.03        -0.28
    1         0.47         0.18
    """
    for name in names:
        if name in data.columns:
            if overwrite:
                data = data.drop(name, axis=1)
            else:
                raise Warning(
                    f"{name} already in dataframe. Use `overwrite=True` to replace it."
                )

    iso_pleasant, iso_eventful = calculate_iso_coords(
        data, val_range=val_range, angles=angles
    )
    data = data.assign(**{names[0]: iso_pleasant, names[1]: iso_eventful})

    logger.info(f"Added ISO coordinates to DataFrame with column names: {names}")
    return data


def likert_data_quality(
    df: pd.DataFrame, allow_na: bool = False, val_range: Tuple[int, int] = (1, 5)
) -> Optional[List[int]]:
    """
    Perform basic quality checks on PAQ (Likert scale) data.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing PAQ data
    allow_na : bool, optional
        Whether to allow NaN values in PAQ data, by default False
    val_range : Tuple[int, int], optional
        Valid range for PAQ values, by default (1, 5)

    Returns
    -------
    Optional[List[int]]
        List of indices to be removed, or None if no issues found

    Examples
    --------
    >>> import pandas as pd
    >>> import numpy as np
    >>> df = pd.DataFrame({
    ...     'PAQ1': [np.nan, 2, 3, 3], 'PAQ2': [3, 2, 6, 3], 'PAQ3': [2, 2, 3, 3],
    ...     'PAQ4': [1, 2, 3, 3], 'PAQ5': [5, 2, 3, 3], 'PAQ6': [3, 2, 3, 3],
    ...     'PAQ7': [4, 2, 3, 3], 'PAQ8': [2, 2, 3, 3]
    ... })
    >>> likert_data_quality(df)
    [0, 1, 2]
    >>> likert_data_quality(df, allow_na=True)
    [1, 2]
    """
    paqs = return_paqs(df, incl_ids=False)
    invalid_indices = []

    for i, row in paqs.iterrows():
        if not allow_na and row.isna().any():
            invalid_indices.append(i)
        elif row.notna().all():
            if row.min() < min(val_range) or row.max() > max(val_range):
                invalid_indices.append(i)
            elif row.nunique() == 1 and row.iloc[0] != np.mean(val_range):
                invalid_indices.append(i)

    if invalid_indices:
        logger.info(f"Found {len(invalid_indices)} samples with data quality issues")
        return invalid_indices

    logger.info("PAQ data quality check passed")
    return None


def simulation(
    n: int = 3000,
    val_range: Tuple[int, int] = (1, 5),
    incl_iso_coords: bool = False,
    **coord_kwargs,
) -> pd.DataFrame:
    """
    Generate random PAQ responses for simulation purposes.

    Parameters
    ----------
    n : int, optional
        Number of samples to simulate, by default 3000
    val_range : Tuple[int, int], optional
        Range of values for PAQ responses, by default (1, 5)
    add_iso_coords : bool, optional
        Whether to add calculated ISO coordinates, by default False
    **coord_kwargs : dict
        Additional keyword arguments to pass to add_iso_coords function

    Returns
    -------
    pd.DataFrame
        DataFrame of randomly generated PAQ responses

    Examples
    --------
    >>> df = simulation(n=5, incl_iso_coords=True)
    >>> df.shape
    (5, 10)
    >>> list(df.columns)
    ['PAQ1', 'PAQ2', 'PAQ3', 'PAQ4', 'PAQ5', 'PAQ6', 'PAQ7', 'PAQ8', 'ISOPleasant', 'ISOEventful']
    """
    np.random.seed(42)
    df = pd.DataFrame(
        np.random.randint(min(val_range), max(val_range) + 1, size=(n, 8)),
        columns=PAQ_IDS,
    )

    if incl_iso_coords:
        df = add_iso_coords(df, val_range=val_range, **coord_kwargs)

    logger.info(f"Generated simulated PAQ data with {n} samples")
    return df


def ssm_metrics(
    df: pd.DataFrame,
    paq_cols: List[str] = PAQ_IDS,
    method: str = "cosine",
    val_range: Tuple[int, int] = (5, 1),
    angles: Tuple[int, ...] = EQUAL_ANGLES,
) -> pd.DataFrame:
    """
    Calculate the Structural Summary Method (SSM) metrics for each response.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing PAQ data
    paq_cols : List[str], optional
        List of PAQ column names, by default PAQ_IDS
    method : str, optional
        Method to calculate SSM metrics, either "cosine" or "polar", by default "cosine"
    val_range : Tuple[int, int], optional
        Range of values for PAQ responses, by default (5, 1)
    angles : Tuple[int, ...], optional
        Angles for each PAQ in degrees, by default EQUAL_ANGLES

    Returns
    -------
    pd.DataFrame
        DataFrame containing the SSM metrics

    Raises
    ------
    ValueError
        If PAQ columns are not present in the DataFrame or if an invalid method is specified

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({
    ...     'PAQ1': [4, 2], 'PAQ2': [3, 5], 'PAQ3': [2, 4], 'PAQ4': [1, 3],
    ...     'PAQ5': [5, 1], 'PAQ6': [3, 2], 'PAQ7': [4, 3], 'PAQ8': [2, 5]
    ... })
    >>> ssm_metrics(df).round(2)
       amplitude   angle  elevation  displacement  r_squared
    0       0.68  263.82      10.57         -7.57       0.15
    1       1.21   20.63       0.01          3.11       0.39
    """
    # TODO: Replace with a call to circumplex package
    if not set(paq_cols).issubset(df.columns):
        raise ValueError("PAQ columns are not present in the DataFrame")

    if method == "polar":
        iso_pleasant, iso_eventful = calculate_iso_coords(
            df[paq_cols], val_range, angles
        )
        r, theta = _convert_to_polar_coords(iso_pleasant, iso_eventful)
        mean = df[paq_cols].mean(axis=1)
        mean = mean / (max(val_range) - min(val_range)) if val_range != (0, 1) else mean

        return pd.DataFrame(
            {
                "amplitude": r,
                "angle": theta,
                "elevation": mean,
                "displacement": 0,  # Displacement is always 0 for polar method
                "r_squared": 1,  # R-squared is always 1 for polar method
            }
        )
    elif method == "cosine":
        return df[paq_cols].apply(
            lambda y: ssm_cosine_fit(y, angles).table(),
            axis=1,
            result_type="expand",
        )
    else:
        raise ValueError("Method must be either 'polar' or 'cosine'")


def ssm_cosine_fit(
    y: pd.Series,
    angles: Tuple[int, ...] = EQUAL_ANGLES,
    bounds: Tuple[List[float], List[float]] = (
        [0, 0, 0, -np.inf],
        [np.inf, 360, np.inf, np.inf],
    ),
) -> SSMMetrics:
    """
    Fit a cosine model to the PAQ data for SSM analysis.

    Parameters
    ----------
    y : pd.Series
        Series of PAQ values
    angles : Tuple[int, ...], optional
        Angles for each PAQ in degrees, by default EQUAL_ANGLES
    bounds : Tuple[List[float], List[float]], optional
        Bounds for the optimization parameters, by default ([0, 0, 0, -np.inf], [np.inf, 360, np.inf, np.inf])

    Returns
    -------
    SSMMetrics
        Calculated SSM metrics

    Examples
    --------
    >>> import pandas as pd
    >>> y = pd.Series([4, 3, 2, 1, 5, 3, 4, 2])
    >>> metrics = ssm_cosine_fit(y)
    >>> [round(v, 2) if isinstance(v, float) else v for v in metrics.table()]
    [0.68, 263.82, 10.57, -7.57, 0.15]
    """

    def cosine_model(theta, amp, delta, elev, dev):
        return elev + amp * np.cos(np.radians(theta - delta)) + dev

    param, _ = optimize.curve_fit(
        cosine_model,
        xdata=angles,
        ydata=y,
        bounds=bounds,
    )
    amp, delta, elev, dev = param
    r_squared = _r2_score(y, cosine_model(angles, *param))

    return SSMMetrics(
        amplitude=amp,
        angle=delta,
        elevation=elev,
        displacement=dev,
        r_squared=r_squared,
    )


def _convert_to_polar_coords(
    x: float | np.ndarray, y: float | np.ndarray
) -> Tuple[float | np.ndarray, float | np.ndarray]:
    """
    Convert Cartesian coordinates to polar coordinates.

    Parameters
    ----------
    x : Union[float, np.ndarray]
        x-coordinate(s)
    y : Union[float, np.ndarray]
        y-coordinate(s)

    Returns
    -------
    Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]
        Tuple of (r, theta) in polar coordinates

    Examples
    --------
    >>> x, y = 3, 4
    >>> r, theta = _convert_to_polar_coords(x, y)
    >>> round(r, 2), round(theta, 2)
    (5.0, 53.13)
    """
    r = np.sqrt(x**2 + y**2)
    theta = np.rad2deg(np.arctan2(y, x))
    return r, theta


def _r2_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Calculate the R-squared score between true and predicted values.

    Parameters
    ----------
    y_true : np.ndarray
        True values
    y_pred : np.ndarray
        Predicted values

    Returns
    -------
    float
        R-squared score

    Examples
    --------
    >>> y_true = np.array([3, 4, 5, 2, 1])
    >>> y_pred = np.array([2.5, 4.2, 5.1, 2.2, 1.3])
    >>> round(_r2_score(y_true, y_pred), 2)
    0.96
    """
    ss_total = np.sum((y_true - np.mean(y_true)) ** 2)
    ss_residual = np.sum((y_true - y_pred) ** 2)
    return 1 - (ss_residual / ss_total)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
