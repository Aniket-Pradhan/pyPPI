"""
This module contains functions to open and parse the files found in this
directory (data) and generally act as datatypes. This is so other parts of the
program do not become coupled to the data parsing process.
"""

import json
import os
import gzip
import pandas as pd

PATH = os.path.normpath(os.path.join(os.path.expanduser('~'), '.pyppi/'))

hprd_mappings_txt = os.path.join(PATH, 'hprd/HPRD_ID_MAPPINGS.txt')
hprd_ptms_txt = os.path.join(PATH, 'hprd/POST_TRANSLATIONAL_MODIFICATIONS.txt')
uniprot_trembl_dat = os.path.join(PATH, 'uniprot_trembl_human.dat.gz')
uniprot_sprot_dat = os.path.join(PATH, 'uniprot_sprot_human.dat.gz')
swissprot_hsa_path = os.path.join(PATH, 'hsa_swiss-prot.list')
uniprot_hsa_path = os.path.join(PATH, 'hsa_uniprot.list')
default_db_path = os.path.join(PATH, 'pyppi.db')
obo_file = os.path.join(PATH, 'go.obo.gz')
psimi_obo_file = os.path.join(PATH, 'mi.obo.gz')
ipr_names_path = os.path.join(PATH, 'ipr_names.list')
pfam_names_path = os.path.join(PATH, 'Pfam-A.clans.tsv.gz')

ptm_labels_path = os.path.join(PATH, 'labels.tsv')
annotation_extractor_path = os.path.join(PATH, 'annotation_extractor.pkl')
accession_features_path = os.path.join(PATH, 'accession_features.pkl')
ppi_features_path = os.path.join(PATH, 'ppi_features.pkl')

kegg_network_path = os.path.join(PATH, 'networks/kegg_network.tsv')
hprd_network_path = os.path.join(PATH, 'networks/hprd_network.tsv')
pina2_network_path = os.path.join(PATH, 'networks/pina2_network.tsv')
bioplex_network_path = os.path.join(PATH, 'networks/bioplex_network.tsv')
innate_i_network_path = os.path.join(PATH, 'networks/innate_i_network.tsv')
innate_c_network_path = os.path.join(PATH, 'networks/innate_c_network.tsv')
testing_network_path = os.path.join(PATH, 'networks/testing_network.tsv')
training_network_path = os.path.join(PATH, 'networks/training_network.tsv')
full_training_network_path = os.path.join(
    PATH, 'networks/full_training_network.tsv')
interactome_network_path = os.path.join(
    PATH, 'networks/interactome_network.tsv')

bioplex_v4_path = os.path.join(
    PATH, 'networks/BioPlex_interactionList_v4a.tsv')
innate_c_mitab_path = os.path.join(PATH, 'networks/innatedb_curated.mitab.gz')
innate_i_mitab_path = os.path.join(PATH, 'networks/innatedb_imported.mitab.gz')
pina2_sif_path = os.path.join(PATH, 'networks/pina2_homo_sapiens-20140521.sif')

uniprot_record_cache = os.path.join(PATH, 'uprot_records.dict')
uniprot_map_path = os.path.join(PATH, 'accession_map.json')
classifier_path = os.path.join(PATH, 'classifier.pkl')


def line_generator(io_func):
    """
    Decorator to turn a io dealing function into an iterator of file lines.
    :param io_func: function that opens a file with error handling
    """
    def wrapper_func(*args, **kwargs):
        fp = io_func(*args, **kwargs)
        for line in fp:
            if isinstance(line, bytes):
                yield line.decode('utf-8')
            yield line
        fp.close()
    return wrapper_func


@line_generator
def generic_io(file):
    return open(file, 'r')


@line_generator
def uniprot_hsa_list():
    return open(uniprot_hsa_path, 'r')


@line_generator
def swissprot_hsa_list():
    return open(swissprot_hsa_path, 'r')


@line_generator
def uniprot_sprot():
    return gzip.open(uniprot_sprot_dat, 'rt')


@line_generator
def uniprot_trembl():
    return gzip.open(uniprot_trembl_dat, 'rt')


@line_generator
def hprd_ptms():
    return open(hprd_ptms_txt, 'r')


@line_generator
def hprd_id_map():
    return open(hprd_mappings_txt, 'r')


@line_generator
def bioplex_v4():
    return open(bioplex_v4_path, 'r')


@line_generator
def innate_curated():
    return gzip.open(innate_c_mitab_path, 'rt')


@line_generator
def innate_imported():
    return gzip.open(innate_i_mitab_path, 'rt')


@line_generator
def pina2():
    return open(pina2_sif_path, 'r')


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


def ipr_name_map():
    """
    Parse the interpro list into a dictionary. Expects uppercase accessions.
    """
    fp = open(ipr_names_path, 'r')
    ipr_map = {}
    for line in fp:
        xs = line.strip().split("\t")
        term = xs[0].upper()
        descrip = xs[-1].strip()
        ipr_map[term] = descrip
    fp.close()
    return ipr_map


def pfam_name_map():
    """
    Parse the pfam list into a dictionary. Expects uppercase accessions.
    """
    fp = gzip.open(pfam_names_path, 'rt')
    pf_map = {}
    for line in fp:
        xs = line.strip().split("\t")
        term = xs[0].upper()
        descrip = xs[-1].strip()
        pf_map[term] = descrip
    fp.close()
    return pf_map


def get_term_description(term, go_dag, ipr_map, pfam_map):
    term = term.upper()
    if 'IPR' in term:
        return ipr_map[term]
    elif 'PF' in term:
        return pfam_map[term]
    elif "GO" in term:
        return go_dag[term].name
    return None


def load_uniprot_accession_map():
    if not os.path.isfile(uniprot_map_path):
        raise IOError("No mapping file could be found.")
    with open(uniprot_map_path, 'r') as fp:
        return json.load(fp)


def save_uniprot_accession_map(mapping):
    with open(uniprot_map_path, 'w') as fp:
        return json.dump(mapping, fp)


def load_ptm_labels():
    """
    Load the labels in the tsv file into a list.
    """
    if not os.path.isfile(ptm_labels_path):
        raise IOError("No label file could be found.")
    labels = set()
    with open(ptm_labels_path, 'r') as fp:
        for line in fp:
            l = line.strip().replace(' ', '-').capitalize()
            labels.add(l)
    return list(labels)


def save_ptm_labels(labels):
    with open(ptm_labels_path, 'w') as fp:
        for l in labels:
            l = l.replace(' ', '-').capitalize()
            fp.write('{}\n'.format(l))


def load_network_from_path(path):
    from ..base import NULL_VALUES
    return pd.read_csv(path, sep='\t', na_values=NULL_VALUES)


def save_network_to_path(interactions, path):
    import numpy as np
    return interactions.to_csv(path, sep='\t', index=False, na_rep=str(np.NaN))


def read_pd_pickle(path):
    return pd.read_pickle(path)


def pickle_pd_object(obj, path):
    return obj.to_pickle(path)


def load_kegg_to_up():
    mapping = {}
    with open(uniprot_hsa_path, 'rt') as fp:
        for line in fp:
            hsa, up, _ = line.strip().split('\t')
            if mapping.get(hsa.strip()):
                mapping[hsa.strip()] += [up.strip()[3:]]
            else:
                mapping[hsa.strip()] = [up.strip()[3:]]
    return mapping
