#!/usr/bin/python

"""
This sub-module contains scoring functions for multi-label indicator arrays
and a class for housing statistics which wraps around a pandas dataframe.
"""

import numpy as np
import pandas as pd


class MultilabelScorer(object):
    """
    Simple helper class to wrap over a binary metric in sci-kit to
    enable support for simple multi-label scoring.
    """
    def __init__(self, sklearn_binary_metric):
        self.scorer = sklearn_binary_metric

    def __call__(self, y, y_pred, **kwargs):
        scores = []
        y = np.asarray(y)
        y_pred = np.asarray(y_pred)
        n_classes = y.shape[1]
        for i in range(n_classes):
            score = self.scorer(y[:, i], y_pred[:, i], **kwargs)
            scores.append(score)
        return np.asarray(scores)


class Statistics(object):
    """
    Simple class to house statistics from learning. Essentially a
    wrapper around a dataframe  with three columns:
    ['Label', 'Data', 'Statistic'].
    """

    def __init__(self):
        self._label_col = 'Label'
        self._data_col = 'Data'
        self._statistic_col = 'Statistic'
        self._columns = [self._label_col, self._data_col, self._statistic_col]
        self._statistics = pd.DataFrame(columns=self._columns)

    def __repr__(self):
        return str(self.__dict__)

    def __str__(self):
        return self.__repr__()

    def frame(self):
        return self._statistics

    def labels(self):
        return np.unique(self._statistics[self._label_col].values)

    def columns(self):
        return self._columns

    def statistic_types(self):
        return set(self._statistics[self._statistic_col].values)

    def update_statistics(self, label, s_type, data):
        _df = pd.DataFrame(columns=self._columns)
        _df[self._label_col] = [label]
        _df[self._data_col] = [data]
        _df[self._statistic_col] = [s_type]
        print(_df)
        self._statistics = pd.concat(
            [self._statistics, _df], ignore_index=True
        )
        return self

    def get_statistic(self, label, s_type):
        assert label in self.labels()
        assert s_type in self.statistic_types()
        _df = self._statistics[self._statistics[self._label_col] == label]
        statistic = (_df[_df[self._statistic_col] == s_type])[self._data_col]
        mu = np.mean(statistic.values)
        std = np.std(statistic.values)
        return mu, std

    def print_statistics(self, label):
        print("{}:".format(label))
        for statistic in self.statistic_types():
            mu, std = self.get_statistic(label, statistic)
            print("\t{}:\t{:.6}\t{:.6}".format(statistic, mu, std))

    def merge(self, other):
        assert self.columns() == other.columns()
        _df = pd.concat([self.frame(), other.frame()], ignore_index=True)
        assert _df.size == self.frame().size + other.frame().size
        self._statistics = _df
        return self

    def write(self, fp, mode='a'):
        labels = self.labels()
        if len(self._statistics) == 0:
            raise ValueError("Nothing to write.")
        if isinstance(fp, str):
            fp = open(fp, mode)
        max_word_len = max([len(l) for l in labels])
        for l in sorted(labels):
            fp.write('{}'.format(l) + ' ' * (max_word_len-len(l))
                     + '\tmean' + ' '*6 + '\tstd\n')
            for s in sorted(self.statistic_types()):
                mu, std = self.get_statistic(l, s)
                fp.write('\t{}:'.format(s) + ' ' *
                         (max_word_len - len(s) - 5) +
                         '\t{:.6f}\t{:.6f}\n'.format(mu, std))
            fp.write('\n')
        return
