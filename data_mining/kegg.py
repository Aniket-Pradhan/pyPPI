#!/usr/bin/env python

import numpy as np
import pandas as pd
from bioservices import KEGG
from bioservices import UniProt as UniProtMapper
from data_mining.uniprot import UniProt as UniProtReader

from data_mining.tools import make_interaction_frame, process_interactions
from data_mining.tools import write_to_edgelist

"""
Author: Daniel Esposito
Contact: danielce90@gmail.com

This module provides functionality to query pathways by keyword, extract pathways
and parse pathways into a :pd.DataFrame: of interactions with reaction labels.
"""

kegg = KEGG(cache=True)
uniprot_mapper = UniProtMapper(cache=True)
kegg.organism = 'hsa'
kegg.settings.TIMEOUT = 1000
uniprot_mapper.settings.TIMEOUT = 1000
links_to_include = ['PCrel', 'PPrel', 'ECrel', 'GGrel']
types_to_include = ['group', 'gene', 'enzyme']
link_db_swiss_list = 'data/swiss_hsa.list'
link_db_uniprot_list = 'data/uniprot_hsa.list'

motif_pathway_ids = [
    'path:hsa04010',
    'path:hsa04151',
    'path:hsa01521'
]

subtypes_to_exclude = [
    'missing-interaction',
    'indirect-effect',
    'expression',
    'repression',
    'compound',
    'hidden-compound'
]


def reset_kegg():
    """
    Clear the KEGG connection Cache

    :return: None
    """
    kegg.clear_cache()


def reset_uniprot():
    """
    Clear the UniProt connection Cache

    :return: None
    """
    uniprot_mapper.clear_cache()


def download_pathway_ids(organism):
    """
    Query KEGG for a recent list of pathways for an organism.

    :param organism: A KEGG organism code. For example 'hsa'.
    :return: List of pathway ids.
    """
    kegg.organism = organism
    pathways = kegg.pathwayIds
    return pathways


def pathways_to_dataframe(pathway_ids, drop_nan=True, allow_self_edges=False, allow_duplicates=False,
                          min_label_count=None, uniprot=False, trembl=False, merge=True, verbose=False, output=None):
    """
    Download and parse a list of pathway ids into a dataframe of interactions.

    :param pathway_ids: List KEGG pathway accessions. For example ['path:hsa00010'].
    :param drop_nan: Drop entries containing NaN in any column.
    :param allow_self_edges: Remove rows for which source is target.
    :param allow_duplicates: Remove exact copies accross columns.
    :param min_label_count: Remove labels with less than the specified count.
    :param uniprot: Map KEGG_IDs to uniprot.
    :param trembl: Use trembl acc when swissprot in unavailable. Otherwise, kegg_id is considered unmappable.
    :param merge: Merge entries with identical source and target columns during filter.
    :param verbose: True to print progress.
    :param output: File to write dataframe to.
    :return: DataFrame with 'source', 'target' and 'label' columns.
    """
    interaction_frames = [pathway_to_dataframe(p_id, verbose) for p_id in pathway_ids]
    interactions = pd.concat(interaction_frames, ignore_index=True)
    if uniprot:
        interactions = map_to_uniprot(interactions, trembl=trembl)
    interactions = process_interactions(
        interactions=interactions,
        drop_nan=drop_nan,
        allow_self_edges=allow_self_edges,
        allow_duplicates=allow_duplicates,
        exclude_labels=subtypes_to_exclude,
        min_counts=min_label_count,
        merge=merge

    )
    if output:
        write_to_edgelist(interactions, output)
    return interactions


def pathway_to_dataframe(pathway_id, verbose=False):
    """
    Extract protein-protein interaction from KEGG pathway to a pandas DataFrame.
    NOTE: Interactions will be directionless.

    :param: str pathwayId: a valid pathway Id
    :return: DataFrame with columns source, target and label
    """
    res = kegg.parse_kgml_pathway(pathway_id)
    sources = []
    targets = []
    labels = []

    if verbose:
        print("# --- Parsing pathway {} --- #".format(pathway_id))

    for rel in res['relations']:
        id1 = rel['entry1']
        id2 = rel['entry2']
        name1 = res['entries'][[x['id'] for x in res['entries']].index(id1)]['name']
        name2 = res['entries'][[x['id'] for x in res['entries']].index(id2)]['name']
        type1 = res['entries'][[x['id'] for x in res['entries']].index(id1)]['type']
        type2 = res['entries'][[x['id'] for x in res['entries']].index(id2)]['type']
        reaction_type = rel['name'].replace(' ', '-')
        link_type = rel['link']

        if link_type not in links_to_include:
            continue

        if type1 not in types_to_include or type2 not in types_to_include:
            continue

        for a in name1.strip().split(' '):
            for b in name2.strip().split(' '):
                valid_db_a = (kegg.organism in a or 'ec' in a)
                valid_db_b = (kegg.organism in b or 'ec' in b)

                if valid_db_a and valid_db_b:
                    sources.append(a)
                    targets.append(b)
                    labels.append(reaction_type)

    interactions = make_interaction_frame(sources, targets, labels)
    return interactions


def map_to_uniprot(interactions, trembl=False):
    """
    Map KEGG_ID accessions into uniprot. Takes the first if multiple accesssion are found, favoring
    SwissProt over TrEmbl

    :param interactions: DataFrame with columns source, target and label.
    :param trembl: Use Trembl if SwissProt is unavailable.
    :return: DataFrame with columns source, target and label.
    """
    print("Warning: This may take a while if the uniprot cache is empty.")
    filtered_map = {}
    unique_ids = set(a for a in interactions.source.values) | set(b for b in interactions.target.values)
    mapping = uniprot_mapper.mapping(fr='KEGG_ID', to='ACC', query=unique_ids)
    uniprot_reader = UniProtReader()

    for kegg_id, uniprot_ls in mapping.items():
        status_ls = zip(uniprot_ls, [uniprot_reader.get_review_status(acc) for acc in uniprot_ls])
        reviewed = [acc for (acc, status) in status_ls if status.lower() == 'reviewed']
        unreviewed = [acc for (acc, status) in status_ls if status.lower() == 'unreviewed']
        if len(reviewed) > 0:
            if len(reviewed) > 1:
                print('Warning: More that one reviewed acc found for {}: {}'.format(kegg_id, reviewed))
            filtered_map[kegg_id] = reviewed[0]
        else:
            print('Warning: No reviewed acc found for {}.'.format(kegg_id))
            if trembl and len(unreviewed) > 0:
                filtered_map[kegg_id] = unreviewed[0]
            else:
                print('Warning: Could not map {}.'.format(kegg_id))
                filtered_map[kegg_id] = np.NaN

    # Remaining kegg_ids that have not mapped to anything go to np.NaN
    sources = [filtered_map.get(kegg_id, np.NaN) for kegg_id in interactions.source.values]
    targets = [filtered_map.get(kegg_id, np.NaN) for kegg_id in interactions.target.values]
    labels = interactions.label.values
    interactions = make_interaction_frame(sources, targets, labels)
    return interactions
