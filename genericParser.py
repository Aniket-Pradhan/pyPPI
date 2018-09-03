import io
import urllib.request

FilePath = "http://bioplex.hms.harvard.edu/data/BioPlex_interactionList_v4a.tsv"

def parseGenericFileData(data, separator = '\t', header = False):

	"""
	Input:
		data - A io.StringIO variable, with data.
		separator - The separator used to separate the data
		header - A boolean, which defines whether the data has a header or not.

	returns:
		A dictionary which consists of the header has keys, and the values specified as it's values.

	"""

	keyWords = []

	if header:
		for i in data.readline().split(separator):
			keyWords.append(i.strip())
	else:
		valueCounter = 1
		for i in range(len(data.readline().split(separator))):
			keyWords.append('value' + str(valueCounter))
			valueCounter += 1
		data.seek(0)

	dataList = {}

	for word in keyWords:
		dataList[word] = []

	for line in data:
		lineData = line.split(separator)
		for i in range(len(keyWords)):
			dataList[keyWords[i]].append(lineData[i].strip())

	return dataList


response = urllib.request.urlopen(FilePath)
data = response.read()
text = io.StringIO(data.decode('utf-8'))

parseGenericFileData(text)