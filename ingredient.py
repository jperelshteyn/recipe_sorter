from pymongo import MongoClient
from genre import Genre
from adjective import Adjective


client = MongoClient()
db = client.recipes


class Ingredient:

    def __init__(self, name=None, _id=None):
        assert db.name == 'recipes'
        assert name or _id
        data = None
        if _id:
            if type(_id) is str:
                data = db.ingredients.find_one({'_id': ObjectId(_id)})
            elif type(_id) is ObjectId:
                data = db.ingredients.find_one({'_id': _id})
        elif name:
            name = name.lower()
            data = db.ingredients.find_one({'name': name}) or \
                   db.ingredients.find_one({'name': {'$regex': '.*'+name+'.*'}})
            if not data and len(name.split()) > 1:
                for word in name.split():
                    data = db.ingredients.find_one({'name': name}) or \
                           db.ingredients.find_one({'name': {'$regex': '.*'+name+'.*'}})
                    if data:
                        break
        if data: 
            self.name = data['name']
            self._id = data['_id']
            self.description = data['description']
            self.adjective_ids = data['adjective_ids']
            self.poem_ids = data['poem_ids']
            self.valid = data['valid']
            self.source = data['source']
            self.genre_scores = data['genre_scores']
        else:
            self = None

    def associate_poem(self, poem_id):
        assert type(poem_id) is str or type(poem_id) is ObjectId
        assert db.name == 'recipes'
        data = db.ingredients.find_one({'_id': self._id})
        poem_id = poem_id if type(poem_id) is ObjectId else ObjectId(poem_id)        
        data['poem_ids'] = list(set(data['poem_ids'] + [poem_id]))
        db.ingredients.update({'_id': self._id}, data)
        
    def associate_adjective(self, adjective_id):
        assert type(adjective_id) is str or type(adjective_id) is ObjectId
        assert db.name == 'recipes'
        data = db.ingredients.find_one({'_id': self._id})
        data['adjective_ids'] = list(set(data['adjective_ids'] + [adjective_id]))
        db.ingredients.update({'_id': self._id}, data)

    def get_poem_texts(self):
        assert db.name == 'recipes'
        return [p['text'] for p in db.poems.find({'_id':{'$in': self.poem_ids}})]
    
    def get_adjectives(self):
        adjectives = []
        for adj_id in self.adjective_ids:
            adj = Adjective(_id = adj_id)
            adj.get()
            adjectives.append(adj.word)
            adjectives += adj.synonyms
        return adjectives
    
    def update_genre_scores(self, genre_id):
        adjective_scores = {}
        genre = Genre(_id=genre_id)
        genre.get()
        genre_adjectives = set(genre.adjectives)
        ingredient_adjectives = self.get_adjectives()
        word_freq = 1/len(ingredient_adjectives)
        for ingr_adj in ingredient_adjectives:
            if ingr_adj in genre_adjectives:
                adjective_scores[ingr_adj] = \
                    adjective_scores.get(ingr_adj, 0) + word_freq
        self.genre_scores[genre_id] = adjective_scores
        self.save()
    
    def save(self):
        data = {'name': self.name,
                '_id': self._id,
                'description': self.description,
                'adjective_ids': self.adjective_ids,
                'poem_ids': self.poem_ids,
                'valid': self.valid,
                'source': self.source,
                'genre_scores': self.genre_scores}
        db.ingredients.update({'_id': self._id}, data)