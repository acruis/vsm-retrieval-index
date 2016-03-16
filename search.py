import re
import nltk
import sys
import getopt
import json
import heapq
import time
import math

show_time = True

"""
Dictionary
	- Position index
	- Length of postings list in characters
	- Pre-calculated idf

Postings
	- Doc ID
	- Pre-calculated log frequency weight
"""

k = 10  # number of results to return


# heapify an array, O(n) + O(k lg n)
def first_k_most_relevant():
	exit


def usage():
	"""Prints the proper format for calling this script."""
	print "usage: " + sys.argv[0] + " -d dictionary-file -p postings-file -q file-of-queries -o output-file-of-results"


def load_args():
	"""Attempts to parse command line arguments fed into the script when it was called.
	Notifies the user of the correct format if parsing failed.
	"""
	dictionary_file = postings_file = queries_file = output_file = None

	try:
		opts, args = getopt.getopt(sys.argv[1:], 'd:p:q:o:')
	except getopt.GetoptError, err:
		usage()
		sys.exit(2)
	for o, a in opts:
		if o == '-d':
			dictionary_file = a
		elif o == '-p':
			postings_file = a
		elif o == '-q':
			queries_file = a
		elif o == '-o':
			output_file = a
		else:
			assert False, "unhandled option"
	if dictionary_file is None or postings_file is None or queries_file is None or output_file is None:
		usage()
		sys.exit(2)
	return dictionary_file, postings_file, queries_file, output_file


def process_queries(dictionary_file, postings_file, queries_file, output_file):
	# load dictionary
	begin = time.time() * 1000.0
	with open(dictionary_file) as dict_file:
		dictionary = json.load(dict_file)

	# open queries
	postings = file(postings_file)
	output = file(output_file, 'w')

	with open(queries_file) as queries:
		for query in queries:

			query_terms = normalize(query)
			doc_scores = {}
			for term in query_terms:
				doc_scores = update_relevance(doc_scores, term, dictionary, postings)

			results = first_k_most_relevant(doc_scores)
			output.write(" ".join(results))

	postings.close()
	output.close()
	after = time.time() * 1000.0
	if show_time: print after-begin


def normalize(query):
	""" Tokenize and stem

	:param query:
	:return:
	"""
	query_tokens = nltk.word_tokenize(query)
	stemmer = nltk.stem.PorterStemmer()
	query_terms = map(lambda word : stemmer.stem(word), query_tokens)
	return query_terms


def update_relevance(doc_scores, term, dictionary, postings_file):
	postings = read_postings_of_term(term, dictionary, postings_file)
	for docID_and_tf_weight in postings:
		docID = docID_and_tf_weight[0]
		tf_weight = docID_and_tf_weight[1]

		if docID not in doc_scores:
			doc_scores[docID] = 0

		doc_scores[docID] += calculate_score()

	return doc_scores


def calculate_score():
	return 0


def read_postings_of_term(term, dictionary, postings_file):
		""" Gets own postings list from file and stores it in its attribute. For search token nodes only.

		:param term:
		:param postings_file: File object referencing the file containing the complete set of postings lists.
		:param dictionary: Dictionary that takes search token keys, and returns a tuple of pointer and length.
			The pointer points to the starting point of the search token's postings list in the file.
			The length refers to the length of the search token's postings list in bytes.
		"""

		if term in dictionary:
			term_pointer = dictionary[term][0]
			postings_length = dictionary[term][1]
			postings_file.seek(term_pointer)
			postings = postings_file.read(postings_length).split()
			postings = map(lambda docID_and_tf_weight : docID_and_tf_weight.split(","), postings)
			postings = map(lambda docID_and_tf_weight : [int(docID_and_tf_weight[0]), float(docID_and_tf_weight[1])],postings)
			return postings


def main():
	dictionary_file, postings_file, queries_file, output_file = load_args()

	process_queries(dictionary_file, postings_file, queries_file, output_file)

if __name__ == "__main__":
	main()