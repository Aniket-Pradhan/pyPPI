
"""
This module contains the SQLAlchemy database definitions and related
functions to access and update the database files.
"""
import logging
import numpy as np
from enum import Enum

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import and_

from ..database import Base
from ..database.exceptions import ObjectNotFound, ObjectAlreadyExists
from ..base import SOURCE, TARGET, LABEL, EXPERIMENT_TYPE, PUBMED, NULL_VALUES


logger = logging.getLogger("pyppi")


def _format_annotation(value, upper=True):
    if upper:
        return str(value).strip().upper()
    else:
        return str(value).strip()


def _format_annotations(values, upper=True, allow_duplicates=False):
    if isinstance(values, str):
        values = values.split(',')

    if values is None:
        return None

    if not allow_duplicates:
        return sorted(set(
            _format_annotation(value, upper) for value in values
            if _format_annotation(value, upper)
        ))
    else:
        return sorted(
            _format_annotation(value, upper) for value in values
            if _format_annotation(value, upper)
        )


def _check_annotations(values, dbtype=None):
    values = _format_annotations(values)

    if not dbtype:
        return
    if not values:
        return

    elif dbtype == "GO":
        all_valid = all(["GO:" in v for v in values])
    elif dbtype == "IPR":
        all_valid = all(["IPR" in v for v in values])
    elif dbtype == "PF":
        all_valid = all(["PF" in v for v in values])
    else:
        raise ValueError("Unrecognised dbtype '{}'".format(dbtype))

    if not all_valid:
        raise ValueError(
            "Annotations contain invalid values for database type {}".format(
                dbtype
            )
        )


pmid_interactions = Table(
    'pmid_interactions',
    Base.metadata,
    Column('interaction_id', Integer, ForeignKey('interaction.id')),
    Column('pubmed_id', Integer, ForeignKey('pubmed.id'))
)


psimi_interactions = Table(
    'psimi_interactions',
    Base.metadata,
    Column('interaction_id', Integer, ForeignKey('interaction.id')),
    Column('psimi_id', Integer, ForeignKey('psimi.id'))
)


class Protein(Base):
    """
    Protein schema definition. This is a basic table housing selected fields
    from the uniprot database dump files.
    """
    __tablename__ = "protein"

    id = Column('id', Integer, primary_key=True)
    uniprot_id = Column('uniprot_id', String, nullable=False, unique=True)
    taxon_id = Column('taxon_id', Integer, nullable=False)
    gene_id = Column('gene_id', String)
    _go_mf = Column('go_mf', String)
    _go_cc = Column('go_cc', String)
    _go_bp = Column('go_bp', String)
    _interpro = Column('interpro', String)
    _pfam = Column('pfam', String)
    _keywords = Column("keywords", String)
    reviewed = Column(Boolean, nullable=False)

    interactions = relationship(
        "Interaction", backref="protein",
        primaryjoin="or_("
        "Protein.id==Interaction.source, "
        "Protein.id==Interaction.target"
        ")"
    )

    error_msg = (
        "Expected a comma delimited string, list or set "
        "for argument {arg}. Found {type}."
    )

    def __init__(self, uniprot_id=None, gene_id=None, taxon_id=None,
                 go_mf=None, go_cc=None, go_bp=None, interpro=None, pfam=None,
                 keywords=None, reviewed=None):
        self.uniprot_id = uniprot_id
        self.gene_id = gene_id
        self.taxon_id = taxon_id
        self.go_mf = go_mf
        self.go_cc = go_cc
        self.go_bp = go_bp
        self.interpro = interpro
        self.pfam = pfam
        self.reviewed = reviewed
        self.keywords = keywords

    def __repr__(self):
        string = ("<Protein(id={}, uniprot_id={}, gene_id={}, taxon_id={})>")
        return string.format(
            self.id, self.uniprot_id, self.gene_id, self.taxon_id
        )

    def __eq__(self, other):
        if not isinstance(other, Protein):
            raise TypeError("Cannot compare 'Protein' with '{}'".format(
                type(other).__name__
            ))
        else:
            return all([
                getattr(self, attr.value) == getattr(other, attr.value)
                for attr in Protein.columns()
            ])

    @staticmethod
    def columns():
        class Columns(Enum):
            GO_MF = 'go_mf'
            GO_BP = 'go_bp'
            GO_CC = 'go_cc'
            PFAM = 'pfam'
            INTERPRO = 'interpro'
            REVIEWED = 'reviewed'
            KW = 'keywords'
            TAX = 'taxon_id'
            GENE = 'gene_id'
            UNIPROT = "uniprot_id"
        return Columns

    def save(self, session, commit=False):
        try:
            _check_annotations(self.go_bp, dbtype='GO')
            _check_annotations(self.go_cc, dbtype='GO')
            _check_annotations(self.go_mf, dbtype='GO')

            _check_annotations(self.interpro, dbtype='IPR')
            _check_annotations(self.pfam, dbtype='PF')

            session.add(self)
            if commit:
                session.commit()
                return session.query(Protein).get(self.id)
        except:
            session.rollback()
            raise

    @property
    def go_mf(self):
        return self._go_mf

    @go_mf.setter
    def go_mf(self, value):
        if not value:
            self._go_mf = None
        else:
            self._set_annotation_attribute("_go_mf", value)

    @property
    def go_cc(self):
        return self._go_cc

    @go_cc.setter
    def go_cc(self, value):
        if not value:
            self._go_cc = None
        else:
            self._set_annotation_attribute("_go_cc", value)

    @property
    def go_bp(self):
        return self._go_bp

    @go_bp.setter
    def go_bp(self, value):
        if not value:
            self._go_bp = None
        else:
            self._set_annotation_attribute("_go_bp", value)

    @property
    def interpro(self):
        return self._interpro

    @interpro.setter
    def interpro(self, value):
        if not value:
            self._interpro = None
        else:
            self._set_annotation_attribute("_interpro", value)

    @property
    def pfam(self):
        return self._pfam

    @pfam.setter
    def pfam(self, value):
        if not value:
            self._pfam = None
        else:
            self._set_annotation_attribute("_pfam", value)

    @property
    def keywords(self):
        return self._keywords

    @keywords.setter
    def keywords(self, value):
        if not value:
            self._keywords = None
        else:
            self._set_annotation_attribute("_keywords", value)
            if self._keywords is not None:
                self._keywords = ','.join(
                    [x.capitalize() for x in self.keywords.split(',')]
                )

    def _set_annotation_attribute(self, attr, value):
        accepted_types = [
            isinstance(value, str),
            isinstance(value, list),
            isinstance(value, set)
        ]
        if not any(accepted_types):
            raise TypeError(self.error_msg.format(
                arg=attr, type=type(value).__name__))
        else:
            value = _format_annotations(value, allow_duplicates=False)
            if not value:
                value = None
            else:
                setattr(self, attr, ','.join(value))


class Interaction(Base):
    """
    PPI schema definition. This is a basic table containing fields
    such as computed features.
    """
    __tablename__ = "interaction"

    id = Column(Integer, primary_key=True)
    is_training = Column(Boolean, nullable=False)
    is_holdout = Column(Boolean, nullable=False)
    is_interactome = Column(Boolean, nullable=False)
    taxon_id = Column('taxon_id', Integer, nullable=False)
    source = Column('source', ForeignKey("protein.id"), nullable=False)
    target = Column('target', ForeignKey("protein.id"), nullable=False)
    combined = Column('combined', String, unique=True, nullable=False)
    _label = Column('label', String)
    _keywords = Column('keywords', String)
    _go_mf = Column('go_mf', String)
    _go_cc = Column('go_cc', String)
    _go_bp = Column('go_bp', String)
    _ulca_go_mf = Column('ulca_go_mf', String)
    _ulca_go_cc = Column('ulca_go_cc', String)
    _ulca_go_bp = Column('ulca_go_bp', String)
    _interpro = Column('interpro', String)
    _pfam = Column('pfam', String)

    # M-2-O relationships
    # Modifying these will cause an auto-flush, hence the object must
    # be saved first or Integrity errors may be raised.
    pmid = relationship(
        "Pubmed", backref="pmid_interactions",
        uselist=True, secondary=pmid_interactions, lazy='joined'
    )
    psimi = relationship(
        "Psimi", backref="psimi_interactions",
        uselist=True, secondary=psimi_interactions, lazy='joined'
    )

    def __init__(self, source=None, target=None, is_interactome=None,
                 is_training=None, is_holdout=None, label=None,
                 go_mf=None, go_cc=None, go_bp=None,
                 ulca_go_mf=None, ulca_go_cc=None, ulca_go_bp=None,
                 interpro=None, pfam=None, keywords=None):

        if isinstance(source, Protein):
            self.source = source.id
        else:
            self.source = source

        if isinstance(target, Protein):
            self.target = target.id
        else:
            self.target = target

        self.label = label
        self.is_training = is_training
        self.is_holdout = is_holdout
        self.is_interactome = is_interactome

        # Create a unique identifier using the uniprot ids combined
        # into a string. This column is unique causing a contraint
        # failure if an (B, A) is added when (A, B) already exists.
        self.combined = ','.join(sorted(
            [str(self.source), str(self.target)]
        ))

        self.keywords = keywords
        self.go_mf = go_mf
        self.go_cc = go_cc
        self.go_bp = go_bp
        self.ulca_go_mf = ulca_go_mf
        self.ulca_go_cc = ulca_go_cc
        self.ulca_go_bp = ulca_go_bp
        self.interpro = interpro
        self.pfam = pfam

    def __repr__(self):
        string = (
            "<Interaction("
            "id={}, source={}, target={}, training={}, holdout={}, "
            "interactome={}, label={}"
            ")"
            ">"
        )
        return string.format(
            self.id, self.source, self.target,
            self.is_training, self.is_holdout,
            self.is_interactome, self.label
        )

    def __eq__(self, other):
        if not isinstance(other, Interaction):
            raise TypeError("Cannot compare 'Interaction' with '{}'".format(
                type(other).__name__
            ))
        else:
            return all([
                getattr(self, attr.value) == getattr(other, attr.value)
                for attr in Interaction.columns()
            ])

    @staticmethod
    def columns():
        class Columns(Enum):
            ID = 'id'
            GO_MF = 'go_mf'
            GO_BP = 'go_bp'
            GO_CC = 'go_cc'
            ULCA_GO_MF = 'ulca_go_mf'
            ULCA_GO_BP = 'ulca_go_bp'
            ULCA_GO_CC = 'ulca_go_cc'
            PFAM = 'pfam'
            INTERPRO = 'interpro'
            LABEL = 'label'
            KW = 'keywords'
            COMBINED = 'combined'
            IS_HOLDOUT = 'is_holdout'
            IS_TRAINING = 'is_training'
            IS_INTERACTOME = 'is_interactome'
        return Columns

    def save(self, session, commit=False):
        try:
            _check_annotations(self.go_bp, dbtype='GO')
            _check_annotations(self.go_cc, dbtype='GO')
            _check_annotations(self.go_mf, dbtype='GO')

            _check_annotations(self.ulca_go_bp, dbtype='GO')
            _check_annotations(self.ulca_go_cc, dbtype='GO')
            _check_annotations(self.ulca_go_mf, dbtype='GO')

            _check_annotations(self.interpro, dbtype='IPR')
            _check_annotations(self.pfam, dbtype='PF')

            if (self.is_holdout or self.is_training) and not self.label:
                raise ValueError("Training/Holdout interaction must be labled")

            if not isinstance(self.is_holdout, bool):
                raise TypeError(
                    "is_holdout must be a boolean value."
                )
            if not isinstance(self.is_training, bool):
                raise TypeError(
                    "is_training must be a boolean value."
                )
            if not isinstance(self.is_interactome, bool):
                raise TypeError(
                    "is_interactome must be a boolean value."
                )

            invalid_source = self.source is None or session.query(
                Protein).get(self.source) is None
            invalid_target = self.target is None or session.query(
                Protein).get(self.target) is None

            if self.source and invalid_source:
                raise ObjectNotFound(
                    "Source '{}' does not exist in table 'protein'.".format(
                        self.source
                    )
                )
            if self.target and invalid_target:
                raise ObjectNotFound(
                    "Target '{}' does not exist in table 'protein'.".format(
                        self.target
                    )
                )

            if (self.source is not None) and (self.target is not None):
                source = session.query(Protein).get(self.source)
                target = session.query(Protein).get(self.target)
                query_set = session.query(Interaction).filter(
                    Interaction.combined == ','.join(sorted(
                        [str(self.source), str(self.target)]
                    ))
                )
                already_exists = query_set.count() != 0

                existing_interaction = None
                if query_set.count() > 0:
                    existing_interaction = query_set[0]

                if already_exists and \
                        existing_interaction.id != self.id:
                    raise ObjectAlreadyExists(
                        "Interaction ({}, {}) already exists.".format(
                            source.uniprot_id, target.uniprot_id)
                    )
                same_taxon = (source.taxon_id == target.taxon_id)
                if not same_taxon:
                    raise ValueError(
                        "Source and target must have the same taxonomy ids. "
                    )
                else:
                    self.taxon_id = source.taxon_id

            # Re-compute combined incase source/target changes
            self.combined = ','.join(sorted(
                [str(self.source), str(self.target)]
            ))

            session.add(self)
            if commit:
                session.commit()
                return session.query(Interaction).get(self.id)

        except:
            session.rollback()
            raise

    @property
    def keywords(self):
        return self._keywords

    @keywords.setter
    def keywords(self, value):
        if not value:
            self._keywords = None
        else:
            self._set_annotation_attribute("_keywords", value)
            if self._keywords is not None:
                self._keywords = ','.join(
                    [x.capitalize() for x in self.keywords.split(',')]
                )

    @property
    def go_mf(self):
        return self._go_mf

    @go_mf.setter
    def go_mf(self, value):
        if not value:
            self._go_mf = None
        else:
            self._set_annotation_attribute("_go_mf", value)

    @property
    def go_cc(self):
        return self._go_cc

    @go_cc.setter
    def go_cc(self, value):
        if not value:
            self._go_cc = None
        else:
            self._set_annotation_attribute("_go_cc", value)

    @property
    def go_bp(self):
        return self._go_bp

    @go_bp.setter
    def go_bp(self, value):
        if not value:
            self._go_bp = None
        else:
            self._set_annotation_attribute("_go_bp", value)

    @property
    def ulca_go_mf(self):
        return self._ulca_go_mf

    @ulca_go_mf.setter
    def ulca_go_mf(self, value):
        if not value:
            self._ulca_go_mf = None
        else:
            self._set_annotation_attribute("_ulca_go_mf", value)

    @property
    def ulca_go_cc(self):
        return self._ulca_go_cc

    @ulca_go_cc.setter
    def ulca_go_cc(self, value):
        if not value:
            self._ulca_go_cc = None
        else:
            self._set_annotation_attribute("_ulca_go_cc", value)

    @property
    def ulca_go_bp(self):
        return self._ulca_go_bp

    @ulca_go_bp.setter
    def ulca_go_bp(self, value):
        if not value:
            self._ulca_go_bp = None
        else:
            self._set_annotation_attribute("_ulca_go_bp", value)

    @property
    def interpro(self):
        return self._interpro

    @interpro.setter
    def interpro(self, value):
        if not value:
            self._interpro = None
        else:
            self._set_annotation_attribute("_interpro", value)

    @property
    def pfam(self):
        return self._pfam

    @pfam.setter
    def pfam(self, value):
        if not value:
            self._pfam = None
        else:
            self._set_annotation_attribute("_pfam", value)

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, value):
        valid_types = [
            isinstance(value, str),
            isinstance(value, list),
            isinstance(value, set),
            isinstance(value, type(None))
        ]
        if not any(valid_types):
            raise TypeError("Label must be list, str, set or None.")

        if isinstance(value, list) or isinstance(value, set):
            value = [v for v in value if v is not None]

        if not value:
            self._label = None
        else:
            if isinstance(value, str):
                value = value.split(',')
            labels = ','.join(sorted(
                set(v.strip().capitalize() for v in value if v.strip())
            ))
            if not labels:
                self._label = None
            else:
                self._label = labels

    @property
    def labels_as_list(self):
        if self.label is None:
            return []
        else:
            return list(sorted(self.label.split(',')))

    def add_label(self, label):
        if not isinstance(label, str):
            raise TypeError("Label must be string.")
        elif not label.strip():
            raise ValueError("Cannot set empty label.")
        elif len(label.split(',')) > 1:
            raise ValueError("Cannot set multiple labels at once.")
        else:
            if self.label is None:
                self.label = label
            else:
                self.label = self.label.split(',') + [label]
            return self

    def remove_label(self, label):
        if self.label is None:
            return self
        if not isinstance(label, str):
            raise TypeError("Label must be string")
        elif not label.strip():
            raise ValueError("Cannot remove empty label.")
        elif len(label.split(',')) > 1:
            raise ValueError("Cannot remove multiple labels at once.")
        else:
            labels = self.label.split(',')
            label = label.strip().capitalize()
            try:
                labels.remove(label)
                self.label = labels
            except ValueError:
                return self

    def add_pmid_reference(self, pmid):
        if not isinstance(pmid, Pubmed):
            raise TypeError("pmid must be an instance of Pubmed.")
        if not (pmid in self.pmid):
            self.pmid.append(pmid)
        return self

    def remove_pmid_reference(self, pmid):
        if not isinstance(pmid, Pubmed):
            raise TypeError("pmid must be an instance of Pubmed.")
        if pmid in self.pmid:
            self.pmid.remove(pmid)
        return self

    def add_psimi_reference(self, psimi):
        if not isinstance(psimi, Psimi):
            raise TypeError("psimi must be an instance of Psimi.")
        if not (psimi in self.psimi):
            self.psimi.append(psimi)
        return self

    def remove_psimi_reference(self, psimi):
        if not isinstance(psimi, Psimi):
            raise TypeError("psimi must be an instance of Psimi.")
        if psimi in self.psimi:
            self.psimi.remove(psimi)
        return self

    def _set_annotation_attribute(self, attr, value):
        accepted_types = [
            isinstance(value, str),
            isinstance(value, list),
            isinstance(value, set)
        ]
        if not any(accepted_types):
            raise TypeError(self.error_msg.format(
                arg=attr, type=type(value).__name__)
            )
        else:
            value = _format_annotations(value, allow_duplicates=True)
            if not value:
                value = None
            else:
                setattr(self, attr, ','.join(value))

    @property
    def has_missing_data(self):
        return any([
            not bool(self.go_bp),
            not bool(self.go_mf),
            not bool(self.go_cc),
            not bool(self.ulca_go_bp),
            not bool(self.ulca_go_cc),
            not bool(self.ulca_go_mf),
            not bool(self.keywords),
            not bool(self.interpro),
            not bool(self.pfam)
        ])


class Pubmed(Base):
    """
    Pubmed schema definition. This is a basic table containing fields
    relating to a pubmed id. It simple has an integer column, auto-generated
    and auto-incremented, and an `accession` column representing the pubmed
    accession number.
    """
    __tablename__ = "pubmed"

    id = Column(Integer, primary_key=True)
    accession = Column(String, unique=True, nullable=False)

    def __init__(self, accession):
        self.accession = accession

    def __repr__(self):
        string = "<Pubmed(id={}, accession={})>"
        return string.format(
            self.id, self.accession
        )

    def save(self, session, commit=False):
        try:
            session.add(self)
            if commit:
                session.commit()
        except:
            session.rollback()
            raise

    @property
    def interactions(self):
        return self.pmid_interactions


class Psimi(Base):
    """
    PSIMI ontology schema definition. This is a basic table containing fields
    relating to a psi-mi experiment type term. It simple has an integer column, 
    auto-generated and auto-incremented, an `accession` column representing 
    the psi-mi accession number and `description` column, which is a plain
    text description.
    """
    __tablename__ = "psimi"

    id = Column(Integer, primary_key=True)
    accession = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=False)

    def __init__(self, accession, description):
        self.accession = accession
        self.description = description

    def __repr__(self):
        string = "<Psimi(id={}, accession={}, desc={})>"
        return string.format(
            self.id, self.accession, self.description
        )

    def save(self, session, commit=False):
        try:
            session.add(self)
            if commit:
                session.commit()
        except:
            session.rollback()
            raise

    @property
    def interactions(self):
        return self.psimi_interactions


# ---- Helper for M2M linking
def construct_m2m(session, entry, pmids, psimis, replace=False):
    pmid_objs = set() if replace else set(entry.pmid)
    if pmids not in NULL_VALUES:
        for pmid in pmids.split(','):
            pmid_obj = session.query(Pubmed).filter_by(
                accession=pmid
            ).first()
            if pmid_obj is not None:
                pmid_objs.add(pmid_obj)
        entry.pmid = list(pmid_objs)

    if psimis not in NULL_VALUES:
        psimi_objs = set() if replace else set(entry.psimi)
        for psimi in psimis.split(','):
            psimi_obj = session.query(Psimi).filter_by(
                accession=psimi
            ).first()
            if psimi_obj is not None:
                psimi_objs.add(psimi_obj)
        entry.psimi = list(psimi_objs)

    return entry


def create_interactions(session, df, existing_interactions, protein_map,
                        is_training, is_holdout, is_interactome,
                        feature_map, replace_label=False,
                        replace_m2m=False, name=None):
    zipped = zip(
        df[SOURCE],
        df[TARGET],
        df[LABEL],
        df[PUBMED],
        df[EXPERIMENT_TYPE]
    )
    for (uniprot_a, uniprot_b, label, pmids, psimis) in zipped:
        if str(label) in NULL_VALUES:
            label = None
        entry = existing_interactions.get((uniprot_a, uniprot_b), None)
        if entry is None:
            entry = Interaction(
                source=protein_map[uniprot_a].id,
                target=protein_map[uniprot_b].id,
                is_training=is_training,
                is_holdout=is_holdout,
                is_interactome=is_interactome,
                label=label,
                **feature_map[(uniprot_a, uniprot_b)]
            )
        else:
            if is_training:
                entry.is_training = is_training
            if is_holdout:
                entry.is_holdout = is_holdout
            if is_interactome:
                entry.is_interactome = is_interactome

            if not is_interactome and label is not None:
                if replace_label:
                    entry.label = label.split(',')
                else:
                    new_labels = label.split(',')
                    entry.label = entry.labels_as_list + new_labels

            for key, value in feature_map[(uniprot_a, uniprot_b)].items():
                setattr(entry, key, value)

        # The following block constructs the Many-to-Many relationships
        # between the Interaction table and the Pubmed/Psimi tables.
        entry.save(session, commit=False)
        entry = construct_m2m(
            session, entry, pmids, psimis, replace=replace_m2m
        )
        existing_interactions[(uniprot_a, uniprot_b)] = entry

    return existing_interactions
