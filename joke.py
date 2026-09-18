import random, json, urllib.request
from pathlib import Path

url = "https://v2.jokeapi.dev/joke/Programming"
response = urllib.request.urlopen(url)
joke = json.loads(response.read())

def get_random_joke():
    print(joke['setup'] if joke['type'] == 'twopart' else joke['joke'])
    if joke['type'] == 'twopart':
        print(joke['delivery'])
        

if __name__ == '__main__':
    get_random_joke()