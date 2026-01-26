"""
LLM-powered menu grouping for price analysis.

Groups menu items from target restaurant and competitors into:
- Narrow groups: Specific item types (e.g., "burgers", "lo mein", "spring rolls")
- Wide groups: Broad categories (e.g., "mains", "appetizers", "desserts")

Purpose: Enable price comparison across restaurants for similar items.

Usage:
    from app.competitor_analysis.menu_grouper import group_menus_for_analysis

    result = await group_menus_for_analysis(
        menu_items_df=menu_items_df,
        restaurants_df=restaurants_df,
    )

    # result["narrow_groups"]["burgers"] = [
    #     {"restaurant_name": "Target Restaurant", "item_name": "Classic Burger", "price": 12.99, "is_target": True},
    #     {"restaurant_name": "Competitor A", "item_name": "Beef Burger", "price": 10.99, "is_target": False},
    # ]
"""

import os
import json
from typing import Optional

import pandas as pd
from openai import AsyncOpenAI


# Fixed wide categories for consistency
WIDE_CATEGORIES = [
    "appetizers",
    "mains",
    "proteins",
    "sides",
    "salads",
    "soups",
    "desserts",
    "drinks",
    "light_snacks",
    "combo_meals",
    "other",
]


def _prepare_menu_items_for_llm(
    menu_items_df: pd.DataFrame,
    restaurants_df: pd.DataFrame,
) -> list[dict]:
    """
    Prepare menu items for LLM processing.

    Returns list of items with restaurant context.
    """
    if menu_items_df.empty:
        return []

    # Create restaurant lookup
    restaurant_lookup = {}
    if not restaurants_df.empty:
        for _, row in restaurants_df.iterrows():
            restaurant_lookup[row['restaurant_id']] = {
                'name': row['name'],
                'is_target': row.get('is_target', False),
            }

    items = []
    for idx, row in menu_items_df.iterrows():
        rid = row['restaurant_id']
        restaurant_info = restaurant_lookup.get(rid, {'name': 'Unknown', 'is_target': False})

        item = {
            'id': str(idx),
            'restaurant_id': rid,
            'restaurant_name': restaurant_info['name'],
            'is_target': restaurant_info['is_target'],
            'item_name': row.get('item_name') or row.get('item_name_clean') or '',
            'category': row.get('category') or row.get('category_normalized') or '',
            'description': row.get('description') or row.get('description_clean') or '',
            'price': row.get('price_numeric'),
        }
        items.append(item)

    return items


def _build_grouping_prompt(items: list[dict]) -> str:
    """Build the prompt for menu grouping."""

    # Format items for the prompt
    items_text = []
    for item in items:
        price_str = f"${item['price']:.2f}" if item['price'] else "N/A"
        desc_raw = item.get('description')
        # Handle NaN, None, and empty strings
        if desc_raw and isinstance(desc_raw, str) and desc_raw.strip():
            desc = f" - {desc_raw[:100]}"
        else:
            desc = ""
        items_text.append(
            f"[{item['id']}] {item['item_name']} ({price_str}) from {item['restaurant_name']}{desc}"
        )

    items_list = "\n".join(items_text)

    prompt = f"""You are a restaurant menu analyst. Your task is to group menu items from multiple restaurants for price comparison.

## Menu Items to Analyze:
{items_list}

## Your Task:
For each menu item, assign:
1. **narrow_group**: A specific, descriptive group name for similar items across restaurants.
   - Examples: "beef burgers", "chicken fried rice", "spring rolls", "pad thai", "caesar salad"
   - Group items that are essentially the same dish or very close variants
   - Use lowercase, descriptive names (2-4 words typically)
   - Be specific enough for meaningful price comparison

2. **wide_group**: One of these fixed categories:
   - "appetizers" (starters, small plates, dim sum, wings)
   - "mains" (entrees, main courses, large plates)
   - "proteins" (standalone protein dishes, grilled meats)
   - "sides" (rice, noodles as sides, vegetables)
   - "salads" (salads, light bowls)
   - "soups" (soups, broths)
   - "desserts" (sweets, pastries, ice cream)
   - "drinks" (beverages, bubble tea, sodas)
   - "light_snacks" (small bites, chips, bread)
   - "combo_meals" (meal deals, family packs)
   - "other" (if nothing else fits)

## Output Format:
Return a JSON array with one object per item:
```json
[
  {{"id": "0", "narrow_group": "general tso chicken", "wide_group": "mains"}},
  {{"id": "1", "narrow_group": "spring rolls", "wide_group": "appetizers"}},
  ...
]
```

Important:
- Use the exact item ID from the input
- Create narrow groups that enable meaningful price comparison
- Items that are unique should still get a descriptive narrow_group name
- Output ONLY the JSON array, no other text"""

    return prompt


async def _call_openai_for_grouping(
    items: list[dict],
    api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
) -> list[dict]:
    """
    Call OpenAI API to get menu item groupings.

    Returns list of {id, narrow_group, wide_group} dicts.
    """
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var.")

    client = AsyncOpenAI(api_key=api_key)

    prompt = _build_grouping_prompt(items)

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a precise menu analyst. Output only valid JSON arrays."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.1,  # Low temperature for consistency
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content

    # Parse the JSON response
    try:
        result = json.loads(content)
        # Handle both {"items": [...]} and [...] formats
        if isinstance(result, dict):
            result = result.get('items') or result.get('groupings') or list(result.values())[0]
        return result
    except json.JSONDecodeError as e:
        print(f"Failed to parse LLM response: {e}")
        print(f"Response was: {content[:500]}")
        return []


def _build_grouped_output(
    items: list[dict],
    groupings: list[dict],
) -> dict:
    """
    Build the final grouped output structure.

    Returns:
        {
            "narrow_groups": {
                "burgers": [
                    {"restaurant_name": "...", "item_name": "...", "price": 12.99, "is_target": True},
                    ...
                ],
                ...
            },
            "wide_groups": {
                "mains": [...],
                ...
            },
            "items": [...]  # All items with their groupings
        }
    """
    # Create lookup from groupings
    grouping_lookup = {g['id']: g for g in groupings}

    # Enrich items with groupings
    enriched_items = []
    for item in items:
        grouping = grouping_lookup.get(item['id'], {})
        enriched = {
            **item,
            'narrow_group': grouping.get('narrow_group', 'uncategorized'),
            'wide_group': grouping.get('wide_group', 'other'),
        }
        enriched_items.append(enriched)

    # Build narrow groups
    narrow_groups = {}
    for item in enriched_items:
        group_name = item['narrow_group']
        if group_name not in narrow_groups:
            narrow_groups[group_name] = []

        narrow_groups[group_name].append({
            'restaurant_id': item['restaurant_id'],
            'restaurant_name': item['restaurant_name'],
            'item_name': item['item_name'],
            'price': item['price'],
            'is_target': item['is_target'],
            'description': item.get('description'),
        })

    # Build wide groups
    wide_groups = {}
    for item in enriched_items:
        group_name = item['wide_group']
        if group_name not in wide_groups:
            wide_groups[group_name] = []

        wide_groups[group_name].append({
            'restaurant_id': item['restaurant_id'],
            'restaurant_name': item['restaurant_name'],
            'item_name': item['item_name'],
            'price': item['price'],
            'is_target': item['is_target'],
            'narrow_group': item['narrow_group'],
        })

    # Sort each group: target first, then by price
    def sort_group(items_list):
        return sorted(
            items_list,
            key=lambda x: (not x['is_target'], x['price'] or float('inf'))
        )

    narrow_groups = {k: sort_group(v) for k, v in narrow_groups.items()}
    wide_groups = {k: sort_group(v) for k, v in wide_groups.items()}

    # Sort group names alphabetically
    narrow_groups = dict(sorted(narrow_groups.items()))
    wide_groups = dict(sorted(wide_groups.items()))

    return {
        'narrow_groups': narrow_groups,
        'wide_groups': wide_groups,
        'items': enriched_items,
        'stats': {
            'total_items': len(enriched_items),
            'narrow_group_count': len(narrow_groups),
            'wide_group_count': len(wide_groups),
            'target_items': sum(1 for i in enriched_items if i['is_target']),
            'competitor_items': sum(1 for i in enriched_items if not i['is_target']),
        }
    }


async def group_menus_for_analysis(
    menu_items_df: pd.DataFrame,
    restaurants_df: pd.DataFrame,
    api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
) -> dict:
    """
    Group menu items from target and competitors for price analysis.

    Args:
        menu_items_df: Cleaned menu items DataFrame
        restaurants_df: Cleaned restaurants DataFrame with is_target flag
        api_key: OpenAI API key (or set OPENAI_API_KEY env var)
        model: OpenAI model to use (default: gpt-4o-mini for cost efficiency)

    Returns:
        {
            "narrow_groups": {
                "group_name": [
                    {"restaurant_name": "...", "item_name": "...", "price": 12.99, "is_target": True/False},
                    ...
                ],
                ...
            },
            "wide_groups": {
                "category_name": [...],
                ...
            },
            "items": [...],  # All items with groupings
            "stats": {...}   # Summary statistics
        }
    """
    # Prepare items for LLM
    items = _prepare_menu_items_for_llm(menu_items_df, restaurants_df)

    if not items:
        return {
            'narrow_groups': {},
            'wide_groups': {},
            'items': [],
            'stats': {
                'total_items': 0,
                'narrow_group_count': 0,
                'wide_group_count': 0,
                'target_items': 0,
                'competitor_items': 0,
            }
        }

    print(f"Grouping {len(items)} menu items with LLM...")

    # Get groupings from LLM
    groupings = await _call_openai_for_grouping(items, api_key, model)

    print(f"LLM returned {len(groupings)} groupings")

    # Build output structure
    result = _build_grouped_output(items, groupings)

    print(f"Created {result['stats']['narrow_group_count']} narrow groups, "
          f"{result['stats']['wide_group_count']} wide groups")

    return result


def get_price_comparison_summary(grouped_data: dict) -> pd.DataFrame:
    """
    Generate a price comparison summary from grouped data.

    Returns DataFrame with:
        narrow_group, target_price, competitor_avg, competitor_min, competitor_max,
        price_diff, price_diff_pct
    """
    rows = []

    for group_name, items in grouped_data['narrow_groups'].items():
        target_items = [i for i in items if i['is_target']]
        competitor_items = [i for i in items if not i['is_target'] and i['price']]

        if not target_items:
            continue

        target_price = target_items[0]['price']
        if target_price is None:
            continue

        comp_prices = [i['price'] for i in competitor_items if i['price']]

        if comp_prices:
            comp_avg = sum(comp_prices) / len(comp_prices)
            comp_min = min(comp_prices)
            comp_max = max(comp_prices)
            price_diff = target_price - comp_avg
            price_diff_pct = (price_diff / comp_avg) * 100 if comp_avg else 0
        else:
            comp_avg = comp_min = comp_max = None
            price_diff = price_diff_pct = None

        rows.append({
            'narrow_group': group_name,
            'target_item': target_items[0]['item_name'],
            'target_price': target_price,
            'competitor_count': len(competitor_items),
            'competitor_avg': round(comp_avg, 2) if comp_avg else None,
            'competitor_min': comp_min,
            'competitor_max': comp_max,
            'price_diff': round(price_diff, 2) if price_diff else None,
            'price_diff_pct': round(price_diff_pct, 1) if price_diff_pct else None,
        })

    df = pd.DataFrame(rows)

    # Sort by price difference (most expensive relative to competitors first)
    if not df.empty and 'price_diff_pct' in df.columns:
        df = df.sort_values('price_diff_pct', ascending=False, na_position='last')

    return df


def get_category_summary(grouped_data: dict) -> pd.DataFrame:
    """
    Generate a category-level price summary.

    Returns DataFrame with:
        wide_group, target_avg, target_count, competitor_avg, competitor_count
    """
    rows = []

    for category, items in grouped_data['wide_groups'].items():
        target_items = [i for i in items if i['is_target'] and i['price']]
        competitor_items = [i for i in items if not i['is_target'] and i['price']]

        target_prices = [i['price'] for i in target_items]
        comp_prices = [i['price'] for i in competitor_items]

        rows.append({
            'wide_group': category,
            'target_count': len(target_items),
            'target_avg': round(sum(target_prices) / len(target_prices), 2) if target_prices else None,
            'target_min': min(target_prices) if target_prices else None,
            'target_max': max(target_prices) if target_prices else None,
            'competitor_count': len(competitor_items),
            'competitor_avg': round(sum(comp_prices) / len(comp_prices), 2) if comp_prices else None,
            'competitor_min': min(comp_prices) if comp_prices else None,
            'competitor_max': max(comp_prices) if comp_prices else None,
        })

    df = pd.DataFrame(rows)

    # Sort by target item count
    if not df.empty:
        df = df.sort_values('target_count', ascending=False)

    return df
