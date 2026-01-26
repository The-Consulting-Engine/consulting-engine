"""
Data cleaning pipeline for competitor analysis.

Transforms raw scraped data into clean, analysis-ready pandas DataFrames.
Handles messy, incomplete data from multiple sources (Google Places, Uber Eats, Apify).

Usage:
    from app.competitor_analysis.data_cleaner import build_all_tables

    tables = build_all_tables(
        restaurants_raw=[...],
        menus_raw=[...],
        reviews_raw=[...],
        competitors_raw=[...],
        target_restaurant_id="abc123"
    )

    restaurants_df = tables["restaurants"]
    menu_items_df = tables["menu_items"]
    reviews_df = tables["reviews"]
    competitors_df = tables["competitors"]
"""

import re
from datetime import datetime
from typing import Optional, Any

import pandas as pd
import numpy as np


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def safe_get(d: dict, key: str, default: Any = None) -> Any:
    """Safely get a value from a dict, handling None dicts."""
    if not isinstance(d, dict):
        return default
    return d.get(key, default)


def clean_string(value: Any) -> Optional[str]:
    """
    Clean a string value: lowercase, strip whitespace, empty → None.

    Handles: None, numbers, lists, dicts gracefully.
    """
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return None

    s = str(value).strip().lower()
    if s in ("", "none", "null", "nan", "n/a", "na"):
        return None
    return s


def clean_string_preserve_case(value: Any) -> Optional[str]:
    """Clean string but preserve original case (for names, titles)."""
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return None

    s = str(value).strip()
    if s in ("", "None", "null", "nan", "N/A", "NA", "n/a", "na"):
        return None
    return s


def parse_price(value: Any) -> Optional[float]:
    """
    Parse price from various formats → float.

    Handles:
        - "$12.99" → 12.99
        - "12.99" → 12.99
        - 1299 (cents) → 12.99 (if > 100, assumes cents)
        - 12.99 → 12.99
        - "$12-15" → 12.0 (takes first number)
        - None, "N/A" → None
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        # If it looks like cents (> 100), convert
        if value > 100:
            return float(value) / 100
        return float(value)

    if not isinstance(value, str):
        return None

    # Remove currency symbols and whitespace
    cleaned = re.sub(r'[£€$,\s]', '', value.strip())

    if not cleaned or cleaned.lower() in ('n/a', 'na', 'none', 'null', ''):
        return None

    # Handle ranges like "12-15" or "12.99-15.99" - take first number
    if '-' in cleaned:
        cleaned = cleaned.split('-')[0]

    try:
        price = float(cleaned)
        # If parsed value > 100, might be cents
        if price > 100 and '.' not in value:
            return price / 100
        return price
    except (ValueError, TypeError):
        return None


def parse_timestamp(value: Any) -> Optional[datetime]:
    """
    Parse timestamp from various formats → datetime.

    Handles:
        - ISO format: "2024-01-15T10:30:00Z"
        - Date strings: "January 15, 2024", "2024-01-15"
        - Unix timestamps (seconds or milliseconds)
        - Relative: "2 weeks ago", "a month ago" (approximate)
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, (int, float)):
        try:
            # Unix timestamp - check if milliseconds
            if value > 1e12:
                value = value / 1000
            return datetime.fromtimestamp(value)
        except (ValueError, OSError):
            return None

    if not isinstance(value, str):
        return None

    value = value.strip()
    if not value or value.lower() in ('n/a', 'none', 'null'):
        return None

    # Try common formats
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%B %d, %Y",
        "%b %d, %Y",
        "%m/%d/%Y",
        "%d/%m/%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    # Handle relative dates (approximate)
    relative_patterns = [
        (r'(\d+)\s*days?\s*ago', lambda m: datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)),
        (r'(\d+)\s*weeks?\s*ago', lambda m: datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)),
        (r'(\d+)\s*months?\s*ago', lambda m: datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)),
        (r'a\s+week\s+ago', lambda m: datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)),
        (r'a\s+month\s+ago', lambda m: datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)),
    ]

    value_lower = value.lower()
    for pattern, _ in relative_patterns:
        if re.search(pattern, value_lower):
            # Return approximate date (today minus some offset)
            # Not precise, but better than None for sorting
            return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    return None


def parse_rating(value: Any) -> Optional[float]:
    """
    Parse rating → float (0-5 scale).

    Handles:
        - 4.5 → 4.5
        - "4.5" → 4.5
        - "4.5 stars" → 4.5
        - {"ratingValue": 4.5} → 4.5
        - 8 (out of 10) → 4.0
        - 90 (out of 100) → 4.5
    """
    if value is None:
        return None

    # Handle dict format from Uber Eats
    if isinstance(value, dict):
        value = value.get('ratingValue') or value.get('rating') or value.get('stars')

    if isinstance(value, (int, float)):
        rating = float(value)
        # Normalize if on different scale
        if rating > 5:
            if rating <= 10:
                rating = rating / 2  # 10-point scale → 5-point
            else:
                rating = rating / 20  # 100-point scale → 5-point
        return max(0.0, min(5.0, rating))

    if isinstance(value, str):
        # Extract first number from string
        match = re.search(r'(\d+\.?\d*)', value)
        if match:
            rating = float(match.group(1))
            if rating > 5:
                if rating <= 10:
                    rating = rating / 2
                else:
                    rating = rating / 20
            return max(0.0, min(5.0, rating))

    return None


def parse_coordinates(lat: Any, lng: Any) -> tuple[Optional[float], Optional[float]]:
    """Parse latitude and longitude to floats."""
    def to_float(v):
        if v is None:
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    return to_float(lat), to_float(lng)


def normalize_category(category: Any) -> Optional[str]:
    """Normalize menu category names for consistency."""
    if category is None:
        return None

    cat = clean_string(category)
    if cat is None:
        return None

    # Common normalizations
    normalizations = {
        'appetizers': 'appetizers',
        'appetizer': 'appetizers',
        'starters': 'appetizers',
        'starter': 'appetizers',
        'apps': 'appetizers',
        'entrees': 'entrees',
        'entree': 'entrees',
        'mains': 'entrees',
        'main courses': 'entrees',
        'main course': 'entrees',
        'desserts': 'desserts',
        'dessert': 'desserts',
        'sweets': 'desserts',
        'drinks': 'beverages',
        'drink': 'beverages',
        'beverages': 'beverages',
        'beverage': 'beverages',
        'sides': 'sides',
        'side dishes': 'sides',
        'side': 'sides',
        'salads': 'salads',
        'salad': 'salads',
        'soups': 'soups',
        'soup': 'soups',
    }

    return normalizations.get(cat, cat)


# =============================================================================
# DATAFRAME BUILDERS
# =============================================================================

def build_restaurants_df(
    restaurants_raw: list[dict],
    target_restaurant_id: Optional[str] = None,
) -> pd.DataFrame:
    """
    Build clean restaurants DataFrame.

    Input schema (flexible):
        restaurant_id: str (required)
        name: str
        lat/latitude: float
        lng/longitude: float
        address: str
        source: str
        rating: float
        review_count/user_ratings_total: int
        price_level: str
        phone/phone_number: str
        website: str
        cuisines/categories/types: list[str]

    Output columns:
        restaurant_id, name, name_clean, latitude, longitude, address,
        source, rating, review_count, price_level, phone, website,
        cuisines, is_target
    """
    if not restaurants_raw:
        return pd.DataFrame(columns=[
            'restaurant_id', 'name', 'name_clean', 'latitude', 'longitude',
            'address', 'source', 'rating', 'review_count', 'price_level',
            'phone', 'website', 'cuisines', 'is_target'
        ])

    rows = []
    for r in restaurants_raw:
        if not isinstance(r, dict):
            continue

        # Get restaurant ID (required)
        rid = safe_get(r, 'restaurant_id') or safe_get(r, 'place_id') or safe_get(r, 'id')
        if not rid:
            continue

        # Parse coordinates
        lat = safe_get(r, 'lat') or safe_get(r, 'latitude')
        lng = safe_get(r, 'lng') or safe_get(r, 'longitude')
        lat, lng = parse_coordinates(lat, lng)

        # Get cuisines/categories
        cuisines = (
            safe_get(r, 'cuisines') or
            safe_get(r, 'categories') or
            safe_get(r, 'types') or
            safe_get(r, 'cuisineList') or
            []
        )
        if isinstance(cuisines, str):
            cuisines = [cuisines]
        cuisines = [c for c in cuisines if c and isinstance(c, str)]

        # Parse price level
        price_level = safe_get(r, 'price_level')
        if isinstance(price_level, dict):
            price_level = price_level.get('value')

        row = {
            'restaurant_id': str(rid),
            'name': clean_string_preserve_case(safe_get(r, 'name') or safe_get(r, 'title')),
            'name_clean': clean_string(safe_get(r, 'name') or safe_get(r, 'title')),
            'latitude': lat,
            'longitude': lng,
            'address': clean_string_preserve_case(safe_get(r, 'address')),
            'source': clean_string(safe_get(r, 'source')) or 'unknown',
            'rating': parse_rating(safe_get(r, 'rating')),
            'review_count': safe_get(r, 'review_count') or safe_get(r, 'user_ratings_total'),
            'price_level': clean_string(str(price_level)) if price_level else None,
            'phone': clean_string_preserve_case(safe_get(r, 'phone') or safe_get(r, 'phone_number')),
            'website': safe_get(r, 'website'),
            'cuisines': cuisines if cuisines else None,
            'is_target': str(rid) == str(target_restaurant_id) if target_restaurant_id else False,
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Convert review_count to numeric
    if 'review_count' in df.columns:
        df['review_count'] = pd.to_numeric(df['review_count'], errors='coerce').astype('Int64')

    # Drop duplicates by restaurant_id, keeping first
    df = df.drop_duplicates(subset=['restaurant_id'], keep='first')

    return df


def build_menu_items_df(
    menus_raw: list[dict],
) -> pd.DataFrame:
    """
    Build clean menu items DataFrame.

    Input schema (flexible):
        restaurant_id: str (required)
        item_name/name/title: str (required)
        category: str
        description/item_description: str
        price/price_tagline: str or float
        source: str
        is_available: bool
        image_url: str

    Output columns:
        restaurant_id, item_name, item_name_clean, category, category_normalized,
        description, description_clean, price_raw, price_numeric, source,
        is_available, image_url
    """
    if not menus_raw:
        return pd.DataFrame(columns=[
            'restaurant_id', 'item_name', 'item_name_clean', 'category',
            'category_normalized', 'description', 'description_clean',
            'price_raw', 'price_numeric', 'source', 'is_available', 'image_url'
        ])

    rows = []
    for m in menus_raw:
        if not isinstance(m, dict):
            continue

        # Get required fields
        rid = safe_get(m, 'restaurant_id') or safe_get(m, 'place_id')
        item_name_raw = (
            safe_get(m, 'item_name') or
            safe_get(m, 'name') or
            safe_get(m, 'title')
        )

        # Skip if no restaurant_id or item_name
        if not rid or not item_name_raw:
            continue

        # Clean item name and skip if it's empty/invalid
        item_name = clean_string_preserve_case(item_name_raw)
        if not item_name:
            continue

        # Get price
        price_raw = safe_get(m, 'price') or safe_get(m, 'price_tagline') or safe_get(m, 'priceTagline')

        # Get description
        description = (
            safe_get(m, 'description') or
            safe_get(m, 'item_description') or
            safe_get(m, 'itemDescription')
        )

        row = {
            'restaurant_id': str(rid),
            'item_name': item_name,
            'item_name_clean': clean_string(item_name_raw),
            'category': clean_string_preserve_case(safe_get(m, 'category')),
            'category_normalized': normalize_category(safe_get(m, 'category')),
            'description': clean_string_preserve_case(description),
            'description_clean': clean_string(description),
            'price_raw': str(price_raw) if price_raw else None,
            'price_numeric': parse_price(price_raw),
            'source': clean_string(safe_get(m, 'source')) or 'unknown',
            'is_available': safe_get(m, 'is_available', True),
            'image_url': safe_get(m, 'image_url'),
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Drop exact duplicates (same restaurant + item + price)
    if not df.empty:
        df = df.drop_duplicates(
            subset=['restaurant_id', 'item_name_clean', 'price_numeric'],
            keep='first'
        )

    return df


def build_reviews_df(
    reviews_raw: list[dict],
) -> pd.DataFrame:
    """
    Build clean reviews DataFrame.

    Input schema (flexible):
        restaurant_id: str (required)
        rating/stars: float
        text/review_text: str
        timestamp/date/published_at: str or datetime
        author/author_name/reviewer: str
        source: str
        likes/likes_count: int
        is_local_guide: bool

    Output columns:
        restaurant_id, rating, text, text_clean, timestamp, author,
        source, likes, is_local_guide, text_length
    """
    if not reviews_raw:
        return pd.DataFrame(columns=[
            'restaurant_id', 'rating', 'text', 'text_clean', 'timestamp',
            'author', 'source', 'likes', 'is_local_guide', 'text_length'
        ])

    rows = []
    for r in reviews_raw:
        if not isinstance(r, dict):
            continue

        # Get restaurant ID (required)
        rid = safe_get(r, 'restaurant_id') or safe_get(r, 'place_id')
        if not rid:
            continue

        # Get text
        text = (
            safe_get(r, 'text') or
            safe_get(r, 'review_text') or
            safe_get(r, 'reviewText') or
            safe_get(r, 'comment')
        )

        # Get timestamp
        timestamp = (
            safe_get(r, 'timestamp') or
            safe_get(r, 'date') or
            safe_get(r, 'published_at') or
            safe_get(r, 'publishedAt') or
            safe_get(r, 'publishAt')
        )

        # Get author
        author = (
            safe_get(r, 'author') or
            safe_get(r, 'author_name') or
            safe_get(r, 'reviewer') or
            safe_get(r, 'name')
        )

        # Get rating
        rating = safe_get(r, 'rating') or safe_get(r, 'stars')

        text_clean = clean_string(text)

        row = {
            'restaurant_id': str(rid),
            'rating': parse_rating(rating),
            'text': clean_string_preserve_case(text),
            'text_clean': text_clean,
            'timestamp': parse_timestamp(timestamp),
            'author': clean_string_preserve_case(author),
            'source': clean_string(safe_get(r, 'source')) or 'unknown',
            'likes': safe_get(r, 'likes') or safe_get(r, 'likes_count') or safe_get(r, 'likesCount') or 0,
            'is_local_guide': safe_get(r, 'is_local_guide') or safe_get(r, 'isLocalGuide') or False,
            'text_length': len(text_clean) if text_clean else 0,
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Convert likes to int
    if 'likes' in df.columns:
        df['likes'] = pd.to_numeric(df['likes'], errors='coerce').fillna(0).astype(int)

    # Sort by timestamp descending (most recent first)
    if not df.empty and 'timestamp' in df.columns:
        df = df.sort_values('timestamp', ascending=False, na_position='last')

    return df


def build_competitors_df(
    competitors_raw: list[dict],
    restaurants_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Build clean competitors DataFrame (links between restaurants).

    Input schema:
        target_restaurant_id: str (required)
        competitor_restaurant_id: str (required)
        distance_meters: float
        rank: int (optional, for ordering)

    Output columns:
        target_restaurant_id, competitor_restaurant_id, distance_meters,
        distance_km, rank

    If restaurants_df provided, also adds:
        competitor_name, competitor_rating, competitor_review_count
    """
    if not competitors_raw:
        cols = [
            'target_restaurant_id', 'competitor_restaurant_id',
            'distance_meters', 'distance_km', 'rank'
        ]
        if restaurants_df is not None:
            cols.extend(['competitor_name', 'competitor_rating', 'competitor_review_count'])
        return pd.DataFrame(columns=cols)

    rows = []
    for i, c in enumerate(competitors_raw):
        if not isinstance(c, dict):
            continue

        target_id = safe_get(c, 'target_restaurant_id')
        competitor_id = safe_get(c, 'competitor_restaurant_id') or safe_get(c, 'place_id')

        if not target_id or not competitor_id:
            continue

        # Parse distance
        distance = safe_get(c, 'distance_meters') or safe_get(c, 'distance')
        if distance is not None:
            try:
                distance = float(distance)
            except (ValueError, TypeError):
                distance = None

        row = {
            'target_restaurant_id': str(target_id),
            'competitor_restaurant_id': str(competitor_id),
            'distance_meters': distance,
            'distance_km': round(distance / 1000, 2) if distance else None,
            'rank': safe_get(c, 'rank') or (i + 1),
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Enrich with restaurant data if available
    if restaurants_df is not None and not df.empty and not restaurants_df.empty:
        restaurant_lookup = restaurants_df.set_index('restaurant_id')[
            ['name', 'rating', 'review_count']
        ].to_dict('index')

        df['competitor_name'] = df['competitor_restaurant_id'].apply(
            lambda x: restaurant_lookup.get(x, {}).get('name')
        )
        df['competitor_rating'] = df['competitor_restaurant_id'].apply(
            lambda x: restaurant_lookup.get(x, {}).get('rating')
        )
        df['competitor_review_count'] = df['competitor_restaurant_id'].apply(
            lambda x: restaurant_lookup.get(x, {}).get('review_count')
        )

    # Sort by distance
    if not df.empty and 'distance_meters' in df.columns:
        df = df.sort_values('distance_meters', ascending=True, na_position='last')
        df['rank'] = range(1, len(df) + 1)

    return df


# =============================================================================
# ORCHESTRATOR
# =============================================================================

def build_all_tables(
    restaurants_raw: list[dict],
    menus_raw: list[dict],
    reviews_raw: list[dict],
    competitors_raw: list[dict],
    target_restaurant_id: Optional[str] = None,
) -> dict[str, pd.DataFrame]:
    """
    Build all cleaned DataFrames from raw data.

    Args:
        restaurants_raw: List of restaurant dicts
        menus_raw: List of menu item dicts
        reviews_raw: List of review dicts
        competitors_raw: List of competitor relationship dicts
        target_restaurant_id: ID of the target restaurant (for is_target flag)

    Returns:
        Dict with keys: 'restaurants', 'menu_items', 'reviews', 'competitors'
    """
    # Handle None inputs
    restaurants_raw = restaurants_raw or []
    menus_raw = menus_raw or []
    reviews_raw = reviews_raw or []
    competitors_raw = competitors_raw or []

    # Build tables in order (restaurants first for competitor enrichment)
    restaurants_df = build_restaurants_df(restaurants_raw, target_restaurant_id)
    menu_items_df = build_menu_items_df(menus_raw)
    reviews_df = build_reviews_df(reviews_raw)
    competitors_df = build_competitors_df(competitors_raw, restaurants_df)

    return {
        'restaurants': restaurants_df,
        'menu_items': menu_items_df,
        'reviews': reviews_df,
        'competitors': competitors_df,
    }


# =============================================================================
# DATA QUALITY HELPERS
# =============================================================================

def get_data_quality_report(tables: dict[str, pd.DataFrame]) -> dict:
    """
    Generate a data quality report for the cleaned tables.

    Returns dict with row counts, null percentages, and basic stats.
    """
    report = {}

    for name, df in tables.items():
        if df.empty:
            report[name] = {'row_count': 0, 'columns': []}
            continue

        col_stats = []
        for col in df.columns:
            null_count = df[col].isna().sum()
            null_pct = round(null_count / len(df) * 100, 1)

            stat = {
                'column': col,
                'dtype': str(df[col].dtype),
                'null_count': int(null_count),
                'null_pct': null_pct,
            }

            # Add numeric stats
            if pd.api.types.is_numeric_dtype(df[col]):
                stat['min'] = df[col].min()
                stat['max'] = df[col].max()
                stat['mean'] = round(df[col].mean(), 2) if not df[col].isna().all() else None

            col_stats.append(stat)

        report[name] = {
            'row_count': len(df),
            'columns': col_stats,
        }

    return report


def print_data_quality_report(tables: dict[str, pd.DataFrame]) -> None:
    """Print a formatted data quality report."""
    report = get_data_quality_report(tables)

    print("=" * 60)
    print("DATA QUALITY REPORT")
    print("=" * 60)

    for table_name, stats in report.items():
        print(f"\n{table_name.upper()}: {stats['row_count']} rows")
        print("-" * 40)

        if not stats['columns']:
            print("  (empty table)")
            continue

        for col in stats['columns']:
            null_str = f"{col['null_pct']}% null" if col['null_pct'] > 0 else "complete"
            extra = ""
            if 'mean' in col and col['mean'] is not None:
                extra = f" | range: {col['min']}-{col['max']}, mean: {col['mean']}"
            print(f"  {col['column']}: {col['dtype']} ({null_str}){extra}")
