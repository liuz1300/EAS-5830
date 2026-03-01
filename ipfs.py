import requests
import json

def pin_to_ipfs(data):
	assert isinstance(data,dict), f"Error pin_to_ipfs expects a dictionary"
	url = "https://api.pinata.cloud/pinning/pinJSONToIPFS"

	headers = {
		"pinata_api_key": "1a321760d1f597ee5e5b",
		"pinata_secret_api_key": "d4571c85772e9837ff3b2d2293610e136a7900891402211669315c3391107935",
		"Content-Type": "application/json"
	}

	response = requests.post(url, headers=headers, data=json.dumps(data))

	if response.status_code != 200:
		raise Exception(f"Pinata upload failed: {response.text}")

	return response.json()["Hash"]

def get_from_ipfs(cid,content_type="json"):
	assert isinstance(cid,str), f"get_from_ipfs accepts a cid in the form of a string"
	url = f"https://gateway.pinata.cloud/ipfs/{cid}"

	response = requests.get(url)

	if response.status_code != 200:
		raise Exception(f"Failed to fetch from IPFS: {response.text}")
	data = response.json()

	assert isinstance(data,dict), f"get_from_ipfs should return a dict"
	return data
