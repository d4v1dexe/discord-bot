import requests

def name_gender_classifier(name: str):
    response = requests.get(f'https://api.genderize.io?name={name}&apikey=c6f6a7fa9f04961e51709d441b88106b')
    return response.json()['gender']

if __name__ == "__main__":
    print(name_gender_classifier("Sofia"))