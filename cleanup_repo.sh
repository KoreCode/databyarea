#!/bin/bash

echo "Starting repo cleanup..."

# create folders if they don't exist
mkdir -p scripts
mkdir -p data
mkdir -p templates
mkdir -p site
mkdir -p assets

echo "Moving generator scripts..."

if [ -f make-site.py ]; then
    mv make-site.py scripts/build_site.py
fi

if [ -f makesitenew.py ]; then
    mv makesitenew.py scripts/old_generator.py
fi

echo "Moving data files..."

if [ -f published_manifest.json ]; then
    mv published_manifest.json data/
fi

echo "Moving generated site folders..."

for folder in \
deck-building-cost-by-state \
concrete-driveway-cost-by-state \
garage-door-repair-cost-by-state \
plumber-rates-by-state \
utility-costs
do
    if [ -d "$folder" ]; then
        mv "$folder" site/
    fi
done

echo "Moving assets..."

for file in *.css *.png *.jpg *.svg
do
    if [ -f "$file" ]; then
        mv "$file" assets/
    fi
done

echo "Removing junk files..."

rm -f yu.zip

echo "Cleanup complete."

echo "New repo structure:"
tree -L 2
