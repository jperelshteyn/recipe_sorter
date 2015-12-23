from recipe_classes import *
from os.path import join
from os import environ
from os import listdir

def export_data(col_names=[]):
    db = client.recipes
    for col_name in db.collection_names():
        if col_name.find('system') == -1 and (len(col_names) == 0 or col_name in col_names):
            collection = {}
            col = db[col_name]
            for record in col.find():
                _id = str(record['_id'])
                del record['_id']
                collection[_id] = object_ids_to_str(record)
            jsonpath = col_name + ".json"
            jsonpath = join('backup/', jsonpath)
            with open(jsonpath, 'w') as jsonfile:
                json.dump(collection, jsonfile)


def object_ids_to_str(record):
    if type(record) is not dict:
        return record
    else:
        for k in record.keys():
            if k.find('_id') > -1:
                if type(record[k]) is list:
                    record[k] = [str(v) for v in record[k] if type(v) is ObjectId]
                else:
                    v = record[k]
                    record[k] = str(v) if type(v) is ObjectId else v
            if type(record[k]) is dict:
                record[k] = object_ids_to_str(record[k])
    return record 


def import_data(file_path, test):
    if test:
        db = client.test
    else:
        db = client.recipes
    col_name = file_path.split('/')[-1].split('.')[0]
    col = db[col_name]
    data = json.loads(open(file_path).read())
    if data:
        col.remove({})
    for _id in data:
        record = {'_id': ObjectId(_id)} if _id != 'None' else {}
        record.update(data[_id])
        record = str_to_object_ids(record)
        col.insert(record)


def str_to_object_ids(record):
    if type(record) is not dict:
        return record
    else:
        for k in record.keys():
            if k.find('_id') > -1:
                if type(record[k]) is list:
                    record[k] = [ObjectId(v) for v in record[k] if type(v) is not ObjectId]
                else:
                    v = record[k]
                    record[k] = ObjectId(v) if type(v) is not ObjectId else v
            if type(record[k]) is dict:
                record[k] = str_to_object_ids(record[k])
    return record


def setup_recipe_database(backup_dir_path = "backup", test=True):
    for file_name in listdir(backup_dir_path):
        if file_name.endswith(".json"):
            import_data(backup_dir_path+'/'+file_name, test)


