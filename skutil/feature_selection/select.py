# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import
from collections import namedtuple
import numpy as np
import pandas as pd
from sklearn.utils.validation import check_is_fitted
from .base import _BaseFeatureSelector
from ..utils import validate_is_pd, is_numeric
from ..utils.fixes import _cols_if_none

__all__ = [
    'FeatureDropper',
    'FeatureRetainer',
    'filter_collinearity',
    'MulticollinearityFilterer',
    'NearZeroVarianceFilterer',
    'SparseFeatureDropper'
]


def _validate_cols(cols):
    """Validate that there are at least two columns
    to evaluate. This is used for the MulticollinearityFilterer,
    as it requires there be at least two columns.

    Parameters
    ----------

    cols : None or array_like, shape=(n_features,)
        The columns to evaluate. If ``cols`` is not None
        and the length is less than 2, will raise a 
        ``ValueError``.
    """

    if cols is not None and len(cols) < 2:
        raise ValueError('too few features')


class SparseFeatureDropper(_BaseFeatureSelector):
    """Retains features that are less sparse (NaN) than
    the provided threshold. Useful in situations where matrices
    are too sparse to impute reliably.

    Parameters
    ----------

    cols : array_like, shape=(n_features,), optional (default=None)
        The names of the columns on which to apply the transformation.
        If no column names are provided, the transformer will be ``fit``
        on the entire frame. Note that the transformation will also only
        apply to the specified columns, and any other non-specified
        columns will still be present after transformation.

    threshold : float, optional (default=0.5)
        The threshold of sparsity above which features will be
        deemed "too sparse" and will be dropped.

    as_df : bool, optional (default=True)
        Whether to return a Pandas ``DataFrame`` in the ``transform``
        method. If False, will return a Numpy ``ndarray`` instead. 
        Since most skutil transformers depend on explicitly-named
        ``DataFrame`` features, the ``as_df`` parameter is True by default.


    Examples
    --------

        >>> import numpy as np
        >>> import pandas as pd
        >>>
        >>> nan = np.nan
        >>> X = np.array([
        ...     [1.0, 2.0, nan],
        ...     [2.0, 3.0, nan],
        ...     [3.0, nan, 1.0],
        ...     [4.0, 5.0, nan]
        ... ])
        >>>
        >>> X = pd.DataFrame.from_records(data=X, columns=['a','b','c'])
        >>> dropper = SparseFeatureDropper(threshold=0.5)
        >>> X_transform = dropper.fit_transform(X)
        >>> assert X_transform.shape[1] == 2 # drop out last column


    Attributes
    ----------

    sparsity_ : array_like, shape=(n_features,)
        The array of sparsity values
    
    drop_ : array_like, shape=(n_features,)
        Assigned after calling ``fit``. These are the features that
        are designated as "bad" and will be dropped in the ``transform``
        method.
    """

    def __init__(self, cols=None, threshold=0.5, as_df=True):
        super(SparseFeatureDropper, self).__init__(cols=cols, as_df=as_df)
        self.threshold = threshold

    def fit(self, X, y=None):
        """Fit the transformer.

        Parameters
        ----------

        X : Pandas ``DataFrame``, shape=(n_samples, n_features)
            The Pandas frame to fit. The frame will only
            be fit on the prescribed ``cols`` (see ``__init__``) or
            all of them if ``cols`` is None. Furthermore, ``X`` will
            not be altered in the process of the fit.

        y : None
            Passthrough for ``sklearn.pipeline.Pipeline``. Even
            if explicitly set, will not change behavior of ``fit``.

        Returns
        -------

        self
        """
        X, self.cols = validate_is_pd(X, self.cols)
        thresh = self.threshold

        # validate the threshold
        if not (is_numeric(thresh) and (0.0 <= thresh < 1.0)):
            raise ValueError('thresh must be a float between '
                             '0 (inclusive) and 1. Got %s' % str(thresh))

        # get cols
        cols = _cols_if_none(X, self.cols)

        # assess sparsity
        self.sparsity_ = X[cols].apply(lambda x: x.isnull().sum() / x.shape[0]).values  # numpy array
        mask = self.sparsity_ > thresh  # numpy boolean array
        self.drop_ = X.columns[mask].tolist()
        return self


class FeatureDropper(_BaseFeatureSelector):
    """A very simple class to be used at the beginning or any stage of a 
    Pipeline that will drop the given features from the remainder of the pipe

    Parameters
    ----------

    cols : array_like, shape=(n_features,), optional (default=None)
        The features to drop. Note that ``FeatureDropper`` behaves slightly
        differently from all other ``_BaseFeatureSelector`` classes in the sense
        that it will drop all of the features prescribed in this parameter. However,
        if ``cols`` is None, it will not drop any (which is counter to other classes,
        which will operate on all columns in the absence of an explicit ``cols``
        parameter).

    as_df : bool, optional (default=True)
        Whether to return a Pandas ``DataFrame`` in the ``transform``
        method. If False, will return a Numpy ``ndarray`` instead. 
        Since most skutil transformers depend on explicitly-named
        ``DataFrame`` features, the ``as_df`` parameter is True by default.


    Examples
    --------

        >>> import numpy as np
        >>> import pandas as pd
        >>>
        >>> X = pd.DataFrame.from_records(data=np.random.rand(3,3), columns=['a','b','c'])
        >>> dropper = FeatureDropper(cols=['a','b'])
        >>> X_transform = dropper.fit_transform(X)
        >>> assert X_transform.shape[1] == 1 # drop out first two columns


    Attributes
    ----------
    
    drop_ : array_like, shape=(n_features,)
        Assigned after calling ``fit``. These are the features that
        are designated as "bad" and will be dropped in the ``transform``
        method.
    """

    def __init__(self, cols=None, as_df=True):
        super(FeatureDropper, self).__init__(cols=cols, as_df=as_df)

    def fit(self, X, y=None):
        # check on state of X and cols
        _, self.cols = validate_is_pd(X, self.cols)
        self.drop_ = self.cols
        return self


class FeatureRetainer(_BaseFeatureSelector):
    """A very simple class to be used at the beginning of a Pipeline that will
    only propagate the given features throughout the remainder of the pipe

    Parameters
    ----------
    
    cols : array_like, shape=(n_features,), optional (default=None)
        The names of the columns on which to apply the transformation.
        If no column names are provided, the transformer will be ``fit``
        on the entire frame. Note that the transformation will also only
        apply to the specified columns, and any other non-specified
        columns will still be present after transformation.

    as_df : bool, optional (default=True)
        Whether to return a Pandas ``DataFrame`` in the ``transform``
        method. If False, will return a Numpy ``ndarray`` instead. 
        Since most skutil transformers depend on explicitly-named
        ``DataFrame`` features, the ``as_df`` parameter is True by default.


    Examples
    --------

        >>> import numpy as np
        >>> import pandas as pd
        >>>
        >>> X = pd.DataFrame.from_records(data=np.random.rand(3,3), columns=['a','b','c'])
        >>> dropper = FeatureRetainer(cols=['a','b'])
        >>> X_transform = dropper.fit_transform(X)
        >>> assert X_transform.shape[1] == 2 # retain first two columns


    Attributes
    ----------
    
    drop_ : array_like, shape=(n_features,)
        Assigned after calling ``fit``. These are the features that
        are designated as "bad" and will be dropped in the ``transform``
        method.
    """

    def __init__(self, cols=None, as_df=True):
        super(FeatureRetainer, self).__init__(cols=cols, as_df=as_df)

    def fit(self, X, y=None):
        """Fit the transformer.

        Parameters
        ----------

        X : Pandas ``DataFrame``, shape=(n_samples, n_features)
            The Pandas frame to fit. The frame will only
            be fit on the prescribed ``cols`` (see ``__init__``) or
            all of them if ``cols`` is None. Furthermore, ``X`` will
            not be altered in the process of the fit.

        y : None
            Passthrough for ``sklearn.pipeline.Pipeline``. Even
            if explicitly set, will not change behavior of ``fit``.

        Returns
        -------

        self
        """
        # check on state of X and cols
        X, self.cols = validate_is_pd(X, self.cols)

        # set the drop as those not in cols
        cols = self.cols if self.cols is not None else []
        self.drop_ = X.drop(cols, axis=1).columns.tolist()  # these will be the left overs

        return self

    def transform(self, X):
        """Transform a test matrix given the already-fit transformer.

        Parameters
        ----------

        X : Pandas ``DataFrame``, shape=(n_samples, n_features)
            The Pandas frame to transform. The prescribed
            ``drop_`` columns will be dropped and a copy of
            ``X`` will be returned.


        Returns
        -------

        dropped : Pandas ``DataFrame`` or np.ndarray, shape=(n_samples, n_features)
            The test data with the prescribed ``drop_`` columns removed.
        """
        check_is_fitted(self, 'drop_')
        # check on state of X and cols
        X, _ = validate_is_pd(X, self.cols)  # copy X
        cols = X.columns if self.cols is None else self.cols

        retained = X[cols]  # if not cols, returns all
        return retained if self.as_df else retained.as_matrix()


class _MCFTuple(namedtuple('_MCFTuple', ('feature_x',
                                         'feature_y',
                                         'abs_corr',
                                         'mac'))):
    """A raw namedtuple is very memory efficient as it packs the attributes
    in a struct to get rid of the __dict__ of attributes in particular it
    does not copy the string for the keys on each instance.
    By deriving a namedtuple class just to introduce the __repr__ method we
    would also reintroduce the __dict__ on the instance. By telling the
    Python interpreter that this subclass uses static __slots__ instead of
    dynamic attributes. Furthermore we don't need any additional slot in the
    subclass so we set __slots__ to the empty tuple. """
    __slots__ = tuple()

    def __repr__(self):
        """Simple custom repr to summarize the main info"""
        return "Dropped: {0}, Corr_feature: {1}, abs_corr: {2:.5f}, MAC: {3:.5f}".format(
            self.feature_x,
            self.feature_y,
            self.abs_corr,
            self.mac)


def filter_collinearity(c, threshold):
    """Performs the collinearity filtration for both the
    ``MulticollinearityFilterer`` as well as the ``H2OMulticollinearityFilterer``

    Parameters
    ----------

    c : pandas ``DataFrame``
        The pre-computed correlation matrix. This is expected to be
        a square matrix, and will raise a ``ValueError`` if it's not.

    threshold : float
        The threshold above which to filter features which
        are multicollinear in nature.


    Returns
    -------

    drops : list (string), shape=(n_features,)
        The features that should be dropped

    macor : list (float), shape=(n_features,)
        The mean absolute correlations between
        the features.

    crrz : list (_MCFTuple), shape=(n_features,)
        The tuple containing all information on the
        collinearity metrics between each pairwise
        correlation.
    """
    # ensure symmetric
    if c.shape[0] != c.shape[1]:
        raise ValueError('input dataframe should be symmetrical in dimensions')

    # init drops list
    drops = []
    macor = []  # mean abs corrs
    corrz = []  # the correlations

    # Iterate over each feature
    finished = False
    while not finished:

        # Whenever there's a break, this loop will start over
        for i, nm in enumerate(c.columns):
            this_col = c[nm].drop(nm).sort_values(
                na_position='first')  # gets the column, drops the index of itself, and sorts
            this_col_nms = this_col.index.tolist()
            this_col = np.array(this_col)

            # check if last value is over thresh
            max_cor = this_col[-1]
            if pd.isnull(max_cor) or max_cor < threshold or this_col.shape[0] == 1:
                if i == c.columns.shape[0] - 1:
                    finished = True

                # control passes to next column name or end if finished
                continue

            # otherwise, we know the corr is over the threshold
            # gets the current col, and drops the same row, sorts asc and gets other col
            other_col_nm = this_col_nms[-1]
            that_col = c[other_col_nm].drop(other_col_nm)

            # get the mean absolute correlations of each
            mn_1, mn_2 = np.nanmean(this_col), np.nanmean(that_col)

            # we might get nans?
            # if pd.isnull(mn_1) and pd.isnull(mn_2):
            # this condition is literally impossible, as it would
            # require every corr to be NaN, and it wouldn't have
            # even gotten here without hitting the continue block.
            if pd.isnull(mn_1):
                drop_nm = other_col_nm
            elif pd.isnull(mn_2):
                drop_nm = nm
            else:
                drop_nm = nm if mn_1 > mn_2 else other_col_nm

            # drop the bad col, row
            c.drop(drop_nm, axis=1, inplace=True)
            c.drop(drop_nm, axis=0, inplace=True)

            # add the bad col to drops
            drops.append(drop_nm)
            macor.append(np.maximum(mn_1, mn_2))
            corrz.append(_MCFTuple(
                feature_x=drop_nm,
                feature_y=nm if not nm == drop_nm else other_col_nm,
                abs_corr=max_cor,
                mac=macor[-1]
            ))

            # if we get here, we have to break so the loop will 
            # start over from the first (non-popped) column
            break

            # if not finished, restarts loop, otherwise will exit loop

    # return
    out_tup = (drops, macor, corrz)
    return out_tup


class MulticollinearityFilterer(_BaseFeatureSelector):
    """Filter out features with a correlation greater than the provided threshold.
    When a pair of correlated features is identified, the mean absolute correlation (MAC)
    of each feature is considered, and the feature with the highest MAC is discarded.

    Parameters
    ----------

    cols : array_like, shape=(n_features,), optional (default=None)
        The names of the columns on which to apply the transformation.
        If no column names are provided, the transformer will be ``fit``
        on the entire frame. Note that the transformation will also only
        apply to the specified columns, and any other non-specified
        columns will still be present after transformation.

    threshold : float, optional (default=0.85)
        The threshold above which to filter correlated features

    method : str, optional (default='pearson')
        The method used to compute the correlation,
        one of ['pearson','kendall','spearman'].

    as_df : bool, optional (default=True)
        Whether to return a Pandas ``DataFrame`` in the ``transform``
        method. If False, will return a Numpy ``ndarray`` instead. 
        Since most skutil transformers depend on explicitly-named
        ``DataFrame`` features, the ``as_df`` parameter is True by default.


    Examples
    --------

    The following demonstrates a simple multicollinearity filterer 
    applied to the iris dataset.

        >>> import pandas as pd
        >>> from skutil.utils import load_iris_df
        >>>
        >>> X = load_iris_df(include_tgt=False)
        >>> mcf = MulticollinearityFilterer(threshold=0.85)
        >>> mcf.fit_transform(X).head()
           sepal length (cm)  sepal width (cm)  petal width (cm)
        0                5.1               3.5               0.2
        1                4.9               3.0               0.2
        2                4.7               3.2               0.2
        3                4.6               3.1               0.2
        4                5.0               3.6               0.2


    Attributes
    ----------

    drop_ : array_like, shape=(n_features,)
        Assigned after calling ``fit``. These are the features that
        are designated as "bad" and will be dropped in the ``transform``
        method.

    mean_abs_correlations_ : list, float
        The corresponding mean absolute correlations of each ``drop_`` name

    correlations_ : list of ``_MCFTuple`` instances
        Contains detailed info on multicollinear columns
    """

    def __init__(self, cols=None, threshold=0.85, method='pearson', as_df=True):
        super(MulticollinearityFilterer, self).__init__(cols=cols, as_df=as_df)
        self.threshold = threshold
        self.method = method

    def fit(self, X, y=None):
        """Fit the multicollinearity filterer.

        Parameters
        ----------

        X : Pandas ``DataFrame``, shape=(n_samples, n_features)
            The Pandas frame to fit. The frame will only
            be fit on the prescribed ``cols`` (see ``__init__``) or
            all of them if ``cols`` is None. Furthermore, ``X`` will
            not be altered in the process of the fit.

        y : None
            Passthrough for ``sklearn.pipeline.Pipeline``. Even
            if explicitly set, will not change behavior of ``fit``.

        Returns
        -------

        self
        """
        # check on state of X and cols
        X, self.cols = validate_is_pd(X, self.cols, assert_all_finite=True)
        cols = _cols_if_none(X, self.cols)
        _validate_cols(cols)

        # Generate correlation matrix
        c = X[cols].corr(method=self.method).apply(lambda x: np.abs(x))

        # get drops list
        self.drop_, self.mean_abs_correlations_, self.correlations_ = filter_collinearity(c, self.threshold)

        return self


def _near_zero_variance_ratio(series, ratio):
    """Perform NZV filtering based on a ratio of the
    most common value to the second-most-common value.

    Parameters
    ----------
    
    series : pandas ``Series``, shape=(n_samples,)
        The series on which to compute ``value_counts``.

    Returns
    -------

    ratio_ : float
        The ratio of the most-prevalent value
        to the second-most-prevalent value.

    drop_ : int
        Whether to keep the feature or drop it.
        1 if drop, 0 if keep.
    """
    counts = series.value_counts().sort_values(ascending=False)

    # if there's only one value...
    if counts.shape[0] < 2:
        return np.nan, 1

    ratio_ = counts.iloc[0] / counts.iloc[1]
    drop_ = int(ratio_ >= ratio)

    return ratio_, drop_


class NearZeroVarianceFilterer(_BaseFeatureSelector):
    """Identify and remove any features that have a variance below
    a certain threshold. There are two possible strategies for near-zero
    variance feature selection:

      1) Select features on the basis of the actual variance they
         exhibit. This is only relevant when the features are real
         numbers.

      2) Remove features where the ratio of the frequency of the most
         prevalent value to that of the second-most frequent value is
         large, say 20 or above (Kuhn & Johnson[1]).

    Parameters
    ----------

    cols : array_like, shape=(n_features,), optional (default=None)
        The names of the columns on which to apply the transformation.
        If no column names are provided, the transformer will be ``fit``
        on the entire frame. Note that the transformation will also only
        apply to the specified columns, and any other non-specified
        columns will still be present after transformation.

    threshold : float, optional (default=1e-6)
        The threshold below which to declare "zero variance"

    as_df : bool, optional (default=True)
        Whether to return a Pandas ``DataFrame`` in the ``transform``
        method. If False, will return a Numpy ``ndarray`` instead. 
        Since most skutil transformers depend on explicitly-named
        ``DataFrame`` features, the ``as_df`` parameter is True by default.

    strategy : str, optional (default='variance')
        The strategy by which feature selection should be performed,
        one of ('variance', 'ratio'). If ``strategy`` is 'variance',
        features will be selected based on the amount of variance they
        exhibit; those that are low-variance (below ``threshold``) will
        be removed. If ``strategy`` is 'ratio', features are dropped if the
        most prevalent value is represented at a ratio greater than or equal to
        ``threshold`` to the second-most frequent value. **Note** that if 
        ``strategy`` is 'ratio', ``threshold`` must be greater than 1.


    Examples
    --------

        >>> import pandas as pd
        >>> import numpy as np
        >>> from skutil.feature_selection import NearZeroVarianceFilterer
        >>> 
        >>> X = pd.DataFrame.from_records(data=np.array([
        ...                                 [1,2,3],
        ...                                 [4,5,3],
        ...                                 [6,7,3],
        ...                                 [8,9,3]]), 
        ...                               columns=['a','b','c'])
        >>> filterer = NearZeroVarianceFilterer(threshold=0.05)
        >>> filterer.fit_transform(X)
           a  b
        0  1  2
        1  4  5
        2  6  7
        3  8  9


    Attributes
    ----------

    drop_ : array_like, shape=(n_features,)
        Assigned after calling ``fit``. These are the features that
        are designated as "bad" and will be dropped in the ``transform``
        method.

    var_ : dict
        The dropped columns mapped to their corresponding 
        variances or ratios, depending on the ``strategy``


    References
    ----------

    .. [1] Kuhn, M. & Johnson, K. "Applied Predictive 
           Modeling" (2013). New York, NY: Springer.
    """

    def __init__(self, cols=None, threshold=1e-6, as_df=True, strategy='variance'):
        super(NearZeroVarianceFilterer, self).__init__(cols=cols, as_df=as_df)
        self.threshold = threshold
        self.strategy = strategy

    def fit(self, X, y=None):
        """Fit the transformer.

        Parameters
        ----------

        X : Pandas ``DataFrame``, shape=(n_samples, n_features)
            The Pandas frame to fit. The frame will only
            be fit on the prescribed ``cols`` (see ``__init__``) or
            all of them if ``cols`` is None. Furthermore, ``X`` will
            not be altered in the process of the fit.

        y : None
            Passthrough for ``sklearn.pipeline.Pipeline``. Even
            if explicitly set, will not change behavior of ``fit``.

        Returns
        -------

        self
        """
        # check on state of X and cols
        X, self.cols = validate_is_pd(X, self.cols, assert_all_finite=True)
        cols = _cols_if_none(X, self.cols)

        # validate strategy
        valid_strategies = ('variance', 'ratio')
        if self.strategy not in valid_strategies:
            raise ValueError('strategy must be one of {0}, but got {1}'.format(
                str(valid_strategies), self.strategy))

        if self.strategy == 'variance':
            # if cols is None, applies over everything
            variances = X[cols].var()
            mask = (variances < self.threshold).values
            self.var_ = variances[mask].tolist()
            self.drop_ = variances.index[mask].tolist()
        else:
            # validate ratio
            ratio = self.threshold
            if not ratio > 1.0:
                raise ValueError('when strategy=="ratio", threshold must be greater than 1.0')

            # get a np.array mask
            matrix = np.array([_near_zero_variance_ratio(X[col], ratio) for col in cols])
            drop_mask = matrix[:, 1].astype(np.bool)
            self.drop_ = np.asarray(cols)[drop_mask].tolist()
            self.var_ = dict(zip(self.drop_, matrix[drop_mask, 0].tolist()))  # just retain the variances

        return self
