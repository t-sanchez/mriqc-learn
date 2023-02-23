# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#
# Copyright 2021 The NiPreps Developers <nipreps@gmail.com>
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
"""Create a pipeline for nested cross-validation."""
from pkg_resources import resource_filename as pkgrf

from joblib import load
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier as RFC
from sklearn.ensemble import GradientBoostingRegressor
from mriqc_learn.models import preprocess as pp


def load_model():
    return load(pkgrf("mriqc_learn.data", "classifier.joblib"))


def init_pipeline(
    model=None,
    drop_ft=True,
    scale="local",
    remove_noisy=True,
    use_classifier=True,
    groupby="site",
):
    if model is None or model == "rfc":
        model = (
            RFC(
                bootstrap=True,
                class_weight=None,
                criterion="gini",
                max_depth=10,
                max_features="sqrt",
                max_leaf_nodes=None,
                min_impurity_decrease=0.0,
                min_samples_leaf=10,
                min_samples_split=10,
                min_weight_fraction_leaf=0.0,
                n_estimators=400,
                oob_score=True,
            ),
        )
    elif model == "gradient_boosting_regression_l1":
        model = GradientBoostingRegressor(loss="absolute_error")
    else:
        raise RuntimeError(f"Unknown model {model}")
    steps = []
    if drop_ft:
        steps += (
            "drop_ft",
            pp.DropColumns(
                drop=[f"size_{ax}" for ax in "xyz"]
                + [f"spacing_{ax}" for ax in "xyz"]
            ),
        )

    if scale == "global":
        from sklearn.preprocessing import RobustScaler

        steps += [
            # ("drop_site", pp.DropColumns(drop=[groupby])),
            (
                "scale",
                pp.GroupRobustScaler(
                    with_centering=True,
                    with_scaling=True,
                    unit_variance=True,
                    groupby=None,
                ),
            ),
        ]
    elif scale == "local":
        steps += [
            (
                "scale",
                pp.GroupRobustScaler(
                    with_centering=True,
                    with_scaling=True,
                    unit_variance=True,
                    groupby=groupby,
                ),
            ),
            ("site_pred", pp.SiteCorrelationSelector(site_col=groupby)),
        ]
    else:
        if not (scale is None or scale.lower() == "none"):
            raise RuntimeError(f"Unknown scaling option {scale}")
        else:
            if groupby is not None:
                steps += [("drop_site", pp.DropColumns(drop=[groupby]))]
    if remove_noisy:
        steps += [
            (
                "winnow",
                pp.NoiseWinnowFeatSelect(
                    use_classifier=use_classifier, ignore=(groupby,)
                ),
            )
        ]
    if remove_noisy or scale == "local":
        steps += [
            ("print", pp.PrintColumns()),
        ]
    if scale == "local":
        steps += [("drop_site", pp.DropColumns(drop=[groupby]))]

    steps += [
        ("model", model),
    ]
    print(steps)
    return Pipeline(steps)
