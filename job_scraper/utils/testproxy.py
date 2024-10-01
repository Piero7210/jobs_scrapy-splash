import requests

proxy_username = '80c437873bbc27d63aa9'
proxy_password = '60e5506f4a26d525'
proxy_url = f'http://{proxy_username}:{proxy_password}@gw.dataimpulse.com:823'

response = requests.get('http://httpbin.org/ip', proxies={"http": proxy_url, "https": proxy_url})
print(response.json())