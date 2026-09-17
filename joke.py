import random
import json
from pathlib import Path

JOKES_FILE = Path(__file__).parent / 'jokes.json'

with open(JOKES_FILE, encoding='utf-8') as f:
    jokes = json.load(f)

def get_random_joke():
    return random.choice(jokes)

if __name__ == '__main__':
    while True:
        joke = get_random_joke()
        print(joke['setup'])
        print(joke['punchline'])
        print()
