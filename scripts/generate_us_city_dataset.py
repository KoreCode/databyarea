import csv
import requests
import os

os.makedirs("data", exist_ok=True)

url = "https://raw.githubusercontent.com/dr5hn/countries-states-cities-database/master/csv/cities.csv"

print("Downloading dataset...")

r = requests.get(url)
r.raise_for_status()

lines = r.text.splitlines()
reader = csv.DictReader(lines)

cities = []

for row in reader:

    if row["country_code"] != "US":
        continue

    city = row["name"].strip()
    state_code = row["state_code"].lower()
    population = row["population"]

    if population == "":
        population = 0

    cities.append((city, state_code, int(population)))

print("US cities found:", len(cities))

# sort largest population first
cities.sort(key=lambda x: x[2], reverse=True)

with open("data/cities.csv","w",newline="",encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["city","state_slug","population"])
    writer.writerows(cities)

print("cities.csv generated successfully")