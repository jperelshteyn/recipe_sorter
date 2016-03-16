from adjective import Adjective
from genre import Genre
from ingredient import Ingredient
from poem import Poem 
from recipe import Recipe
from bs4 import BeautifulSoup
from nltk import wordnet
from unicodedata import normalize
from selenium import webdriver
from textblob import TextBlob as tb
import cnfg
import json
from pymongo import MongoClient


# Global variables
client = MongoClient()
db = client.recipes
config = cnfg.load(".recipe_config")
stop_chars = {',', '.', '?', '!', ';', ':', "'", '"', ')', '('}
db_ingredients = []


def scrape_food_adjectives():
    chromedriver = "/Users/jperelshteyn/Downloads/chromedriver"
    environ["webdriver.chrome.driver"] = chromedriver
    driver = webdriver.Chrome(chromedriver)
    driver.get('http://www.wordnik.com/lists/words-to-describe-the-taste-of-food')
    words = {tag.text for tag in driver.find_elements_by_class_name('word') if tag.text}
    print words
    driver.get('http://hybridrastamama.com/150-words-to-describe-the-taste-of-food-to-children-and-adults-alike/')
    sleep(5)
    div = driver.find_element_by_class_name('entry-content')
    for li in div.find_elements_by_tag_name('li'):
        print li.text
        words.add(li.text.lower())
    for word in words:
        word = word if word.find('(') == -1 else word[:word.find('(')]
        db.food_adjectives.insert({'term': word})
    driver.close()


def scrape_bcc_ingridients():
    ingr_coll = db.ingredients
    for l in 'abcdefghijklmnopqrstuvwxyz':
        response = requests.get('http://www.bbc.co.uk/food/ingredients/by/letter/' + l)
        print response.status_code
        page = BeautifulSoup(response.text)
        foods = page.findAll('li', {'class':"resource food"})
        for f in foods:
            text = f.a.text.strip()
            url = 'http://www.bbc.co.uk' + f.a['href']
            ingr_coll.insert({'source': 'bbc.co.uk', 'name': text, 'url': url}) 


def scrape_poets(ingredients=None):
    '''
    Search for ingredient name on poets.org, parse each search results page and 
    save to db
    
    Args:
        ingredients(set) -- limit scrape to ingredients in set
    '''    
    saved_count = 0
    
    if not ingredients:
        ingredients = get_ingredient_objects()
    
    for ingredient in ingredients:
        try:
            saved_titles = {i['title']: i['_id'] for i in db.poems.find()}
            page = get_poets_page('/search/node/type%3Apoems%20"'+ingredient.name+'"')
            poems = parse_poets_page(page, saved_titles)
            page_links = parse_poets_search_pages(page)
            for page_link in page_links:
                print page_link
                page = get_poets_page(page_link)
                poems += parse_poets_page(page, saved_titles)
            for poem in poems:
                poem_id = poem.save()
                ingredient.associate_poem(poem_id)
            print ingredient.name, 'saved', len(poems)
            saved_count += len(poems)
        except Exception as e:
            print e, 'on', ingredient
    print 'total saved', saved_count


def parse_poets_page(search_page, saved_titles):
    '''
    For each link in search results, grab page, parse it and return list of poem objects
    
    Args:
        search_page(BeautifulSoup) -- search results page object 
    '''
    poems = []
    poem_links = parse_poets_search_results(search_page)
    for title in poem_links:
        if title not in saved_titles:
            poem_page = get_poets_page(poem_links[title])
            poem_tag = poem_page.find('div', {'id': 'poem-content'})
            author = poem_tag.find('h2').span.text
            text = poem_tag.find('div', {'class': 'field-item'}).text
            poems.append(Poem(title, author, text))
            #poems.append({'title': title, 'author': author, 'text': text, 'professional': True})
    return poems


def parse_poets_search_pages(page):
    ul = page.find('ul', {'class':'pager'})
    return [li.a['href'] for li in ul.findAll('li')] if ul else []


def get_poets_page(link):
    if not link.startswith('https://www.poets.org'):
         link = 'https://www.poets.org' + link
    response = requests.get(link)
    return BeautifulSoup(response.text)


def parse_poets_search_results(list_page):
    list_items = list_page.findAll('li', {'class': 'search-result'})
    poem_links = {clean_word(l.a.text): l.a['href'] for l in list_items}
    return poem_links


def scrape_poetryfoundation(ingredients=None):
    chromedriver = "/Users/jperelshteyn/Downloads/chromedriver"
    environ["webdriver.chrome.driver"] = chromedriver
    driver = webdriver.Chrome(chromedriver)
    if not ingredients:
        ingredients = get_ingredient_objects()
    for ingredient in ingredients:
        saved_titles = {i['title']: i['_id'] for i in db.poems.find()}
        print ingredient.name
        for page_num in range(1, 10):
            try:
                poem_links = {}
                i_name = ingredient.name
                url = 'http://www.poetryfoundation.org/search/poems#preview=0&qs='+i_name+'&page='+str(page_num)
                print url
                driver.get(url)
                sleep(1)
                links = driver.find_elements_by_xpath('//a[@class="title"]')
                if len(links) == 0:
                    break
                for l in links:
                    poem_links[clean_word(l.text)] = l.get_attribute('href')
                for title in poem_links:
                    if title not in saved_titles:
                        print title
                        driver.get(poem_links[title])
                        author = driver.find_element_by_xpath('//span[@class="author"]/a').text
                        text = driver.find_element_by_xpath('//div[@class="poem"]').text
                        #poems.append({'title': title, 'author': author, 'text': text, 'professional': True})
                        poem = Poem(title, author, text)
                        poem_id = poem.save()
                        ingredient.associate_poem(poem_id)
                    else:
                        ingredient.associate_poem(saved_titles[title])
            except Exception as e:
                print e, 'on', ingredient
                traceback.print_exc()
    driver.close


def remove_duplicate_ingredients():
    ingr = set()
    ingr_coll = db.ingredients
    ingr_coll.count()
    for i in ingr_coll.find():
        if i['name'] in ingr:
            ingr_coll.remove({'_id': i['_id']})
        else:
            ingr.add(i['name'])


def is_URL(string):
    return string.find('http') == 0


def scrape_food_ingridients(start_page=1):
    ingr_coll = db.ingredients
    chromedriver = "/Users/jperelshteyn/Downloads/chromedriver"
    environ["webdriver.chrome.driver"] = chromedriver
    driver = webdriver.Chrome(chromedriver)
    for page_num in range(start_page, 1000):
        url = "http://www.food.com/about/?pn=" + str(page_num)
        print url
        driver.get(url)
        anchors = driver.find_elements_by_xpath('//div[contains(@class,"fd-tile")]//a')
        if not anchors or len(anchors) == 0:
            driver.save_screenshot('screenie.png')
            break
        a_dict = {}
        for a in anchors:
            if not a or not a.text:
                driver.save_screenshot('screenie.png')
                print 'error: ' + str(a)
                continue
            a_dict[a.text] = a.get_attribute('href')
            print a.text
        for food in a_dict:
            if not is_URL(a_dict[food]):
                print 'url error: ' + str(food)
                continue
            driver.get(a_dict[food])
            p = driver.find_element_by_xpath('//div[@class="fd-main"]/p')
            print food, len(p.text)
            ingr_coll.insert({'source': 'food.com', 'name': food, 'description': p.text})
    driver.close()


def scrape_bbc_descriptions(ingredient):
    try:
        ingredient = ingredient.strip().lower().replace(' ', '_')
        response = requests.get('http://www.bbc.co.uk/food/' + ingredient)
        print ingredient
        print response.status_code
        page = BeautifulSoup(response.text)
        summary_div = page.find('div', {'id':"summary"})
        text = summary_div.text
        return text
    except:
        print 'None'
        return None


def filter_adjectives(text):
    if text:
        return set(clean_word(t[0]) for t in tb(text).tags if t[1] == 'JJ')
    else:
        return set()


def get_adjacent_poem_text(ingredient, num_adjacent_words):
    text = ''
    for poem in ingredient.get_poem_texts():
        poem_words = [clean_word(word) for word in poem.split()]
        for ind, word in enumerate(poem_words):
            if word == ingredient.name.lower():
                beg_ind = max(0, ind - num_adjacent_words)
                end_ind = min(len(poem_words) - 1, ind + num_adjacent_words)
                text += ' '.join(poem_words[beg_ind:end_ind+1]) + '; '
#                 for word_index in range(beg_ind, end_ind+1):
#                     if poem_words[word_index]:
#                         words.append(poem_words[word_index])
    return text


def get_synonyms(words):
    cred = 'key=' + config['altervista']
    url = 'http://thesaurus.altervista.org/thesaurus/v1'
    synonyms_dict = {}
    for word in words:
        r_string = "{}?{}&{}&{}&{}".format(url, cred, "word=" + word, 'language=en_US', 'output=json')
        r = requests.get(r_string)
        obj = r.json()
        synonyms = []
        if r.status_code == 200:
            for resp in obj['response']:
                if resp['list']['category'] == '(adj)' and 'synonyms' in resp['list']:
                    for synonym in resp['list']['synonyms'].split('|'):
                        if synonym.find('antonym') == -1:
                            p_loc = synonym.find('(')
                            if p_loc > -1:
                                synonym = synonym[:p_loc].strip()
                            synonyms.append(u_to_a(synonym))
            synonyms_dict[word] = synonyms
        else:
            print word, r.text
            if r.status_code == 403:
                print 'Over rate limit'
                return 'Exit'
            else:
                db.non_adjectives.insert({'word': word})
    return synonyms_dict


def scrape_synonym(words):
    synonyms_dict = {}
    for word in words:
        synonyms = []
        url = 'http://www.synonym.com/synonyms/' + word
        response = requests.get(url)
        print url, response.status_code
        if response.status_code == 200:
            page = BeautifulSoup(response.text)
            cards = page.findAll('div', {'class':"synonym"})
            for card in cards:
                if card.h3.text.find('adj') > -1:
                    ul = card.find('ul', {'class': 'synonyms'})
                    for li in ul.findAll('li'):
                        synonyms.append(clean_word(li.a.text))
        else:
            print word, response.status_code
            if response.status_code == 403:
                print 'Denied'
                return 'Exit'
            else:
                db.non_adjectives.insert({'word': word})
        synonyms_dict[word] = synonyms
    return synonyms_dict



def update_ingredient_adjectives(ingredients=None, num_adjacent_words=3):
    saved_adjectives = set(c['word'] for c in db.adjectives.find())
    saved_non_adjectives = set(c['word'] for c in db.non_adjectives.find())
    sarg = {}
    completed = []
    if not ingredients:
        ingredients = get_ingredient_objects()
    #try:
    for ingredient in ingredients:
        print ingredient.name
        poem_text = get_adjacent_poem_text(ingredient, num_adjacent_words)
        desc = ingredient.description
        all_text = (poem_text if poem_text else '') + '; ' + (desc if desc else '')
        adjectives = filter_adjectives(all_text)
        known_adjectives = adjectives & saved_adjectives
        new_adjectives = adjectives - saved_adjectives - saved_non_adjectives
        synonyms = get_synonyms(new_adjectives)
        if synonyms == 'Exit':
            break
        synonyms2 = scrape_synonym(new_adjectives)
        if synonyms2 == 'Exit':
            break
        synonyms.update(synonyms2)
        print len(all_text.split()), 'words,',  \
                len(known_adjectives), 'known adjectives,',  \
                len(new_adjectives), 'new adjectives,',  \
                len(synonyms), 'with synonyms'
        for word in synonyms:
            print 'associating word', word
            adj = Adjective(word)
            adj.add_synonyms(synonyms[word])
            adj_id = adj.save()
            ingredient.associate_adjective(adj_id)
        for word in known_adjectives:
            adj = Adjective(word)
            adj.get()
            ingredient.associate_adjective(adj._id)
        completed.append(ingredient)


def scrape_wiki_adjectives(term):
    term = '_'.join(term.split())
    response = requests.get('https://en.wikipedia.org/wiki/' + term)
    page = BeautifulSoup(response.text)
    article_div = page.find('div', {'id':"bodyContent"})
    text = article_div.text
    return set(clean_word(t[0]) for t in tb(text).tags if t[1] == 'JJ')


def update_genre_adjectives():
    saved_adjectives = set(c['word'] for c in db.adjectives.find())
    for genre_name in ['Rock', 'Jazz', 'Classical']:
        genre = Genre(genre_name)
        genre.get()
        print genre.name
        scraped_adjectives = set(genre.scraped_adjectives)
        known_adjectives = scraped_adjectives & saved_adjectives
        new_adjectives = scraped_adjectives - saved_adjectives
        synonyms = get_synonyms(new_adjectives)
        if synonyms == 'Exit':
            break
        synonyms2 = scrape_synonym(new_adjectives)
        if synonyms2 == 'Exit':
            break
        synonyms.update(synonyms2)
        print len(scraped_adjectives), 'scraped adjectives,',  \
                len(known_adjectives), 'known adjectives,',  \
                len(new_adjectives), 'new adjectives,',  \
                len(synonyms), 'with synonyms'
        for word in synonyms:
            print 'associating word', word
            adj = Adjective(word)
            adj.add_synonyms(synonyms[word])
            adj_id = adj.save()
            genre.associate_adjective(adj_id)
        for word in known_adjectives:
            adj = Adjective(word)
            adj.get()
            genre.associate_adjective(adj._id)

def score_ingredients():
    genre_adjectives = {}
    genres = ['Rock', 'Jazz', 'Classical']
    for g_name in genres:
        genre = Genre(g_name)
        genre.get()
        genre_adjectives[g_name] = genre.get_adjectives()
    for ingredient in get_ingredient_objects():
        ingr_adjectives = ingredient.get_adjectives()
        if not ingr_adjectives: continue
        norm_score = 1/len(ingr_adjectives)
        genre_scores = {g:{} for g in genres}
        count = 0
        for ingr_adj in ingr_adjectives:
            for g_name in genres:
                if ingr_adj in genre_adjectives[g_name]:
                    genre_scores[g_name][ingr_adj] = genre_scores[g_name].get(ingr_adj, 0) + norm_score
                    count += 1
        print ingredient.name, count, norm_score
        ingredient.genre_scores = genre_scores
        ingredient.save()




