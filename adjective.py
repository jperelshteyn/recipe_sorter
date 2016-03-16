from pymongo import MongoClient


client = MongoClient()
db = client.recipes

class Adjective:

    def __init__(self, word='', _id=None):
        assert type(word) is str or type(word) is unicode
        self.word = word.lower()
        self.synonyms = []
        self._id = _id

    def get(self):
        assert db.name == 'recipes'
        data = None
        if self._id:
            data = db.adjectives.find_one({'_id': self._id})
        else:
            data = db.adjectives.find_one({'word': self.word})
        if data:
            self._id = data['_id']
            self.synonyms = data['synonyms']

    def add_synonyms(self, synonyms):
        assert type(synonyms) is list or type(synonyms) is set
        self.synonyms = list(set(self.synonyms) | set(synonyms))

    def save(self):
        assert db.name == 'recipes'
        data = {'word': self.word, 'synonyms': self.synonyms}
        if self._id:
            data['_id'] = self._id
            db.adjectives.update({'_id': self._id}, data)
            return self._id
        else:
            return db.adjectives.insert(data)