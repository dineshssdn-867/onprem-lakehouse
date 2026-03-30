"""
Generate synthetic Yelp-like dataset for the lakehouse pipeline.

Produces JSON files matching the Yelp academic dataset schema:
  - yelp_academic_dataset_business.json  (~5,000 restaurants)
  - yelp_academic_dataset_user.json      (~10,000 users)
  - yelp_academic_dataset_review.json    (~50,000 reviews)
  - yelp_academic_dataset_checkin.json   (~3,000 checkins)
  - yelp_academic_dataset_tip.json       (~8,000 tips)

Usage:
  pip install faker boto3
  python generate_data.py                  # writes to ./output/
  python generate_data.py --upload         # writes + uploads to MinIO s3://raw-data/yelp/json/
"""

import argparse
import json
import os
import random
import string
import uuid
from datetime import datetime, timedelta

try:
    from faker import Faker
except ImportError:
    print("Install faker: pip install faker")
    raise

fake = Faker()
Faker.seed(42)
random.seed(42)

# ── Constants ──────────────────────────────────────────────────────────────

NUM_BUSINESSES = 5000
NUM_USERS = 10000
NUM_REVIEWS = 50000
NUM_CHECKINS = 3000
NUM_TIPS = 8000

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

CATEGORIES = [
    "Restaurants", "Food", "Bars", "Nightlife", "American (Traditional)",
    "American (New)", "Italian", "Mexican", "Japanese", "Chinese",
    "Thai", "Indian", "Mediterranean", "French", "Korean",
    "Vietnamese", "Seafood", "Pizza", "Burgers", "Sushi Bars",
    "Sandwiches", "Breakfast & Brunch", "Coffee & Tea", "Bakeries",
    "Desserts", "Ice Cream & Frozen Yogurt", "Steakhouses",
    "Fast Food", "Cajun/Creole", "Greek", "BBQ", "Vegetarian",
    "Vegan", "Tapas Bars", "Wine Bars", "Sports Bars", "Gastropubs",
    "Food Trucks", "Delis", "Diners",
]

CITIES = [
    ("Phoenix", "AZ"), ("Scottsdale", "AZ"), ("Mesa", "AZ"),
    ("Las Vegas", "NV"), ("Henderson", "NV"),
    ("Charlotte", "NC"), ("Raleigh", "NC"),
    ("Pittsburgh", "PA"), ("Philadelphia", "PA"),
    ("Tampa", "FL"), ("Miami", "FL"),
    ("Nashville", "TN"), ("Austin", "TX"), ("Portland", "OR"),
    ("Denver", "CO"), ("Seattle", "WA"), ("Chicago", "IL"),
]

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

REVIEW_SNIPPETS = [
    "The food was absolutely delicious.",
    "Service was a bit slow but the atmosphere made up for it.",
    "Great value for the price.",
    "Would definitely come back again!",
    "Not my favorite place, but decent enough.",
    "The ambiance is fantastic, perfect for a date night.",
    "Portions were generous and everything was fresh.",
    "Waited 30 minutes for a table but it was worth it.",
    "The staff was friendly and attentive.",
    "Overpriced for what you get.",
    "Hidden gem in the neighborhood!",
    "The dessert menu is to die for.",
    "Parking can be a hassle during peak hours.",
    "Best brunch spot in town.",
    "The cocktails were creative and well-made.",
    "A solid choice for a quick lunch.",
    "The pasta was cooked perfectly al dente.",
    "Live music on weekends adds a nice touch.",
    "The sushi was incredibly fresh.",
    "Could use more vegetarian options.",
]

TIP_SNIPPETS = [
    "Try the daily special!",
    "Ask for the secret menu.",
    "Best to make reservations on weekends.",
    "Happy hour is 4-6 PM, great deals.",
    "The patio seating is lovely in the evening.",
    "Get the garlic bread, you won't regret it.",
    "Parking is free after 6 PM.",
    "The brunch menu is only available on weekends.",
    "They have a great kids menu.",
    "Don't skip the homemade desserts.",
]

# ── Helpers ────────────────────────────────────────────────────────────────

def make_id():
    return uuid.uuid4().hex[:22]


def random_date(start_year=2015, end_year=2023):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = end - start
    random_days = random.randint(0, delta.days)
    dt = start + timedelta(days=random_days)
    dt = dt.replace(
        hour=random.randint(0, 23),
        minute=random.randint(0, 59),
        second=random.randint(0, 59),
    )
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def random_hours():
    """Generate realistic business hours."""
    hours = {}
    open_days = random.sample(DAYS, k=random.randint(5, 7))
    for day in open_days:
        open_h = random.choice(["6:0", "7:0", "8:0", "9:0", "10:0", "11:0"])
        close_h = random.choice(["20:0", "21:0", "22:0", "23:0", "0:0"])
        hours[day] = f"{open_h}-{close_h}"
    return hours


def weighted_stars():
    """Yelp-like rating distribution (skewed toward 4-5 stars)."""
    return random.choices([1, 2, 3, 4, 5], weights=[5, 8, 15, 30, 42], k=1)[0]


def review_stars():
    """Individual review rating distribution."""
    return random.choices([1, 2, 3, 4, 5], weights=[8, 10, 18, 30, 34], k=1)[0]


def random_friends(user_ids, max_friends=50):
    n = random.choices(
        [0, 1, 5, 10, 20, 50],
        weights=[10, 20, 30, 20, 15, 5],
        k=1,
    )[0]
    n = min(n, len(user_ids))
    return ", ".join(random.sample(user_ids, n))


# ── Generators ─────────────────────────────────────────────────────────────

def generate_businesses():
    print(f"Generating {NUM_BUSINESSES} businesses...")
    businesses = []
    for _ in range(NUM_BUSINESSES):
        city, state = random.choice(CITIES)
        num_cats = random.randint(1, 4)
        cats = ", ".join(random.sample(CATEGORIES, num_cats))
        biz = {
            "business_id": make_id(),
            "name": fake.company() + " " + random.choice(
                ["Grill", "Kitchen", "Bistro", "Cafe", "Diner",
                 "Bar & Grill", "Eatery", "Restaurant", "Tavern", "Lounge"]
            ),
            "address": fake.street_address(),
            "city": city,
            "state": state,
            "postal_code": fake.zipcode(),
            "latitude": round(float(fake.latitude()), 6),
            "longitude": round(float(fake.longitude()), 6),
            "stars": round(random.uniform(1.0, 5.0) * 2) / 2,  # 0.5 increments
            "review_count": random.randint(3, 500),
            "is_open": random.choices([0, 1], weights=[15, 85], k=1)[0],
            "categories": cats,
            "hours": random_hours(),
        }
        businesses.append(biz)
    return businesses


def generate_users():
    print(f"Generating {NUM_USERS} users...")
    users = []
    user_ids = [make_id() for _ in range(NUM_USERS)]

    for i, uid in enumerate(user_ids):
        review_count = random.randint(0, 200)
        user = {
            "user_id": uid,
            "name": fake.name(),
            "review_count": review_count,
            "yelping_since": random_date(2005, 2020),
            "useful": random.randint(0, 500),
            "funny": random.randint(0, 300),
            "cool": random.randint(0, 300),
            "elite": ", ".join(
                str(y) for y in sorted(random.sample(
                    range(2010, 2024), k=random.randint(0, 5)
                ))
            ),
            "friends": random_friends(user_ids, max_friends=50),
            "fans": random.randint(0, 100),
            "average_stars": round(random.uniform(1.0, 5.0), 2),
            "compliment_hot": random.randint(0, 50),
            "compliment_more": random.randint(0, 30),
            "compliment_profile": random.randint(0, 20),
            "compliment_cute": random.randint(0, 15),
            "compliment_list": random.randint(0, 10),
            "compliment_note": random.randint(0, 40),
            "compliment_plain": random.randint(0, 60),
            "compliment_cool": random.randint(0, 50),
            "compliment_funny": random.randint(0, 50),
            "compliment_writer": random.randint(0, 30),
            "compliment_photos": random.randint(0, 25),
        }
        users.append(user)
    return users, user_ids


def generate_reviews(business_ids, user_ids):
    print(f"Generating {NUM_REVIEWS} reviews...")
    reviews = []
    for _ in range(NUM_REVIEWS):
        num_sentences = random.randint(2, 6)
        text = " ".join(random.choices(REVIEW_SNIPPETS, k=num_sentences))
        review = {
            "review_id": make_id(),
            "user_id": random.choice(user_ids),
            "business_id": random.choice(business_ids),
            "stars": review_stars(),
            "useful": random.randint(0, 20),
            "funny": random.randint(0, 10),
            "cool": random.randint(0, 15),
            "text": text,
            "date": random_date(2015, 2023),
        }
        reviews.append(review)
    return reviews


def generate_checkins(business_ids):
    print(f"Generating {NUM_CHECKINS} checkins...")
    checkins = []
    sampled = random.sample(business_ids, min(NUM_CHECKINS, len(business_ids)))
    for bid in sampled:
        num_dates = random.randint(1, 30)
        dates = ", ".join(sorted(random_date(2015, 2023) for _ in range(num_dates)))
        checkin = {
            "business_id": bid,
            "date": dates,
        }
        checkins.append(checkin)
    return checkins


def generate_tips(business_ids, user_ids):
    print(f"Generating {NUM_TIPS} tips...")
    tips = []
    for _ in range(NUM_TIPS):
        tip = {
            "user_id": random.choice(user_ids),
            "business_id": random.choice(business_ids),
            "text": random.choice(TIP_SNIPPETS),
            "date": random_date(2015, 2023),
            "compliment_count": random.randint(0, 10),
        }
        tips.append(tip)
    return tips


# ── Write JSON (one object per line, like Yelp dataset) ───────────────────

def write_jsonl(data, filename, output_dir=OUTPUT_DIR):
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w") as f:
        for record in data:
            f.write(json.dumps(record) + "\n")
    size_mb = os.path.getsize(filepath) / (1024 * 1024)
    print(f"  Wrote {filepath} ({len(data)} records, {size_mb:.1f} MB)")
    return filepath


# ── Upload to MinIO ───────────────────────────────────────────────────────

def upload_to_minio(files):
    import boto3
    from botocore.client import Config as BotoConfig

    endpoint = os.environ.get("AWS_S3_ENDPOINT", "http://localhost:9000")
    access_key = os.environ.get("AWS_ACCESS_KEY", "minio")
    secret_key = os.environ.get("AWS_SECRET_KEY", "minio123")

    print(f"\nUploading to MinIO at {endpoint}...")
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=BotoConfig(signature_version="s3v4"),
        region_name="us-east-1",
    )

    bucket = "raw-data"
    prefix = "yelp/json"

    for filepath in files:
        key = f"{prefix}/{os.path.basename(filepath)}"
        print(f"  Uploading {key}...")
        s3.upload_file(filepath, bucket, key)
        print(f"  Done: s3://{bucket}/{key}")

    print("All files uploaded successfully!")


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic Yelp dataset")
    parser.add_argument("--upload", action="store_true", help="Upload to MinIO after generating")
    parser.add_argument("--output-dir", default=OUTPUT_DIR, help="Output directory")
    args = parser.parse_args()

    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("Generating synthetic Yelp dataset")
    print(f"  Businesses: {NUM_BUSINESSES}")
    print(f"  Users:      {NUM_USERS}")
    print(f"  Reviews:    {NUM_REVIEWS}")
    print(f"  Checkins:   {NUM_CHECKINS}")
    print(f"  Tips:       {NUM_TIPS}")
    print("=" * 60)

    # Generate
    businesses = generate_businesses()
    users, user_ids = generate_users()
    business_ids = [b["business_id"] for b in businesses]

    reviews = generate_reviews(business_ids, user_ids)
    checkins = generate_checkins(business_ids)
    tips = generate_tips(business_ids, user_ids)

    # Write JSONL files (one JSON object per line — Yelp format)
    files = []
    files.append(write_jsonl(businesses, "yelp_academic_dataset_business.json", output_dir))
    files.append(write_jsonl(users, "yelp_academic_dataset_user.json", output_dir))
    files.append(write_jsonl(reviews, "yelp_academic_dataset_review.json", output_dir))
    files.append(write_jsonl(checkins, "yelp_academic_dataset_checkin.json", output_dir))
    files.append(write_jsonl(tips, "yelp_academic_dataset_tip.json", output_dir))

    print(f"\nAll files written to {output_dir}/")

    if args.upload:
        upload_to_minio(files)

    print("\nDone!")


if __name__ == "__main__":
    main()
