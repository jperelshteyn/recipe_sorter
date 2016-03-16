from pymongo import MongoClient

client = MongoClient()
db = client.recipes


class Poem:

    def __init__(self, title='', author='', text='', is_professional=True, _id=None):
        self.title = title.lower()
        self.author = author.lower()
        self.text = text
        self.is_professional = is_professional
        self._id = _id 

    def get(self):
        assert db.name == 'recipes'
        assert (self.title and self.author) or self._id
        data = None
        if self.title and self.author:
            data = db.poems.find_one({'title': self.title, 'author': self.author})
        elif self._id:
            data = db.poems.find_one({'_id': self._id})
        if data:
            self.title = data['title']
            self.author = data['author']
            self.text = data['text']
            self.is_professional = data['professional']
            self._id = data['_id']

    def _is_duplicate(self):
        data = db.poems.find_one({'title': self.title, 'author': self.author})
        return data != None

    def save(self):
        assert db.name == 'recipes'
        assert self.title and self.author and self.text
        data = {'title': self.title, 
                'author': self.author,
                'text': self.text,
                'professional': self.is_professional}
        if self._id:
            db.poems.update({'_id': self._id}, data)
        elif not self._is_duplicate():
            self._id = db.poems.insert(data)
        return self._id