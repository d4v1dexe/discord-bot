import json, urllib.request, urllib.error
from pathlib import Path

url = "https://v2.jokeapi.dev/joke/Programming"


def get_random_joke():
    try:
        response = urllib.request.urlopen(url, timeout=10)
        return json.loads(response.read())
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            json.JSONDecodeError) as e:
        print(f'Failed to fetch joke: {e}')
        return None

if __name__ == '__main__':
    joke = get_random_joke()
    if joke is None:
        print('Could not fetch a joke right now.')
    else:
        print(joke['setup'] if joke['type'] == 'twopart' else joke['joke'])
        if joke['type'] == 'twopart':
            print(joke['delivery'])
