import json, urllib.request
from pathlib import Path

url = "https://v2.jokeapi.dev/joke/Programming"


def get_random_joke():
    response = urllib.request.urlopen(url)
    return json.loads(response.read())

if __name__ == '__main__':
    joke = get_random_joke()
    print(joke['setup'] if joke['type'] == 'twopart' else joke['joke'])
    if joke['type'] == 'twopart':
        print(joke['delivery'])