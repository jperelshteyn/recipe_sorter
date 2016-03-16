import json
from pymongo import MongoClient
from adjective import Adjective


client = MongoClient()
db = client.recipes


class Genre:

    def __init__(self, name=None, adjective_ids=[], scraped_adjectives=None, _id=None):
        self.name = name
        self.scraped_adjectives = scraped_adjectives
        self.adjective_ids = adjective_ids
        self._id = _id
    
    def to_json(self):
        return {'_id': self._id,
                'name': self.name,
                'adjective_ids': self.adjective_ids,
                'scraped_adjectives': self.scraped_adjectives}
    
    def for_web(self):
        json = self.to_json
        del json['adjective_ids']
        del json['scraped_adjectives']
        return json
    
    def get(self):
        assert db.name == 'recipes'
        sarg = {'_id': self._id} if self._id else {'name': self.name}
        data = db.genres.find_one(sarg)
        if data:
            self._id = data['_id']
            self.name = data['name']
            self.adjective_ids = data['adjective_ids']
            self.scraped_adjectives = data['scraped_adjectives']
            
    def save(self):
        assert db.name == 'recipes'
        data = self.to_json()
        if self._id:
            db.genres.update({'_id': self._id}, data)
        else:
            self._id = db.genres.insert(data)
        return self._id
    
    def associate_adjective(self, adjective_id):
        assert type(adjective_id) is ObjectId
        self.adjective_ids = list(set(self.adjective_ids + [adjective_id]))
        self.save()
        
    def get_adjectives(self):
        adjectives = set(self.scraped_adjectives)
        for adj_id in self.adjective_ids:
            adj = Adjective(_id = adj_id)
            adj.get()
            adjectives.update(set(adj.synonyms))
        return adjectives