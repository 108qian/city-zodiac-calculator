import streamlit as st
import requests
from datetime import datetime

st.set_page_config(page_title="City Founding Chinese Zodiac", layout="centered")

st.title("City Founding Year → Chinese Zodiac Calculator")
st.markdown("Enter a city name. Add country if results are wrong or missing (helps disambiguate).")

# Chinese zodiac cycle (index 0 = Monkey, matches (year % 12 == 4) for modern reference)
ZODIAC = [
    "Monkey", "Rooster", "Dog", "Pig", "Rat", "Ox",
    "Tiger", "Rabbit", "Dragon", "Snake", "Horse", "Goat"
]

def get_chinese_zodiac(year: int) -> str:
    if year == 0:
        return "—"
    # Handle BC (negative years) by shifting modulo correctly
    idx = (year - 4) % 12   # 4 BC = Rat, 5 BC = Pig, etc. — cycle continues backward
    if idx < 0:
        idx += 12
    return ZODIAC[idx]

def fetch_founding_year(city: str, country: str = None) -> tuple:
    sparql = """
    SELECT ?city ?cityLabel ?inception ?inceptionTime WHERE {
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
      
      ?city wdt:P31/wdt:P279* wd:Q515.          # city or subclass
      ?city rdfs:label ?cityLabel.
      FILTER(STR(?cityLabel) = "%s" || LCASE(STR(?cityLabel)) = LCASE("%s"))
      
      OPTIONAL { ?city wdt:P571 ?inception. }
      
      FILTER EXISTS { ?city wdt:P17 ?country. }
      %s
    }
    ORDER BY DESC(?inception)
    LIMIT 1
    """ % (city, city,
           '?country rdfs:label "%s"@en .' % country if country else "")

    url = "https://query.wikidata.org/sparql"
    headers = {"Accept": "application/sparql-results+json"}
    try:
        r = requests.get(url, params={"query": sparql}, headers=headers, timeout=12)
        r.raise_for_status()
        data = r.json()

        bindings = data.get("results", {}).get("bindings", [])
        if not bindings:
            return None, "No founding date found for this city (or spelling/country mismatch). Try adding country."

        item = bindings[0]
        inception = item.get("inception", {}).get("value")
        if not inception:
            return None, "Found city but no inception/founding date recorded."

        # Parse year (handles +YYYY-MM-DD and -YYYY-MM-DD for BC)
        if "T" in inception:
            dt_str = inception.split("T")[0]
        else:
            dt_str = inception

        if dt_str.startswith("-"):
            year = -int(dt_str[1:5])
        else:
            year = int(dt_str[:4])

        city_label = item.get("cityLabel", {}).get("value", city)
        return year, f"({city_label})"

    except Exception as e:
        return None, f"Error reaching Wikidata: {str(e)}"

# UI
col1, col2 = st.columns([3, 2])

with col1:
    city_name = st.text_input("City name", value="New Brighton", key="city")

with col2:
    country_name = st.text_input("Country (optional)", value="United States", key="country")

if st.button("Calculate Zodiac", type="primary"):
    if not city_name.strip():
        st.warning("Please enter a city name.")
    else:
        with st.spinner("Querying Wikidata..."):
            year, extra = fetch_founding_year(city_name.strip(), country_name.strip() or None)

        if year is not None:
            zodiac = get_chinese_zodiac(year)
            st.success(f"**{city_name}** was founded in **{year}** {extra}")
            st.markdown(f"### Chinese Zodiac: **{zodiac}** 🐉")
            st.caption(f"(Cycle continues backward into BC years)")
        else:
            st.error(extra)

st.markdown("---")
st.caption("Prototype using Wikidata (P571 = inception). Some cities have approximate, disputed, or missing dates. Results best for major/well-documented cities.")
st.caption(f"Last tested: {datetime.now().strftime('%Y-%m')}")
