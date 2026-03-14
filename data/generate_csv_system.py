import csv
import os
import json

os.makedirs("data", exist_ok=True)

# ----------------------------
# SERVICES
# ----------------------------

services = [
("roof-replacement-cost-by-state","Roof Replacement Cost"),
("hvac-installation-cost-by-state","HVAC Installation Cost"),
("foundation-repair-cost-by-state","Foundation Repair Cost"),
("window-replacement-cost-by-state","Window Replacement Cost"),
("deck-building-cost-by-state","Deck Building Cost"),
("garage-door-repair-cost-by-state","Garage Door Repair Cost"),
("water-heater-installation-cost-by-state","Water Heater Installation Cost"),
("concrete-driveway-cost-by-state","Concrete Driveway Cost"),
("electrician-rates-by-state","Electrician Rates"),
("plumber-rates-by-state","Plumber Rates"),
("painter-rates-by-state","Painter Rates"),
("handyman-rates-by-state","Handyman Rates")
]

with open("data/services.csv","w",newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["slug","name"])
    writer.writerows(services)

print("services.csv created")

# ----------------------------
# STATES
# ----------------------------

states = [
("alabama","Alabama"),
("alaska","Alaska"),
("arizona","Arizona"),
("arkansas","Arkansas"),
("california","California"),
("colorado","Colorado"),
("connecticut","Connecticut"),
("delaware","Delaware"),
("florida","Florida"),
("georgia","Georgia"),
("hawaii","Hawaii"),
("idaho","Idaho"),
("illinois","Illinois"),
("indiana","Indiana"),
("iowa","Iowa"),
("kansas","Kansas"),
("kentucky","Kentucky"),
("louisiana","Louisiana"),
("maine","Maine"),
("maryland","Maryland"),
("massachusetts","Massachusetts"),
("michigan","Michigan"),
("minnesota","Minnesota"),
("mississippi","Mississippi"),
("missouri","Missouri"),
("montana","Montana"),
("nebraska","Nebraska"),
("nevada","Nevada"),
("new-hampshire","New Hampshire"),
("new-jersey","New Jersey"),
("new-mexico","New Mexico"),
("new-york","New York"),
("north-carolina","North Carolina"),
("north-dakota","North Dakota"),
("ohio","Ohio"),
("oklahoma","Oklahoma"),
("oregon","Oregon"),
("pennsylvania","Pennsylvania"),
("rhode-island","Rhode Island"),
("south-carolina","South Carolina"),
("south-dakota","South Dakota"),
("tennessee","Tennessee"),
("texas","Texas"),
("utah","Utah"),
("vermont","Vermont"),
("virginia","Virginia"),
("washington","Washington"),
("west-virginia","West Virginia"),
("wisconsin","Wisconsin"),
("wyoming","Wyoming")
]

with open("data/states.csv","w",newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["slug","name"])
    writer.writerows(states)

print("states.csv created")

# ----------------------------
# CITIES (starter set)
# ----------------------------

cities = [
("Austin","texas",950000),
("Dallas","texas",1300000),
("Houston","texas",2300000),
("San Antonio","texas",1500000),
("Fort Worth","texas",900000),
("Los Angeles","california",4000000),
("San Diego","california",1400000),
("San Jose","california",1000000),
("San Francisco","california",880000),
("Sacramento","california",500000),
("Miami","florida",470000),
("Orlando","florida",300000),
("Tampa","florida",390000),
("Jacksonville","florida",950000),
("Tallahassee","florida",200000),
("Minneapolis","minnesota",430000),
("St Paul","minnesota",300000),
("Rochester","minnesota",120000),
("Duluth","minnesota",85000),
("Bloomington","minnesota",90000)
]

with open("data/cities.csv","w",newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["city","state_slug","population"])
    writer.writerows(cities)

print("cities.csv created")

# ----------------------------
# POPULAR CITIES
# ----------------------------

popular = [
("Austin","texas"),
("Dallas","texas"),
("Houston","texas"),
("Los Angeles","california"),
("San Diego","california"),
("Miami","florida"),
("Orlando","florida"),
("Minneapolis","minnesota")
]

with open("data/popular_cities.csv","w",newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["city","state_slug"])
    writer.writerows(popular)

print("popular_cities.csv created")

# ----------------------------
# MANIFEST
# ----------------------------

with open("data/published_manifest.json","w") as f:
    json.dump({},f)

print("published_manifest.json created")
