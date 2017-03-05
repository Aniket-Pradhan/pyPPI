#!/usr/bin/env python

"""
This script runs the bootstrap kfold validation experiments as used in
the publication.
"""

import numpy as np

from pyPPI.data import load_network_from_path, load_ptm_labels
from pyPPI.data import testing_network_path, training_network_path

from pyPPI.models.binary_relevance import BinaryRelevance
from pyPPI.models import make_classifier, supported_estimators
from pyPPI.model_selection.scoring import MultilabelScorer, Statistics
from pyPPI.model_selection.experiment import KFoldExperiment, Bootstrap
from pyPPI.model_selection.sampling import IterativeStratifiedKFold

from pyPPI.data_mining.features import AnnotationExtractor
from pyPPI.data_mining.uniprot import UniProt, get_active_instance
from pyPPI.data_mining.tools import xy_from_interaction_frame

from sklearn.base import clone
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import RandomizedSearchCV
from sklearn.metrics import f1_score, precision_score
from sklearn.metrics import recall_score, make_scorer


if __name__ == '__main__':
    n_jobs = 3
    n_iter = 3
    n_splits = 5
    induce = True
    verbose = True
    use_feature_cache = True

    print("Loading data...")
    uniprot = get_active_instance(verbose=verbose)
    data_types = UniProt.data_types()
    selection = [
        data_types.GO_MF.value,
        data_types.GO_BP.value,
        data_types.GO_CC.value,
        data_types.INTERPRO.value,
        data_types.PFAM.value
    ]
    labels = load_ptm_labels()
    annotation_ex = AnnotationExtractor(
        induce=induce,
        selection=selection,
        n_jobs=n_jobs,
        verbose=verbose,
        cache=use_feature_cache
    )
    training = load_network_from_path(training_network_path)
    testing = load_network_from_path(testing_network_path)

    # Get the features into X, and multilabel y indicator format
    print("Preparing training and testing data...")
    mlb = MultiLabelBinarizer(classes=labels)
    X_train_ppis, y_train = xy_from_interaction_frame(training)
    X_test_ppis, y_test = xy_from_interaction_frame(testing)
    mlb.fit(y_train)

    X_train = annotation_ex.transform(X_train_ppis)
    X_test = annotation_ex.transform(X_test_ppis)
    y_train = mlb.transform(y_train)
    y_test = mlb.transform(y_test)

    # Make the estimators and BR classifier
    print("Making classifier...")
    param_distribution = {
        'C': np.arange(0.01, 10.01, step=0.01),
        'penalty': ['l1', 'l2']
    }
    random_cv = RandomizedSearchCV(
        cv=3,
        n_iter=60,
        param_distributions=param_distribution,
        estimator=make_classifier('LogisticRegression'),
        scoring=make_scorer(f1_score, greater_is_better=True)
    )
    estimators = [
        Pipeline(
            [('vectorizer', CountVectorizer(binary=False)),
             ('clf', clone(random_cv))]
        )
        for l in labels
    ]
    clf = BinaryRelevance(estimators, n_jobs=n_jobs)

    # Make the bootstrap and KFoldExperiments
    print("Setting up experiments...")
    cv = IterativeStratifiedKFold(n_splits=n_splits, shuffle=True)
    kf = KFoldExperiment(
        estimator=clf, cv=cv, n_jobs=n_splits,
        verbose=verbose, backend='threading'
    )
    bootstrap = Bootstrap(
        kfold_experiemnt=kf, n_iter=n_iter, n_jobs=n_jobs,
        verbose=verbose, backend='multiprocessing'
    )

    # Fit the data
    print("Fitting training data...")
    bootstrap.fit(X_train, y_train)

    # Make the scoring functions
    print("Evaluating performance...")
    f1_scorer = MultilabelScorer(f1_score)
    recall_scorer = MultilabelScorer(recall_score)
    precision_scorer = MultilabelScorer(precision_score)
    score_funcs = [recall_scorer, precision_scorer, f1_scorer]
    thresholds = [0.5, 0.5, 0.5]

    # Evaluate performance
    validation_data = bootstrap.validation_scores(
        X_train, y_train, score_funcs, thresholds, True, False
    )
    testing_data = bootstrap.held_out_scores(
        X_test, y_test, score_funcs, thresholds, True, False
    )

    # Put everything into a dataframe
    print("Saving statistics dataframes...")
    validation_stats = Statistics.statistics_from_data(
        data=validation_data,
        statistics_names=['Recall', 'Precision', 'F1'],
        classes=mlb.classes_,
        return_df=True
    )
    # Put everything into a dataframe
    testing_stats = Statistics.statistics_from_data(
        data=testing_data,
        statistics_names=['Recall', 'Precision', 'F1'],
        classes=mlb.classes_,
        return_df=True
    )
    validation_stats.to_csv(
        'results/validation_stats.csv', sep='\t', index=False
    )
    testing_stats.to_csv(
        'results/testing_stats.csv', sep='\t', index=False
    )
