LISTINGS = [
    {"id": "home-1", "location": "Austin", "bedrooms": 3},
    {"id": "home-2", "location": "Boston", "bedrooms": 2},
    {"id": "home-3", "location": "Austin", "bedrooms": 1},
]


def search_properties(location: str = "", min_bedrooms: int = 0):
    """Filter listings by location substring and bedroom count."""
    normalized_location = location.strip().lower()
    return [
        listing
        for listing in LISTINGS
        if (not normalized_location or normalized_location in listing["location"].lower())
        and listing["bedrooms"] >= min_bedrooms
    ]
