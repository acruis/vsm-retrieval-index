"""
Dictionary format:
[
	{
		"67": 5.46,
		"238": 1.23
	}
	{
		"hi": [0, 2, 4.567495861],
		"bye": [3, 1, 0.123584232]
	}
]

[] = list
{} = dict
(no tuples)

VSM lnc vector length of document 238:	dictionary[0]["238"]
Pointer to "retrieval": 				dictionary[1]["retrieval"][0]
Length of postings for "retrieval":		dictionary[1]["retrieval"][1]
idf of "retrieval":   					dictionary[1]["retrieval"][2]
"""

import re
import getopt
import sys
import nltk
import json
from collections import defaultdict
from math import log10, sqrt
from os import listdir
from os.path import isfile, join
from itertools import groupby
try:
	import cPickle as pickle
except:
	import pickle


def load_all_doc_names(docs_dir):
	"""Takes in the document directory path, and lists names of all non-directory
	files from the given path. Returns a list of tuples (file_name, file_path) where
	file_name is the integer conversion of the file name, and the file_path is used
	to actually load the documents for indexing later. The list is sorted by file_name
	(as integers)

	:param docs_dir: The document directory path as a string
	:return: A list of (docID, file_path) tuples, sorted by docID as integers
	"""
	sorted_members = sorted([int(dir_member) for dir_member in listdir(docs_dir)])
	# Additional check for only files in directory
	joined_members = [(dir_member, join(docs_dir, str(dir_member))) for dir_member in sorted_members]
	joined_files = [(member_name, member_path) for member_name, member_path in joined_members if isfile(member_path)]
	return joined_files

def get_doc_tokens(doc_name):
	"""Extracts all tokens in the given document as elements in a list.

	:param doc_name: A tuple containing the docID, and doc_path which is the filepath to the document.
	"""
	docID, doc_path = doc_name
	with open(doc_path) as doc_file:
		doc = doc_file.read()
	# Tokenize to doc content to sentences, then to words.
	sentences = nltk.tokenize.sent_tokenize(doc)
	stemmer = nltk.stem.porter.PorterStemmer()
	return [stemmer.stem(word.lower()) for sentence in sentences for word in nltk.tokenize.word_tokenize(sentence)]	

def index_doc(doc_name, postings_list):
	"""Indexes a single document in the corpus. Makes use of stemming and tokenization.

	:param doc_name: A tuple containing the docID (to be stored as a posting) and doc_path which is the filepath to the document.
	:param postings_list: The postings list, to be updated (mutated) as part of the indexing process.
	"""
	docID, doc_path = doc_name
	words = get_doc_tokens(doc_name)
	# Append doc to postings list.
	# No need to sort the list if we call index_doc in sorted docID order.
	for word in words:
		if word in postings_list:
			postings_list[word].append(docID)
		else:
			postings_list[word] = [docID]

def index_all_docs(docs):
	"""Calls index_doc on all documents in their order in the list passed as argument. Maintaining this order is important as this
	results in sorted postings without having to manually sort the postings for each term at the end of the indexing step.

	:param docs: The list of tuples containing the docID and file path to all documents, sorted by docID
	:return: The inverted index constructed from the given documents
	"""
	postings_list = {}
	document_lengths = {}
	for doc in docs:
		index_doc(doc, postings_list)
	return postings_list

def lnc_from_tf(tf):
	"""Takes tf, and uses lnc to convert it to the term weight. The formula is 1 + log(tf_t,d) where the log base is 10.

	:param tf: The frequency of a term in a document. Should not be 0.
	"""
	return 1 + log10(tf)

def convert_preliminary_postings(preliminary_postings):
	"""Converts postings in the form of [docID1, docID2, docID2, docID3, docID4,...] to [(docID1, 1), (docID2, 2), (docID3, 1), (docID3, 1),...]

	:param preliminary_postings: Ungrouped document ID postings
	"""
	converted_postings = {}
	for word in preliminary_postings:
		docIDs = preliminary_postings[word]
		groupedDocIDs = [(docID, lnc_from_tf(len(list(group)))) for (docID,group) in groupby(docIDs)]
		converted_postings[word] = groupedDocIDs
	return converted_postings

def calculate_doc_lengths(postings_list):
	"""Calculates the VSM lnc vector length for each document, given the postings list.

	:param postings_list: The postings list, which contains (docID, lnc_weight) tuples as term postings.
	"""
	doc_sum_squares = defaultdict(float)
	for term in postings_list:
		for docID, weight in postings_list[term]:
			doc_sum_squares[docID] += pow(weight, 2)
	doc_lengths = {}
	for docID in doc_sum_squares:
		doc_lengths[int(docID)] = sqrt(doc_sum_squares[docID])
	return doc_lengths

def idf_docs(df, big_N):
	"""Calculates the idf of a term. The formula is log(N/df_t) where the log base is 10.

	:param df: The document frequency of the term
	:param big_N: The total number of documents
	"""
	return log10(float(big_N)/df)

def write_postings(postings_list, postings_file_name, big_N):
	"""Given an inverted index, write each term onto disk, while keeping track of the pointer to the start of postings for each term,
	together with the run length of said postings on the file, which will be used to construct the dictionary.

	:param postings_list: The inverted index to be stored
	:param postings_file_name: The name of the postings file
	:return: A dictionary object with term as key and a tuple of (postings pointer, postings run length in the file) as value
	"""
	postings_file = file(postings_file_name, 'w')
	dict_terms = {}
	for term, postings in postings_list.iteritems():
		posting_pointer = postings_file.tell()
		# doc_tuple has the format (docID, lnc_weight)
		postings_file.write(" ".join([",".join([str(docID), "%.9f" % weight]) for docID, weight in postings]))
		write_length = postings_file.tell() - posting_pointer
		postings_file.write("\n")
		dict_terms[term] = (posting_pointer, write_length, idf_docs(len(postings), big_N))
	postings_file.close()
	return dict_terms

def all_doc_IDs(docs):
	"""Extracts docIDs from a list of tuples of docID and path to the document file.

	:param docs: A list of tuples of (docID, path to document file) sorted by docID as integers
	:return: The list of docIDs, still sorted as integers
	"""
	# O(doc_count).
	return [docID for docID, doc_path in docs]

def create_dictionary(document_lengths, dict_terms, dict_file_name):
	"""Combines the list of all document IDs (necessary for computing NOT), and the dictionary itself, to create the dictionary file,
	and then writes the resulting list to the specified file path as a JSON data structure.

	:param document_lengths: A mapping from docID to its VSM vector length.
	:param dict_terms: The dictionary, with term as key and tuple of (postings pointer, postings run length in the file) as value
	:dict_file_name: The file path of the resultant dictionary file
	"""
	dict_file = file(dict_file_name, 'w')
	json.dump([document_lengths, dict_terms], dict_file)
	dict_file.close()


def usage():
	"""Prints the proper format for calling this script."""
	print "usage: " + sys.argv[0] + " -i directory-of-documents -d dictionary-file -p postings-file"

def parse_args():
	"""Attempts to parse command line arguments fed into the script when it was called.
	Notifies the user of the correct format if parsing failed.
	"""
	docs_dir = dict_file = postings_file = None
	try:
		opts, args = getopt.getopt(sys.argv[1:], 'i:d:p:')
	except getopt.GetoptError, err:
		usage()
		sys.exit(2)
	for o, a in opts:
		if o == '-i':
			docs_dir = a
		elif o == '-d':
			dict_file = a
		elif o == '-p':
			postings_file = a
		else:
			assert False, "unhandled option"
	if docs_dir is None or dict_file is None or postings_file is None:
		usage()
		sys.exit(2)
	return docs_dir, dict_file, postings_file

def main():
	"""Constructs the inverted index from all documents in the specified file path, then writes dictionary to the specified dictionary
	file in the command line arguments, and postings to the specified postings file.
	"""
	docs_dir, dict_file, postings_file = parse_args()

	print "Searching for all documents in {0}...".format(docs_dir),
	sys.stdout.flush()
	docs = load_all_doc_names(docs_dir)
	big_N = len(docs)
	print "DONE"

	print "Constructing the inverted index...",
	sys.stdout.flush()
	preliminary_postings_list = index_all_docs(docs)
	postings_list = convert_preliminary_postings(preliminary_postings_list)
	doc_lengths = calculate_doc_lengths(postings_list)
	print "DONE"

	print "Writing postings to {0}...".format(postings_file),
	sys.stdout.flush()
	dict_terms = write_postings(postings_list, postings_file, big_N)
	print "DONE"

	print "Writing dictionary to {0}...".format(dict_file),
	sys.stdout.flush()
	create_dictionary(doc_lengths, dict_terms, dict_file)
	print "DONE"

if __name__ == "__main__":
	main()