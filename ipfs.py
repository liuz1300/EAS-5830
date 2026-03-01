import requests
import json

def pin_to_ipfs(data):
	assert isinstance(data,dict), f"Error pin_to_ipfs expects a dictionary"
	url = "https://api.pinata.cloud/pinning/pinJSONToIPFS"

	headers = {
		"pinata_api_key": e30e72100b8dadc81c23,
		"pinata_secret_api_key": d7bb6c5290d223c6de3915b77d94b3e75025ec656398f8d5358b51c4f49ef8d6,
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
