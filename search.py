import re
import nltk
import sys
import getopt
import json
import heapq
import time
import math
from itertools import groupby, chain, islice

show_time = True

k = 10  # number of results to return

def sort_relevant_docs(most_relevant_docs):
	"""Given a list of tuples of documents in the format of (score, docID), sort them primarily by decreasing score, and tiebreak by increasing docID,
	and then return up to the first k elements in the list.

	:param most_relevant_docs: A list of tuples of documents and their scores, where each tuple contains (score, docID). 
	"""
	grouped_relevant = groupby(most_relevant_docs, key=lambda score_doc_entry: score_doc_entry[0])
	sorted_relevant = [sorted(equal_score_entries[1], key=lambda equal_score_entry: equal_score_entry[1]) for equal_score_entries in grouped_relevant]
	flattened_relevant = chain.from_iterable(sorted_relevant)
	trimmed_relevant = islice(flattened_relevant, k) # Takes first k elements from the iterable. If there are less than k elements, it stops when the iterable stops
	relevant_docIDs = [str(docID) for score, docID in trimmed_relevant] # Finally, extract the docID from the tuple and convert it to a string to be written to output
	return list(relevant_docIDs)

# heapify an array, O(n) + O(k lg n)
def first_k_most_relevant(doc_scores):
	"""If there are more than k documents containing terms in a query, return the k documents with the highest scores, tiebroken by least docID first.
	If there are less than k documents, return them, sorted by highest scores, and tiebroken by least docID first.

	:param doc_scores: A dictionary of docID to its corresponding document's score.
	"""
	scores = [(-score, docID) for docID, score in doc_scores.iteritems()] # invert the scores so that heappop gives us the smallest score
	heapq.heapify(scores)
	most_relevant_docs = []
	for _ in range(k):
		if not scores:
			break
		most_relevant_docs.append(heapq.heappop(scores))
	if not most_relevant_docs:
		return most_relevant_docs
	# deals with equal-score cases
	kth_score, kth_docID = most_relevant_docs[-1]
	while scores:
		next_score, next_docID = heapq.heappop(scores)
		if next_score == kth_score:
			most_relevant_docs.append((next_score, next_docID))
		else:
			break
	return sort_relevant_docs(most_relevant_docs)

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
		temp = json.load(dict_file)
		doc_length = temp[0]
		dictionary = temp[1]

	# open queries
	postings = file(postings_file)
	output = file(output_file, 'w')

	with open(queries_file) as queries:
		for query in queries:

			query_terms = normalize(query)
			single_term_query = len(query_terms) == 1
			doc_scores = {}

			for term in query_terms:
				doc_scores = update_relevance(doc_scores, dictionary, postings, query_terms, term, single_term_query)

			for key in doc_scores:
				doc_scores[key] /= doc_length[str(key)]

			results = first_k_most_relevant(doc_scores)
			output.write(" ".join(results))
			output.write("\n")

	postings.close()
	output.close()
	after = time.time() * 1000.0
	if show_time: print after-begin


"""
Dictionary
	- Position index
	- Length of postings list in characters
	- Pre-calculated idf

Postings
	- Doc ID
	- Pre-calculated log frequency weight
"""


def normalize(query):
	""" Tokenize and stem

	:param query:
	:return:
	"""
	query_tokens = nltk.word_tokenize(query)
	stemmer = nltk.stem.PorterStemmer()
	query_terms = map(lambda word : stemmer.stem(word.lower()), query_tokens)
	return query_terms


def update_relevance(doc_scores, dictionary, postings_file, query_terms, term, single_term_query):

	postings = read_postings(term, dictionary, postings_file)
	
	for docID_and_tf in postings:

		docID, tf_in_doc = docID_and_tf
		tf_in_query = query_terms.count(term)
		term_idf = dictionary[term][2]

		weight_of_term_in_doc = tf_in_doc
		weight_of_term_in_query = 1 if single_term_query else (1 + math.log10(tf_in_query)) * term_idf

		if docID not in doc_scores:
			doc_scores[docID] = 0

		doc_scores[docID] += weight_of_term_in_doc if single_term_query else weight_of_term_in_doc * weight_of_term_in_query

	return doc_scores


def read_postings(term, dictionary, postings_file):
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
			postings = map(lambda docID_and_tf : docID_and_tf.split(","), postings)
			postings = map(lambda docID_and_tf : [int(docID_and_tf[0]), float(docID_and_tf[1])],postings)
			return postings
		else:
			return []


def main():
	dictionary_file, postings_file, queries_file, output_file = load_args()

	process_queries(dictionary_file, postings_file, queries_file, output_file)

if __name__ == "__main__":
	main()