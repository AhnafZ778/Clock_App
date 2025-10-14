import os
import requests
import json

api = os.getenv("Weather_API_Key")

url = f"http://api.weatherapi.com/v1/current.json?key={api}&q=Dhaka&aqi=yes"


# response = requests.get(url)

# if response.status_code == 200:
    
#     with open("Output.json", "w") as f:
#         json.dump(response.json(), f, indent=4)
#     print("Saved Data to Output.json")
    
# else:
#     print(f"Error: {response.status_code}\n{response.text}")
    
    