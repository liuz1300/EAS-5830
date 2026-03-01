import requests
import json

def pin_to_ipfs(data):
	assert isinstance(data,dict), f"Error pin_to_ipfs expects a dictionary"
	url = "http://127.0.0.1:5001/api/v0/add"

	files = {
		"file": ("data.json", json.dumps(data))
	}

	response = requests.post(url, files=files)

	if response.status_code != 200:
		raise Exception(f"IPFS upload failed: {response.text}")

	return response.json()["Hash"]

def get_from_ipfs(cid,content_type="json"):
	assert isinstance(cid,str), f"get_from_ipfs accepts a cid in the form of a string"
	url = f"http://127.0.0.1:8080/ipfs/{cid}"

	response = requests.get(url)

	if response.status_code != 200:
		raise Exception(f"Failed to fetch from IPFS: {response.text}")
	data = response.json()

	assert isinstance(data,dict), f"get_from_ipfs should return a dict"
	return data
