from pyppi.data_mining import hprd
from pyppi.data_mining import kegg

"""
A script to utilize the already created parser to parse the already the flat files into a dataframe.
"""

DataPathHPRD = "/home/major/.pyppi/networks/POST_TRANSLATIONAL_MODIFICATIONS.txt"
IDMappingsPathHPRD = "/home/major/.pyppi/networks/HPRD_ID_MAPPINGS.txt"

DataPathKegg = ""
IDMappingsPathKegg = ""

def dataframeHPRD(dataInput, mapping):
	frame = hprd.hprd_to_dataframe(ptm_input=None, mapping_input=None)
	print(type(frame))

def dataframeKegg():
	interactions = kegg.pathways_to_dataframe()
	print(type(interactions))

	# keggToUniprot seems to be broken. Hence takes longer time.

dataInput = open(DataPathHPRD, 'r')
mapping = open(IDMappingsPathHPRD, 'r')



dataframeHPRD(dataInput, mapping)
"""
Similarly we can use KEGG.
"""
# dataframeKegg()

# This library is broken, or is not compatible with Bioservices, as of now. I had raised an issue
# on GitHub regarding the same.