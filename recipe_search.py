from recipe_classes import *
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer


def get_ingredient_names(valid_only=True):
    '''
    Load up global db_ingredients list with ingredients saved in database
    '''
    global db_ingredients
    if len(db_ingredients) == 0:
        sarg = {'valid': True} if valid_only else {}
        for c in db.ingredients.find(sarg):
            db_ingredients.append(c['name'])
    return db_ingredients

real_ingredients = set(n.lower() for n in get_ingredient_names())

def extract_ingredients(messy_ingredients):
    '''
    Check for valid ingredients in the raw ingredient list and return valid ones

    Args:
        messy_ingredients(list) -- raw ingredients from API
    '''
    global real_ingredients
    pure_ingredients = []
    for line in messy_ingredients:
        words = [w.lower() for w in line.split()]
        two_words = set(words[ind-1] +' '+ word for ind, word in enumerate(words) if ind > 0)
        pure = real_ingredients & two_words
        if not pure:
            pure = real_ingredients & set(words)
        if pure:
            pure_ingredients.append(pure.pop())
    return pure_ingredients


def query_edamam(q, limit=50):
    '''
    Query edamam for recipes

    Args:
        q(str) -- query text argument
        limit(int) -- max number of recipes
    '''
    recipes = []
    try:
        cred = 'app_id=' + config['edamam_id'] + '&app_key=' + config['edamam_key']
        r_string = "https://api.edamam.com/search?{}&{}&{}".format("q=" + q, cred, "to=" + str(limit))
        r = requests.get(r_string)
        for h in r.json()['hits']:
            name = h['recipe']['label']
            ingredients = [i['food'] for i in h['recipe']['ingredients']]
            url = h['recipe']['url']
            source = 'edamam'
            recipe = Recipe(name, ingredients, ingredients, url, source)
            recipes.append(recipe)
    except e as Exception:
        print 'edamam error', e
        traceback.print_exc()
    finally:
        return recipes


def query_food2fork(q, limit=50):
    '''
    Query food2fork for recipes

    Args:
        q(str) -- query text argument
        limit(int) -- max number of recipes
    '''
    key = 'key=' + config['food2fork_key']
    page = 1
    more = True
    recipes = []
    try:
        while more:
            get_url = "http://food2fork.com/api/search?{}&{}&{}".format("q=" + q,"page=" + str(page), key)
            resp = requests.get(get_url)
            page += 1
            more = resp.json()['count'] == 30 and resp.status_code == 200
            for r in resp.json()['recipes']:
                get_url = "http://food2fork.com/api/get?rId={}&{}".format(r['recipe_id'], key)
                resp2 = requests.get(get_url)
                data = resp2.json()
                name = data['recipe']['title']
                raw_ingredients = data['recipe']['ingredients']
                url = data['recipe']['source_url']
                source = 'food2fork'
                recipe = Recipe(name, raw_ingredients, [], url, source)
                recipe.extract_ingredients()
                recipes.append(recipe)
                if len(recipes) == limit:
                    return recipes
    except e as Exception:
        print 'food2fork error', e
        traceback.print_exc()
    finally:
        return recipes


def query_yummly(q, ingredients, limit=50):
    '''
    Query yummly for recipes

    Args:
        q(str) -- query text argument
        ingredients(list) -- inredients to query
        limit(int) -- max number of recipes
    '''  
    ingr_list = ingredients.split(',') if ingredients else []
    recipes = []    
    try:
        cred = '_app_id=' + config['yummly_id'] + '&_app_key=' + config['yummly_key']
        ingr_string = ('allowedIngredient[]=' + '&allowedIngredient[]='.join(ingr_list)) if ingr_list else ''
        text_sarg = 'q=' + q if q else ''
        max_result = 'maxResult=' + str(limit)
        r_string = "http://api.yummly.com/v1/api/recipes?{}&{}&{}&{}"\
                        .format(text_sarg, ingr_string, cred, max_result)
        r = requests.get(r_string)
        for m in r.json()['matches']:
            name = m['recipeName']
            raw_ingredients = m['ingredients']
            url = 'http://www.yummly.com/recipe/external/' + m['id']
            source = 'yummly'
            recipe = Recipe(name, raw_ingredients, [], url, source)
            recipe.extract_ingredients()
            recipes.append(recipe)
    except e as Exception:
        print 'yummly error', e
        traceback.print_exc()
    finally:
        return recipes


def search(ingredients_csv, text_sarg, test=True, jsonify=False, limit=111):
    '''
    Search all recipe APIs

    Args:
        ingredients_csv(list) -- inredients to query
        text_sarg(str) -- text to query
        test(bool) -- get results from db instead of API
        jsonify(bool) -- output in JSON format
        limit(int) -- total limit for number of recipes
    '''     
    recipes = []
    count = 0
    if test:
        for r in db.recipes.find():
            count += 1
            if count < limit:
                recipes.append(Recipe(json=r))
    else:
        edamam_sarg = text_sarg+','+ingredients_csv if text_sarg and ingredients_csv \
                                                    else text_sarg or ingredients_csv
        food2fork_sarg = text_sarg+'+'+ingredients_csv if text_sarg and ingredients_csv \
                                                        else text_sarg or ingredients_csv
        recipes += query_edamam(edamam_sarg)
        recipes += query_food2fork(food2fork_sarg)
        recipes += query_yummly(text_sarg, ingredients_csv)
    for recipe in recipes:
        recipe.get_adjectives()
    if jsonify:
        recipes = [r.to_json() for r in recipes]
    return recipes


def cluster_recipes(recipes, num_clusters = 4, max_words = 3):
    '''
    Cluster recipes using K-Means based on their adjective tfidf
    '''
    data = []
    taste_adjectives = {a['term'] for a in db.food_adjectives.find()}
    for recipe in recipes:
        data.append(' '.join(recipe.adjectives))
    tfidf_vectorizer = TfidfVectorizer(max_df=0.8, max_features=200000,
                                       min_df=0.2, stop_words='english',
                                       use_idf=True)
    tfidf_matrix = tfidf_vectorizer.fit_transform(data)
    km = KMeans(n_clusters=num_clusters)
    km.fit(tfidf_matrix)
    terms = tfidf_vectorizer.get_feature_names()
    order_centroids = km.cluster_centers_.argsort()[:, ::-1]
    clusters = km.labels_.tolist()
    clustered_recipes = zip(clusters, recipes)
    cluster_names = {}
    for i in range(num_clusters):
        words = []            
        for ind in order_centroids[i]:
            if len(words) < 2:
                words.append(terms[ind])
            elif len(words) <= max_words and terms[ind] in taste_adjectives:
                words.append(terms[ind])
        cluster_names[i] = ', '.join(words)
    clustered_recipes = [{'cluster_id': cr[0],
                          'recipe': cr[1].for_web()} 
                         for cr in clustered_recipes]
    clusters = [{'id': c[0], 'name': c[1]} for c in cluster_names.items()]
    return clusters, clustered_recipes


def sort_score_recipes(recipes):
    '''
    Score each recipe based on its adjective distance from each genre
    '''
    genres = get_genre_names()
    scored_recipes = []
    recipe_id = 0
    for recipe in recipes:
        recipe_id += 1
        sort_scores = {}
        common_adjectives = {}
        genre_scores = recipe.get_genre_scores(genres)
        ingr_count = len(recipe.ingredients)
        for genre in genre_scores:
            sort_scores[genre] = sum(score for _, score in genre_scores[genre].items()) / ingr_count
            common_adjectives[genre] = [adjective for adjective, _ in genre_scores[genre].items()]
        sort_scores['Silence'] = -sum(sort_scores.values())
        scored_recipes.append({'recipe_id': recipe_id,
                               'recipe': recipe.for_web(), 
                               'sort_scores': sort_scores,
                               'common_adjectives': common_adjectives})
    return scored_recipes


def get_genre_names():
    return ['Rock', 'Jazz', 'Classical']
