import json
import requests

def correct_sent_tc_api(sent):
    url = "https://rewriter-paraphraser-text-changer-multi-language.p.rapidapi.com/rewrite"

    payload = "{\r\"language\": \"en\",\r\"strength\": 3,\r\"text\": \""+sent+"\"\r}"
    headers = {
      'content-type': "application/json",
      'x-rapidapi-host': "rewriter-paraphraser-text-changer-multi-language.p.rapidapi.com",
      'x-rapidapi-key': "fa19dcd5e4mshc0d859752f3a27cp1469e6jsn82ced550c9a3"
      }
    response = requests.request("POST", url, data=payload, headers=headers)
    res_dict=json.loads(response.text)
    return res_dict['rewrite']