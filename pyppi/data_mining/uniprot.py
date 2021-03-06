"""
Purpose: Wrapper methods for accessing uniprot records using biopython. See
http://biopython.org/DIST/docs/api/Bio.SwissProt.Record-class.html for more
information about how biopython stores records.
"""

import time
import logging
import pandas as pd

from Bio import SwissProt
from Bio import ExPASy
from bioservices import UniProt as UniProtMapper
from urllib.error import HTTPError
from enum import Enum
from joblib import delayed, Parallel

from ..base.utilities import chunk_list
from ..base.io import uniprot_sprot, uniprot_trembl
from ..database.models import Protein
from ..database.validators import (
    validate_go_annotations,
    validate_boolean, validate_pfam_annotations,
    validate_function, validate_interpro_annotations,
    validate_keywords
)


UNIPROT_ORD_KEY = dict(P=0, Q=1, O=2)
logger = logging.getLogger("pyppi")
http_error_msg = "Unrecoverable HTTPError downloading record for {}."

ERRORS_TO_RETRY = ('503', '504', '408')


# --------------------------------------------------------------------------- #
#
#                    Biopython/SwissProt Download Utilities
#
# --------------------------------------------------------------------------- #


def download_record(accession, verbose=False, wait=5,
                    retries=3, taxon_id=9606):
    """Download a record for a UniProt accession via the UniProt API. 

    The call will retry upon timeout up to the number specified by `retries`.

    Parameters
    ----------
    accession : str
        UniProt accession.

    verbose : bool, optional
        If True, log informational and warning messages to the console.

    wait : int, optional
        Seconds to wait before retrying download.

    retries : int, optional
        Number of times to retry the download if the server returns
        errors `503`, `504` or `408`.

    taxon_id : int, optional
        The taxonomy id to download the accession for. No record is returned
        if the downloaded record does not match this id.

    Returns
    -------
    :class:`Bio.SwissProt.Record`
        A UniProt record instance.
    """

    record = None
    success = False

    try:
        handle = ExPASy.get_sprot_raw(accession)
        record = SwissProt.read(handle)
        success = True

    except HTTPError as httperr:
        if httperr.code in ERRORS_TO_RETRY:
            if verbose:
                logger.exception(http_error_msg.format(accession))
                logger.info("Re-attempting to download.")

            for i in range(retries):
                logger.info("Attempt %s/%s." % (i + 1, retries))
                time.sleep(wait)
                try:
                    handle = ExPASy.get_sprot_raw(accession)
                    record = SwissProt.read(handle)
                    success = True
                except HTTPError:
                    pass
        else:
            if verbose:
                logger.exception(http_error_msg.format(accession))

    except ValueError:
        if verbose:
            logger.exception("No record found for '{}'.".format(accession))
        record = None
        success = False

    if not success:
        if verbose:
            logger.warning(
                "Failed to download record for '{}'".format(accession)
            )
        record = None

    if (not taxon_id is None) and (not record is None) and \
            int(record.taxonomy_id[0]) != taxon_id:
        if verbose:
            logger.warning(
                "Taxonomy IDs do not match for record {}. "
                "Expected '{}' but found '{}'.".format(
                    accession, taxon_id, int(record.taxonomy_id[0])
                )
            )
        record = None

    return record


def download_records(accessions, verbose=False, wait=5,
                     retries=3, taxon_id=9606):
    """Download records for each UniProt accession via the UniProt API. 

    The call will retry upon timeout up to the number specified by `retries`.

    Parameters
    ----------
    accession : str
        UniProt accession.

    verbose : bool, optional
        If True, log informational and warning messages to the console.

    wait : int, optional
        Seconds to wait before retrying download.

    retries : int, optional
        Number of times to retry the download if the server returns
        errors `503`, `504` or `408`.

    taxon_id : int, optional
        The taxonomy id to download the accession for. No record is returned
        if the downloaded record does not match this id.

    Returns
    -------
    `list`
        A list of :class:`Bio.SwissProt.Record` record instances.
    """
    return [
        download_record(a, verbose, wait, retries, taxon_id)
        for a in accessions
    ]


def parallel_download(accessions, backend="multiprocessing",
                      verbose=False, n_jobs=1, wait=5,
                      retries=3, taxon_id=9606):
    """Parallel download records for UniProt accessions via the UniProt API. 

    The call will retry upon timeout up to the number specified by `retries`.

    Parameters
    ----------
    accession : str
        UniProt accession.

    verbose : bool, optional
        If True, log informational and warning messages to the console.

    wait : int, optional
        Seconds to wait before retrying download.

    retries : int, optional
        Number of times to retry the download if the server returns
        errors `503`, `504` or `408`.

    taxon_id : int, optional
        The taxonomy id to download the accession for. No record is returned
        if the downloaded record does not match this id.

    backend : str
        A supported `Joblib` backend. Can be either 'multiprocessing' or 
        'threading'.

    Returns
    -------
    `list`
        A list of :class:`Bio.SwissProt.Record` record instances.
    """
    # Warning: Setting backend to multiprocessing may cause strange errors.
    # This is most likely due to this function not being run in a
    # protected main loop.
    accession_chunks = chunk_list(accessions, n=n_jobs)
    records = Parallel(backend=backend, verbose=verbose, n_jobs=n_jobs)(
        delayed(download_records)(chunk, verbose, wait, retries, taxon_id)
        for chunk in list(accession_chunks)
    )
    return [r for sublist in records for r in sublist]


def serialise_record(record):
    """
    Serialises the fields in a record that can then used to instantiate
    a :class:`Protein` instance.

    Parameters
    ----------
    record : :class:`Bio.SwissProt.Record`
        Record to serialise

    Returns
    -------
    `dict`
        Serialises the fields in a record that can then used to instantiate
        a :class:`Protein` instance.
    """
    if record is None:
        return None
    else:
        uniprot_id = recent_accession(record)
        taxon_id = taxonid(record)
        gene_id = gene_name(record)
        go_mf = go_terms(record, ont="mf")
        go_bp = go_terms(record, ont="bp")
        go_cc = go_terms(record, ont="cc")
        interpro = interpro_terms(record)
        pfam = pfam_terms(record)
        reviewed = True if review_status(record) == 'Reviewed' else False
        keywords_ = keywords(record)
        function_ = function(record)
        last_update_ = last_update(record)
        last_release_ = last_release(record)

        data = dict(
            uniprot_id=uniprot_id, taxon_id=taxon_id, reviewed=reviewed,
            gene_id=gene_id, go_mf=go_mf, go_bp=go_bp, go_cc=go_cc,
            interpro=interpro, pfam=pfam, keywords=keywords_,
            function=function_, last_update=last_update_,
            last_release=last_release_
        )
        return data


def parse_record_into_protein(record, verbose=False):
    """
    Instantiate a :class:`Protein` instance from a 
    :class:`Bio.SwissProt.Record` instance. It will not be saved to the 
    global session or database.

    Parameters
    ----------
    record : :class:`Bio.SwissProt.Record`
        Record to turn into a :class:`Protein` instance.

    verbose : bool, optional
            If True, log informational and warning messages to the console.

    Returns
    -------
    :class:`Protein`
        Instantiated protein instance that has not been saved.
    """

    if record is None:
        return None
    try:
        constuctor_args = serialise_record(record)
        entry = Protein(**constuctor_args)
        return entry
    except:
        if verbose:
            logger.exception("An error occured when trying to parse record.")
        raise

# --------------------------------------------------------------------------- #
#
#                    Biopython/SwissProt Record Parsing
#
# --------------------------------------------------------------------------- #


def batch_map(accessions, fr='ACC+ID', allow_download=False, cache=False,
              session=None, keep_unreviewed=True, match_taxon_id=9606,
              verbose=False):
    """
    Map a list of accessions using the UniProt batch mapping service.

    Parameters
    ----------
    accessions : list
        List of accessions.

    fr : str, optional
        Database to map from. See :class:`bioservices.UniProt`.

    keep_unreviewed : bool, optional
        If True, keep the unreviewed accession in mapping.

    allow_download : bool, optional
        If True, will download records that are missing for any accession
        in `accessions`.

    cache : bool, optional
        If True, `bioservices` cache will be used by 
        :class:`bioservices.UniProt`. Set to `False` to use the most up-to-date
        mappings.

    session : `scoped_session`, optional
        Session instance to save protein instances to if `allow_download`
        is True.

    match_taxon_id : int, optional
        Ignores mappings to or from proteins that do not match this id.

    verbose :  bool, optional
        Log info/warning/error messages to the console.

    Returns
    -------
    `dict`
        A dictionary of mappings from UniProt accessions to the most
        up-to-date UniProt accessions. Dictionary values are lists.
    """
    uniprot_mapper = UniProtMapper(cache=cache)
    filtered_mapping = {}
    mapping = uniprot_mapper.mapping(fr=fr, to='ACC', query=accessions)

    # No data was downloaded, try again a few times.
    if mapping == {}:
        for i in range(0, 4):
            mapping = uniprot_mapper.mapping(
                fr=fr, to='ACC', query=accessions
            )
            if mapping:
                break
            else:
                if verbose:
                    logger.warning(
                        "Could not download map from uniprot server. "
                        "Attempt {}/5. Re-attempt in 3 seconds.".format(i + 2)
                    )
                time.sleep(3)
    if mapping == {}:
        raise ValueError("Could not download map from uniprot server.")

    for fr, to in mapping.items():
        # Make sure any new accessions are in the database
        invalid_to = []
        for accession in to:
            # Check to see if a protein macthing accession and the
            # taxon id exists.
            entry = Protein.get_by_uniprot_id(accession)
            if entry is not None:
                if (match_taxon_id is not None) and entry.taxon_id != match_taxon_id:
                    invalid_to.append(accession)
            else:
                if allow_download:
                    if verbose:
                        logger.info(
                            "Mapping to {}, but entry not found in database. "
                            "Attempting download.".format(accession)
                        )
                    record = download_record(
                        accession, verbose=True, taxon_id=match_taxon_id
                    )
                    protein = parse_record_into_protein(record)
                    if protein is not None:
                        protein.save(session, commit=True)
                    else:
                        if verbose:
                            logger.info(
                                "No valid record for {} was found".format(
                                    accession)
                            )
                        invalid_to.append(accession)
                else:
                    invalid_to.append(accession)

        to = [a for a in to if a not in invalid_to]
        status = [Protein.get_by_uniprot_id(a).reviewed for a in to]
        reviewed = [a for (a, s) in zip(to, status) if s is True]
        unreviewed = [a for (a, s) in zip(to, status) if s is False]
        targets = reviewed
        if keep_unreviewed:
            targets += unreviewed

        targets = list(set(targets))
        if not (match_taxon_id is None):
            taxon_ids = [
                Protein.get_by_uniprot_id(a).taxon_id for a in targets
            ]
            targets = [
                t for (t, taxon_id) in zip(targets, taxon_ids)
                if match_taxon_id == taxon_id
            ]
        filtered_mapping[fr] = list(sorted(targets))
    return filtered_mapping


def __xrefs(db_name, record):
    result = []
    for xref in record.cross_references:
        extdb = xref[0]
        if extdb == db_name:
            result.append(xref[1:])
    return result


def recent_accession(record):
    if not record:
        return None
    return record.accessions[0]


def taxonid(record):
    if not record:
        return None
    data = record.taxonomy_id[0]
    return int(data)


def review_status(record):
    if not record:
        return None
    return record.data_class


def gene_name(record):
    if not record:
        return None
    try:
        data = record.gene_name.split(';')[0].split('=')[-1].split(' ')[0]
    except (KeyError, AssertionError, Exception):
        data = None
    if not data:
        return None
    return data


def go_terms(record, ont):
    if not record:
        return None
    data = __xrefs("GO", record)
    ids = list(map(lambda x: x[0], data))
    names = list(map(lambda x: x[1], data))
    if ont == 'mf':
        ids = [i for (i, n) in zip(ids, names) if n[0] == 'F']
    elif ont == 'bp':
        ids = [i for (i, n) in zip(ids, names) if n[0] == 'P']
    elif ont == 'cc':
        ids = [i for (i, n) in zip(ids, names) if n[0] == 'C']
    else:
        pass
    return ids


def pfam_terms(record):
    if not record:
        return None
    data = __xrefs("Pfam", record)
    return list(map(lambda x: x[0], data))


def interpro_terms(record):
    if not record:
        return None
    data = __xrefs("InterPro", record)
    return list(map(lambda x: x[0], data))


def keywords(record):
    if not record:
        return None
    data = record.keywords
    return data


def organism_code(record):
    if not record:
        return None
    data = record.entry_name
    data = data.split('_')[1]
    return data


def entry_name(record):
    if not record:
        return None
    return record.entry_name


def last_release(record):
    if not record:
        return None
    return int(record.annotation_update[1])


def last_update(record):
    if not record:
        return None
    return record.annotation_update[0]


def synonyms(record):
    if not record:
        return None
    try:
        data = record.gene_name.split(';')[1].split('=')[1].split(
            ', ').split(' ')[0]
    except (KeyError, AssertionError, Exception):
        data = None
    return data


def function(r):
    if r is None:
        return None
    elif not r.comments:
        return None
    else:
        function = [x for x in r.comments if 'FUNCTION:' in x]
        if not function:
            return None
        else:
            return function[0].replace("FUNCTION: ", '')
