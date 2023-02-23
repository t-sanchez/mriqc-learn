# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#
# Copyright 2022 The NiPreps Developers <nipreps@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# We support and encourage derived works from this project, please read
# about our expectations at
#
#     https://www.nipreps.org/community/licensing/
#
# STATEMENT OF CHANGES: This file is derived from the sources of scikit-learn 0.19,
# which is licensed under the BSD 3-clause.
# This file contains extensions and modifications to the original code.
from itertools import combinations

import numpy as np
from sklearn.model_selection import BaseCrossValidator
from sklearn.utils.validation import _num_samples, indexable


class LeavePSitesOut(BaseCrossValidator):
    """
    A LeavePGroupsOut split ensuring all folds have positive and
    negative samples.

    """

    def __init__(
        self,
        n_groups,
        colname="site",
        robust=True,
        shuffle=False,
        random_state=None,
    ):
        self.n_groups = n_groups
        self.colname = colname
        self.robust = robust
        self.shuffle = shuffle
        self.random_state = random_state

    def _iter_test_masks(self, X, y=None, groups=None, return_key=False):

        if groups is None:
            if X is not None and self.colname in X.columns:
                groups = X[[self.colname]].values.squeeze()
            else:
                raise ValueError("The 'groups' parameter should not be None.")

        _groups = set(groups)

        if len(_groups) <= self.n_groups:
            raise ValueError(
                f"Cannot extract {self.n_groups} "
                f"if the total number of groups is {len(_groups)}"
            )

        if y is not None and hasattr(y, "values"):
            y = y.values

        # if self.shuffle:
        #     from sklearn.utils import check_random_state
        #     import pandas as pd

        #     n_samples = _num_samples(X)
        #     indices = np.arange(n_samples)
        #     check_random_state(self.random_state).shuffle(indices)
        #     X = X.loc[indices] if isinstance(X, pd.DataFrame) else X[indices]
        #     y = y.loc[indices] if isinstance(y, pd.DataFrame) else y[indices]
        #     groups = (
        #         groups.loc[indices]
        #         if isinstance(groups, pd.DataFrame)
        #         else groups[indices]
        #     )
        for test_set_label in combinations(_groups, self.n_groups):
            test_index = np.zeros(_num_samples(X), dtype=bool)

            for label in test_set_label:
                test_index[groups == label] = True

            if self.robust is True and y is not None:
                targets = np.squeeze(y[test_index])
                if np.unique(targets, axis=0).shape[0] == 1:
                    continue

            if len(test_set_label) == 1:
                test_set_label = test_set_label[0]
            yield test_index if not return_key else (
                test_set_label,
                test_index,
            )

    def get_n_splits(self, X=None, y=None, groups=None):
        """Returns the number of splitting iterations in the cross-validator
        Parameters
        ----------
        X : object
            Always ignored, exists for compatibility.
        y : object
            Always ignored, exists for compatibility.
        groups : array-like of shape (n_samples,)
            Group labels for the samples used while splitting the dataset into
            train/test set. This 'groups' parameter must always be specified to
            calculate the number of splits, though the other parameters can be
            omitted.
        Returns
        -------
        n_splits : int
            Returns the number of splitting iterations in the cross-validator.
        """
        return len(list(self._iter_test_masks(X, y, groups)))

    def split(self, X, y=None, groups=None, return_key=False):
        X, y, groups = indexable(X, y, groups)
        indices = np.arange(_num_samples(X))

        for labels, test_index in self._iter_test_masks(
            X, y, groups, return_key=True
        ):
            train_index = indices[np.logical_not(test_index)]
            test_index = indices[test_index]
            from sklearn.utils import check_random_state

            if self.shuffle:
                check_random_state(self.random_state).shuffle(train_index)
                check_random_state(self.random_state).shuffle(test_index)
            # print(train_index, test_index)
            yield (
                (train_index, test_index)
                if not return_key
                else (train_index, (labels, test_index))
            )
