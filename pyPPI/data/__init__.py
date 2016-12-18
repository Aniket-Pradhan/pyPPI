#!/usr/bin/env python

"""
This module contains functions to open and parse the files found in this
directory (data) and generally act as datatypes. This is so other parts of the
program do not become coupled to the data parsing process.
"""

import os
import pandas as pd
from goatools import obo_parser

PATH, _ = os.path.split(__file__)

hprd_mappings_txt = os.path.join(PATH, 'hprd/HPRD_ID_MAPPINGS.txt')
hprd_ptms_txt = os.path.join(PATH, 'hprd/POST_TRANSLATIONAL_MODIFICATIONS.txt')
uniprot_trembl_dat = os.path.join(PATH, 'uniprot_trembl_human.dat')
uniprot_sprot_dat = os.path.join(PATH, 'uniprot_sprot_human.dat')
swissprot_hsa_path = os.path.join(PATH, 'swiss_hsa.list')
uniprot_hsa_path = os.path.join(PATH, 'uniprot_hsa.list')
obo_file = os.path.join(PATH, 'gene_ontology.1_2.obo')
ipr_snames_path = os.path.join(PATH, 'ipr_short_names.dat')
ipr_lnames_path = os.path.join(PATH, 'ipr_names.dat')
pfam_names_path = os.path.join(PATH, 'pfam_names.tsv')
ptm_labels_path = os.path.join(PATH, 'labels.tsv')
accession_features_path = os.path.join(PATH, 'accession_features.pkl')
ppi_features_path = os.path.join(PATH, 'ppi_features.pkl')
kegg_network_path = os.path.join(PATH, 'networks/kegg_network.tsv')
hprd_network_path = os.path.join(PATH, 'networks/hprd_network.tsv')
pina2_network_path = os.path.join(PATH, 'networks/pina2_network.tsv')
bioplex_network_path = os.path.join(PATH, 'networks/bioplex_network.tsv')
innate_i_network_path = os.path.join(PATH, 'networks/innate_i_network.tsv')
innate_c_network_path = os.path.join(PATH, 'networks/innate_c_network.tsv')
training_network_path = os.path.join(PATH, 'networks/training_network.tsv')
testing_network_path = os.path.join(PATH, 'networks/testing_network.tsv')
interactome_network_path = os.path.join(PATH,
                                        'networks/interactome_network.tsv')
bioplex_v2_path = os.path.join(PATH, 'networks/BioPlex_interactionList_v2.tsv')
bioplex_v4_path = os.path.join(PATH, 'networks/BioPlex_interactionList_v4.tsv')
innate_c_mitab_path = os.path.join(PATH, 'networks/innatedb_curated.mitab')
innate_i_mitab_path = os.path.join(PATH, 'networks/innatedb_imported.mitab')
pina2_sif_path = os.path.join(PATH, 'networks/PINA2_Homo_sapiens-20140521.sif')


def line_generator(io_func):
    """
    Decorator to turn a io dealing function into an iterator of file lines.
    :param io_func: function that opens a file with error handling
    """
    def wrapper_func():
        fp = io_func()
        for line in fp:
            yield line
        fp.close()
    return wrapper_func


@line_generator
def generic_io(file):
    try:
        return open(file, 'r')
    except IOError as e:
        print(e)


@line_generator
def uniprot_hsa_list():
    try:
        return open(uniprot_hsa_path, 'r')
    except IOError as e:
        print(e)


@line_generator
def swissprot_hsa_list():
    try:
        return open(swissprot_hsa_path, 'r')
    except IOError as e:
        print(e)


@line_generator
def uniprot_sprot():
    try:
        return open(uniprot_sprot_dat, 'r')
    except IOError as e:
        print(e)


@line_generator
def uniprot_trembl():
    try:
        return open(uniprot_trembl_dat, 'r')
    except IOError as e:
        print(e)


@line_generator
def hprd_ptms():
    try:
        return open(hprd_ptms_txt, 'r')
    except IOError as e:
        print(e)


@line_generator
def hprd_id_map():
    try:
        return open(hprd_mappings_txt, 'r')
    except IOError as e:
        print(e)


@line_generator
def bioplex_v2():
    try:
        return open(bioplex_v2_path, 'r')
    except IOError as e:
        print(e)


@line_generator
def bioplex_v4():
    try:
        return open(bioplex_v4_path, 'r')
    except IOError as e:
        print(e)


@line_generator
def innate_curated():
    try:
        return open(innate_c_mitab_path, 'r')
    except IOError as e:
        print(e)


@line_generator
def innate_imported():
    try:
        return open(innate_i_mitab_path, 'r')
    except IOError as e:
        print(e)


@line_generator
def pina2():
    try:
        return open(pina2_sif_path, 'r')
    except IOError as e:
        print(e)


def hsa_swissprot_map():
    hsa_sp = {}
    for line in swissprot_hsa_list():
        xs = line.strip().split('\t')
        uprot = xs[0].split(':')[1]
        hsa = xs[1].split(':')[1]
        hsa_sp[hsa] = uprot
    return hsa_sp


def hsa_uniprot_map():
    hsa_sp = {}
    for line in uniprot_hsa_list():
        xs = line.strip().split('\t')
        uprot = xs[0].split(':')[1]
        hsa = xs[1].split(':')[1]
        hsa_sp[hsa] = uprot
    return hsa_sp


def load_go_dag(optional_attrs=None):
    """Load an obo file into a goatools GODag object"""
    default = optional_attrs or ['defn', 'is_a', 'relationship', 'part_of']
    return obo_parser.GODag(obo_file, optional_attrs=default)


def ipr_name_map(lowercase_keys=False, short_names=True):
    """
    Parse the interpro list into a dictionary.
    """
    file = ipr_snames_path if short_names else ipr_lnames_path
    fp = open(file, 'r')
    ipr_map = {}
    for line in fp:
        if lowercase_keys:
            xs = line.strip().lower().split("\t")
        else:
            xs = line.strip().upper().split("\t")
        term = xs[0].upper()
        descrip = xs[1]
        ipr_map[term] = descrip
    fp.close()
    return ipr_map


def pfam_name_map(lowercase_keys=False):
    """
    Parse the pfam list into a dictionary.
    """
    fp = open(pfam_names_path, 'r')
    pf_map = {}
    for line in fp:
        if lowercase_keys:
            xs = line.strip().lower().split("\t")
        else:
            xs = line.strip().upper().split("\t")
        term = xs[0].upper()
        descrip = xs[-1]
        pf_map[term] = descrip
    fp.close()
    return pf_map


def ptm_labels():
    """
    Load the labels in the tsv file into a list.
    """
    labels = set()
    with open(ptm_labels_path, 'r') as fp:
        for line in fp:
            l = line.strip().replace(' ', '-').lower()
            labels.add(l)
    return list(labels)


def load_training_network():
    return pd.read_csv(training_network_path, sep='\t')


def load_testing_network():
    return pd.read_csv(testing_network_path, sep='\t')


def load_interactome_network():
    return pd.read_csv(testing_network_path, sep='\t')


def load_accession_features():
    return pd.read_pickle(accession_features_path)


def load_ppi_features():
    return pd.read_pickle(ppi_features_path)
