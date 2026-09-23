import pandas as pd

df_s = pd.read_csv("data/raw/schemes.csv")
df_u = pd.read_csv("data/raw/updated_data.csv")

s_slugs = set(df_s['slug'].dropna().str.lower().str.strip())
u_slugs = set(df_u['slug'].dropna().str.lower().str.strip())
u_only_slugs = u_slugs - s_slugs

u_only_df = df_u[df_u['slug'].str.lower().str.strip().isin(u_only_slugs)]
print(f"Total schemes in updated_data not in schemes.csv: {len(u_only_df)}")
print(u_only_df[['scheme_name', 'slug', 'level', 'schemeCategory']].head(10))

# Check if their names exist in schemes.csv under a different slug
s_names = set(df_s['scheme_name'].dropna().str.lower().str.strip())
matched_by_name = u_only_df[u_only_df['scheme_name'].str.lower().str.strip().isin(s_names)]
print(f"Of these 79 slugs, {len(matched_by_name)} match a scheme name in schemes.csv under a different slug!")
if len(matched_by_name) > 0:
    print("Example name matches with different slugs:")
    for _, r in matched_by_name.head(5).iterrows():
        s_match = df_s[df_s['scheme_name'].str.lower().str.strip() == r['scheme_name'].lower().strip()]
        print(f"  updated_data slug: {r['slug']} vs schemes.csv slug: {s_match['slug'].values[0]} | Name: {r['scheme_name']}")
