import json
import requests
import pathlib

from ..Utils.LogMaster.log_init import MainLogger


class ESDB():
	def __init__(self, config, es_uri, queries_file, schema_file, auto_check_server=True):

		root_log = MainLogger(config)
		self.log = root_log.StandardLogger("NeuralDB - ElasticSearchClient")  # Create a script specific logging instance

		self.es_uri = es_uri

		schema_file = pathlib.Path(schema_file)
		schema_file = schema_file.resolve()  # Find absolute path from a relative one.
		queries_file = pathlib.Path(queries_file)
		queries_file = queries_file.resolve()  # Find absolute path from a relative one.


		self.schema_file = f = open(schema_file, 'r')
		self.schema_file_data = json.load(self.schema_file)
		self.queries_file = f = open(queries_file, 'r')
		self.queries_file_data = json.load(self.queries_file)

		self.log.debug(f"ElasticSearch Client initialized with {self.es_uri}. Config files: {self.schema_file} and {self.queries_file} parsed!")

		if auto_check_server:
			self.__check_es_status()

	def __check_es_status(self):
		es_status = requests.get(self.es_uri, timeout=10)
		es_status = json.dumps(str(es_status))
		if "200" not in str(es_status):
			raise RuntimeError(f"ElasticSearch Server is unreachable!")
		else:
			self.log.info(f"ElasticSearch Server is reachable!")
			return True

	def create_index(self, index_name, schema_name):
		available_schemas = ['object_db_schema', 'word_db_schema']
		success_status = "<Response [200]>"

		try:
			specific_schema = self.schema_file_data[schema_name]
		except KeyError:
			self.log.error(f"Schema not found from available schemas: {available_schemas}")
			return

		# print(json.dumps(specific_schema, indent=2))

		schema_uri = self.es_uri + "/" + index_name

		schema_stat = requests.put(schema_uri, json=specific_schema)

		schema_stat = json.dumps(str(schema_stat))

		check_stat = requests.get(schema_uri + "/_settings")
		check_stat = json.dumps(str(check_stat))

		if "200" in str(schema_stat) and "200" in str(check_stat):
			self.log.info(f"Index {index_name} with {schema_name} schema successfully created and verified!")
		elif "200" in str(schema_stat) and "200" not in str(check_stat):
			self.log.error(
				f'Error creating index {index_name} with {schema_name} schema! Perhaps request was incorrectly formed or '
				f'ElasticSearch Server is unreachable.')
		elif "200" not in str(schema_stat) and "200" in str(check_stat):
			self.log.warning(f'Error creating index {index_name} with {schema_name} schema! The schema named {schema_name} likely '
			      f'already exists.')
		else:
			self.log.error(
				f'Error creating index {index_name} with {schema_name} schema! Perhaps request was incorrectly formed or '
				f'ElasticSearch Server is unreachable.')

	#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

	def add_doc(self, index_name, data_type, data, update="add"):
		es_uri = self.es_uri
		data_type_valid = ['object_db_schema', 'word_db_schema']
		if data_type not in data_type_valid:
			raise ValueError(f"Data type {data_type} not found in available data types: {data_type_valid}")

		update_valid = ["add", "concatenate", "overwrite", "blind"]
		if update not in update_valid:
			raise ValueError(f"Data type {data_type} not found in available data types: {update_valid}")

		success_status = "<Response [200]>"

		if data_type == 'object_db_schema':
			index_check = requests.get(es_uri + "/" + index_name)
			index_check = json.dumps(str(index_check))
			if "200" not in str(index_check):
				raise RuntimeError(f"Index {index_name} not found!")

			try:
				name = data['name']
				description = data['description']
				users = data['users']
				related_objects = data['related_objects']
				locations = data['locations']
			except KeyError:
				raise RuntimeError("Improperly formatted data. Data MUST be in the following format: {name: str, "
				                   "description: str, users: list, related_objects: list, locations: list}")

			# queries_file = open('queries.json', 'r')
			queries = self.queries_file_data

			queries["object_exists"]["query"]["query_string"]["query"] = name

			object_exists = requests.post(es_uri + "/" + index_name + "/_search", json=queries["object_exists"])
			object_exists_simple = json.dumps(str(object_exists))
			object_exists_full = json.loads(str(object_exists.text))

			print(object_exists_full["hits"]["total"]["value"])

			if "200" in object_exists_simple and object_exists_full["hits"]["total"]["value"] > 0 and update != "add":
				print(f"Object {name} already exists in index {index_name}!")
				if object_exists_full["hits"]["total"]["value"] > 1:
					raise RuntimeError("Search for existing objects failed and returned more than one result.")

				hit = object_exists_full["hits"]["hits"][0]
				hit_id = hit["_id"]
				hit_source = hit["_source"]

				print(type(hit_source["users"]))

				if update == "concatenate" or update == "blind":
					hit_source["name"] = name
					hit_source["description"] += description
					hit_source["users"] += users
					hit_source["related_objects"] += related_objects
					hit_source["locations"] += locations
				elif update == "overwrite":
					hit_source["name"] = name
					hit_source["description"] = description
					hit_source["users"] = users
					hit_source["related_objects"] = related_objects
					hit_source["locations"] = locations

				hit_source = json.dumps(hit_source)
				print(hit_source)
				hit_source = """{"doc":""" + hit_source + "}"
				print(hit_source)
				hit_source = json.loads(hit_source)
				print(hit_source)

				update_uri = es_uri + "/" + index_name + "/_update/" + hit_id
				update_stat = requests.post(update_uri, json=hit_source)
				print(update_stat.text)


			elif "200" in object_exists_simple and object_exists_full["hits"]["total"][
				"value"] == 0 and update == "add":
				print(f"Object {name} does not exist in index {index_name}! Proceeding to add object...")

				data_uri = es_uri + "/" + index_name + "/_doc"
				data_stat = requests.post(data_uri, json=data)
				data_stat = json.dumps(str(data_stat))

				print(data_stat)

				if "201" in str(data_stat):
					print(f"Object {name} successfully added to index {index_name}!")
				else:
					print(f"Error adding object {name} to index {index_name}!")
			else:
				print(f"Error checking if object {name} exists in index {index_name}!")

		elif data_type == 'word_db_schema':
			index_check = requests.get(es_uri + "/" + index_name)
			index_check = json.dumps(str(index_check))
			if "200" not in str(index_check):
				raise RuntimeError(f"Index {index_name} not found!")

			try:
				word = data['word']
				definition = data['definition']
				users = data['users']
				related_words = data['related_words']
				related_objects = data['related_objects']
				locations = data['locations']
			except KeyError:
				raise RuntimeError("Improperly formatted data. Data MUST be in the following format: {name: str, "
				                   "description: str, users: list, related_objects: list, locations: list}")

			# queries_file = open('queries.json', 'r')
			queries = self.queries_file_data

			queries["word_exists"]["query"]["query_string"]["query"] = word

			word_exists = requests.post(es_uri + "/" + index_name + "/_search", json=queries["word_exists"])
			word_exists_simple = json.dumps(str(word_exists))
			word_exists_full = json.loads(str(word_exists.text))

			print(word_exists_full["hits"]["total"]["value"])

			if "200" in word_exists_simple and word_exists_full["hits"]["total"]["value"] > 0 and update != "add":
				print(f"Object {word} already exists in index {index_name}!")
				if word_exists_full["hits"]["total"]["value"] > 1:
					raise RuntimeError("Search for existing objects failed and returned more than one result.")

				hit = word_exists_full["hits"]["hits"][0]
				hit_id = hit["_id"]
				hit_source = hit["_source"]

				print(type(hit_source["users"]))

				if update == "concatenate" or update == "blind":
					hit_source["word"] += word
					hit_source["description"] += definition
					hit_source["users"] += users
					hit_source["related_objects"] += related_objects
					hit_source["related_words"] += related_words
					hit_source["locations"] += locations
				elif update == "overwrite":
					hit_source["word"] = word
					hit_source["description"] = definition
					hit_source["users"] = users
					hit_source["related_objects"] = related_objects
					hit_source["related_words"] = related_words
					hit_source["locations"] = locations

				hit_source = json.dumps(hit_source)
				print(hit_source)
				hit_source = """{"doc":""" + hit_source + "}"
				print(hit_source)
				hit_source = json.loads(hit_source)
				print(hit_source)

				update_uri = es_uri + "/" + index_name + "/_update/" + hit_id
				update_stat = requests.post(update_uri, json=hit_source)
				print(update_stat.text)


			elif "200" in word_exists_simple and word_exists_full["hits"]["total"]["value"] == 0 and update == "add":
				print(f"Object {word} does not exist in index {index_name}! Proceeding to add object...")

				data_uri = es_uri + "/" + index_name + "/_doc"
				data_stat = requests.post(data_uri, json=data)
				data_stat = json.dumps(str(data_stat))

				print(data_stat)

				if "201" in str(data_stat):
					print(f"Object {word} successfully added to index {index_name}!")
				else:
					print(f"Error adding object {word} to index {index_name}!")
			else:
				print(f"Error checking if object {word} exists in index {index_name}!")

	def format_object_data(self, name, description="", locations=[], related_objects=[], users=[]):
		if type(name) is not str:
			raise ValueError("The 'name' parameter MUST be of type String.")
		if type(description) is not str:
			raise ValueError("The 'description' parameter MUST be of type String.")
		if type(locations) is not list:
			raise ValueError("The 'locations' parameter MUST be of type List.")
		if type(related_objects) is not list:
			raise ValueError("The 'related_objects' parameter MUST be of type List.")
		if type(users) is not list:
			raise ValueError("The 'users' parameter MUST be of type List.")
		


		data = {
			"name": name,
			"description": description,
			"locations": locations,
			"related_objects": related_objects,
			"users": users
		}
		
		return data

	def format_word_data(self, word, definition="", locations=[], related_objects=[], users=[], related_words=[]):
		if type(word) is not str:
			raise ValueError("The 'word' parameter MUST be of type String.")
		if type(definition) is not str:
			raise ValueError("The 'definition' parameter MUST be of type String.")
		if type(locations) is not list:
			raise ValueError("The 'locations' parameter MUST be of type List.")
		if type(related_objects) is not list:
			raise ValueError("The 'related_objects' parameter MUST be of type List.")
		if type(users) is not list:
			raise ValueError("The 'users' parameter MUST be of type List.")
		if type(related_words) is not list:
			raise ValueError("The 'related_words' parameter MUST be of type List.")

		data = {
			"word": word,
			"definition": definition,
			"locations": locations,
			"related_objects": related_objects,
			"related_words": related_words,
			"users": users
		}

		return data

	def search(self, index_name, index_type, keyword):
		data_type_valid = ['object_db_schema', 'word_db_schema']
		if index_type not in data_type_valid:
			raise ValueError(f"Data type {index_type} not found in available data types: {data_type_valid}")

		queries = self.queries_file_data

		self.log.info(f"Searching for '{keyword}' in '{index_name}' index (of type '{index_type}')...")

		if index_type == "object_db_schema":
			queries["object_full"]["query"]["multi_match"]["query"] = keyword

			object_full = requests.post(self.es_uri + "/" + index_name + "/_search", json=queries["object_full"])
			object_full = json.loads(str(object_full.text))
			return object_full
		elif index_type == "word_db_schema":
			queries["word_full"]["query"]["multi_match"]["query"] = keyword

			word_full = requests.post(self.es_uri + "/" + index_name + "/_search", json=queries["word_full"])
			word_full = json.loads(str(word_full.text))
			return word_full

	def delete_all_indices(self):

		indices_resp = requests.get(self.es_uri + "/_cat/indices/?format=json")
		json_indicies = json.loads(indices_resp.text)
		indicies = []
		for j in json_indicies:
			indicies.append(j["index"])

		for i in indicies:
			del_resp = requests.delete(self.es_uri + "/" + str(i))
