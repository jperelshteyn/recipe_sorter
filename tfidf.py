

class TFIDF:
    '''Thanks to https://github.com/hrs for the base code at https://github.com/hrs/python-tf-idf
    '''
    def __init__(self):
        self.weighted = False
        self.documents = []
        self.corpus_dict = {}

    def addDocument(self, doc_name, list_of_words):
        # building a dictionary
        doc_dict = {}
        for w in list_of_words:
            doc_dict[w] = doc_dict.get(w, 0.) + 1.0
            self.corpus_dict[w] = self.corpus_dict.get(w, 0.0) + 1.0

        # normalizing the dictionary
        length = float(len(list_of_words))
        for k in doc_dict:
            doc_dict[k] = doc_dict[k] / length

        # add the normalized document to the corpus
        self.documents.append((doc_name, doc_dict))

    def similarities(self, list_of_words):
        """Returns a dict of all the [docname, similarity_score] pairs relative to a list of words."""

        # building the query dictionary
        query_dict = {}
        for w in list_of_words:
            query_dict[w] = query_dict.get(w, 0.0) + 1.0

        # normalizing the query
        length = float(len(list_of_words))
        for k in query_dict:
            query_dict[k] = query_dict[k] / length

        # computing the list of similarities
        scores = dict()
        common_words = dict()
        for doc in self.documents:
            common_doc_words = set()
            score = 0.0
            doc_dict = doc[1]
            for k in query_dict:
                if k in doc_dict:
                    score += (query_dict[k] / self.corpus_dict[k]) + (doc_dict[k] / self.corpus_dict[k])
                    common_doc_words.add(k)
            scores[doc[0]] = score
            common_words[doc[0]] = list(common_doc_words)
        return scores, common_words
    
    def cross_similarities(self, other):
        all_scores = dict()
        for other_doc in other.documents:
            scores = dict()
            other_doc_name, other_doc_dict = other_doc
            score_sum = 0
            other_doc_word_count = len(other_doc_dict) if len(other_doc_dict) > 0 else 1
            for self_doc in self.documents:
                score = 0
                self_doc_name, self_doc_dict = self_doc
                common_words = set()
                
                for w in self_doc_dict:
                    if w in other_doc_dict:
                        
                        self_tfidf = self_doc_dict[w] / self.corpus_dict[w]
                        other_tfidf = other_doc_dict[w] / other.corpus_dict[w]
                        score += self_tfidf + other_tfidf
                        
                        common_words.add(w)
                
                score_sum += score
                scores[self_doc_name] = {'score': score / other_doc_word_count
                                         , 'words': list(common_words)}
                
            # turn scores into deviations from the mean of all genres
            
#             for self_doc_name in scores:
#                 scores[self_doc_name]['score'] = scores[self_doc_name]['score'] - (score_sum / 3)
            
            all_scores[other_doc_name] = scores
                
        return all_scores