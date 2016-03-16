import json
from pymongo import MongoClient
from ingredient import Ingredient

client = MongoClient()
db = client.recipes


class Recipe:
    
    def __init__(self, name='', 
                 raw_ingredients=[], 
                 ingredients=[], 
                 url='', 
                 source='', 
                 json={}):
        assert type(ingredients) is list
        if json:
            self.name = json['name']
            self.raw_ingredients = json['raw_ingredients']
            self.ingredients = json['ingredients']
            self.url = json['url']
            self.source = json['source']
            self.adjectives = None
        else:
            self.name = name
            self.raw_ingredients = raw_ingredients
            self.ingredients = ingredients
            self.url = url
            self.source = source
            self.adjectives = None
    
    def to_json(self):
        return {'name': self.name,
                'raw_ingredients': self.raw_ingredients,
                'ingredients': self.ingredients, 
                'url': self.url, 
                'source': self.source,
                'adjectives': self.adjectives}

    def extract_ingredients(self):
        global real_ingredients
        self.ingredients = []
        for line in self.raw_ingredients:
            words = [clean_word(w) for w in line.split()]
            two_words = set(words[ind-1] +' '+ word for ind, word in enumerate(words) if ind > 0)
            pure = real_ingredients & two_words
            if not pure:
                pure = real_ingredients & set(words)
            if pure:
                self.ingredients.append(pure.pop())

    def for_web(self):
        json = self.to_json()
        del json['adjectives']
        return json

    def save(self):
        assert db.name == 'recipes'
        data = self.to_json()
        return db.recipes.insert(data)        

    def get_adjectives(self):
        if not self.adjectives:
            self.adjectives = []
            for ingr_name in self.ingredients:
                ingr = Ingredient(ingr_name)
                if hasattr(ingr, '_id'):
                    self.adjectives += ingr.get_adjectives()
        return self.adjectives
    
    def get_genre_scores(self, genres):
        genre_scores = {g: {} for g in genres}
        for ingr_name in self.ingredients:
            ingr = Ingredient(ingr_name)
            if hasattr(ingr, '_id'):
                for genre in ingr.genre_scores:
                    for adj in ingr.genre_scores[genre]:
                        genre_scores[genre][adj] = genre_scores[genre].get(adj, 0) \
                                                    + ingr.genre_scores[genre][adj]
        return genre_scores