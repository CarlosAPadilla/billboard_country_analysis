import pandas as pd
from playwright.sync_api import sync_playwright
import numpy as np
import requests
import time
import re
from bs4 import BeautifulSoup
import gender_guesser.detector as gender
import matplotlib.pyplot as plt
import seaborn as sns


pw = sync_playwright().start()
chrome = pw.chromium.launch(headless=False)
context = chrome.new_context(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
page = context.new_page()

page.goto('https://www.billboard.com/lists/best-country-songs-all-time/')
page.wait_for_timeout(60000)

slides = page.locator('.c-gallery-vertical__slide-wrapper')
slides_count = slides.count()

song_list = []

for i in range(slides_count):
    title = slides.nth(i).locator('h2').inner_text()
    
    if ',' in title:
        artist = title.split(',')[0]
        song = title.split(',')[1].strip('"').strip("'")
        
        song_df = pd.DataFrame({'artist': [artist], 'song': [song]})
        song_list.append(song_df)

df = pd.concat(song_list)
df['rank'] = range(1, len(df) + 1)
df = df[['rank', 'artist', 'song']]
df.reset_index(drop=True, inplace=True)

page.close()
context.close()
chrome.close()
pw.stop()


df['artist'] = df['artist'].str.replace(r'\n|\t', '', regex=True)
df['artist'] = df['artist'].str.replace(r' [Ff]eaturing.*', '', regex=True)
df['artist'] = df['artist'].str.replace(r'\[.*?\]', '', regex=True)
df['artist'] = df['artist'].str.replace(r'^\s+|\s+$', '', regex=True)
df['artist'] = df['artist'].str.replace(r'\s{2,}', ' ', regex=True)

df['song'] = df['song'].str.replace(r'\n|\t', '', regex=True)
df['song'] = df['song'].str.replace(r'\(.*?\)', '', regex=True)
df['song'] = df['song'].str.replace(r'\[.*?\]', '', regex=True)
df['song'] = df['song'].str.replace(r'^\s+|\s+$', '', regex=True)
df['song'] = df['song'].str.replace(r'\s{2,}', ' ', regex=True)


df['search_artist'] = df['artist'].str.lower()
df['search_artist'] = df['search_artist'].str.replace(r' ', '%20', regex=True)

df['search_song'] = df['song'].str.lower()
df['search_song'] = df['search_song'].str.replace(r' ', '%20', regex=True)

df['query'] = df['search_artist'] + '%20' + df['search_song']
df['query'] = df['query'].str.replace(r'&', 'and', regex=True)
df['query'] = df['query'].str.replace(r'%20{2,}', '%20', regex=True)

df['genius_link'] = 'https://api.genius.com/search?q=' + df['query']



id = 'YOUR_ID_HERE'
secret = 'YOUR_GENIUS_API_TOKEN_HERE'
headers = {'Authorization': 'Bearer ' + secret}


def get_release_year(link):
    
    time.sleep(np.random.uniform(.1, .5, 1)[0])
    
    try:
        req_json = requests.get(link, headers=headers).json()
        song_id = req_json['response']['hits'][0]['result']['id']
        
        song_link = 'https://api.genius.com/songs/' + str(song_id)
        req_json = requests.get(song_link, headers=headers).json()
        
        release_date = req_json['response']['song'].get('release_date_for_display', None)
        
        if not release_date:
            release_components = req_json['response']['song'].get('release_date_components', {})
            year = release_components.get('year', None)
        else:
            year_match = re.search(r'\b(19\d{2}|20\d{2})\b', release_date)
            year = year_match.group(1) if year_match else None
        
        return pd.DataFrame({'release_year': [year], 'query': [link]}, index=[0])
        
    except:
        return pd.DataFrame({'release_year': [None], 'query': [link]}, index=[0])


release_years = []

for i, link in enumerate(df['genius_link']):
    release_years.append(get_release_year(link))

all_release_years = pd.concat(release_years)

df = df.merge(all_release_years, left_on='genius_link', right_on='query', how='left')

df = df[['rank', 'artist', 'song', 'release_year']]


df['release_year'] = pd.to_numeric(df['release_year'], errors='coerce').astype('Int64')

df.to_csv('billboard_with_years.csv', index=False)


df = pd.read_csv('billboard_with_years.csv')

missing_years = df[df['release_year'].isna()]
missing_years

df.loc[df['rank'] == 15, 'release_year'] = 2000
df.loc[df['rank'] == 68, 'release_year'] = 1961

df['release_year'] = df['release_year'].astype(int)

df['rank'] = range(100, 0, -1)

df.loc[df['artist'] == 'Tom T. Hall', 'song'] = '(Old Dogs, Children and) Watermelon Wine'

df.to_csv('billboard_with_years.csv', index=False)



df = pd.read_csv('billboard_with_years.csv')

d = gender.Detector()

def get_gender(artist):
    
    if any(keyword in artist for keyword in ['&', ' and ', 'feat', 'Family', 'Flatts', 
                                               'Town', 'Dunn', 'Chicks', 'Band', 'Judds']):
        return 'Group'
    
    first_name = artist.split()[0]
    
    guess = d.get_gender(first_name)
    
    if guess in ['male', 'mostly_male']:
        return 'Male'
    elif guess in ['female', 'mostly_female']:
        return 'Female'
    else:
        return 'Unknown'

df['gender'] = df['artist'].apply(get_gender)

df[df['gender'] == 'Unknown']

df.loc[df['artist'] == 'Skeeter Davis', 'gender'] = 'Female'
df.loc[df['artist'] == 'Old Crow Medicine Show', 'gender'] = 'Group'
df.loc[df['artist'] == 'DeFord Bailey', 'gender'] = 'Male'
df.loc[df['artist'] == 'Lady A', 'gender'] = 'Group'
df.loc[df['artist'] == 'Emmylou Harris', 'gender'] = 'Female'
df.loc[df['artist'] == 'Webb Pierce', 'gender'] = 'Male'
df.loc[df['artist'] == 'Alabama', 'gender'] = 'Group'
df.loc[df['artist'] == 'Lefty Frizzell', 'gender'] = 'Male'

df.to_csv('billboard_with_years.csv', index=False)

print(df['gender'].value_counts())



df = pd.read_csv('billboard_with_years.csv')

df['decade'] = (df['release_year'] // 10) * 10

df.to_csv('billboard_with_years.csv', index=False)

decade_counts = df.groupby('decade').size()

print(decade_counts)



df = pd.read_csv('billboard_with_years.csv')

decade_counts = df.groupby('decade').size().reset_index(name='count')
gender_counts = df['gender'].value_counts().reset_index()
gender_counts.columns = ['gender', 'count']
decade_gender = df.groupby(['decade', 'gender']).size().reset_index(name='count')
decade_gender_pivot = decade_gender.pivot(index='decade', columns='gender', values='count').fillna(0)



plt.figure(figsize=(14, 8))
sns.barplot(data=decade_counts, x='decade', y='count', color='steelblue')
plt.title('Billboard Top 100 Country Songs by Decade')
plt.xlabel('Decade')
plt.ylabel('Number of Songs')
plt.xticks(ticks=range(len(decade_counts)), labels=[str(int(d)) + 's' for d in decade_counts['decade']], rotation=45)
plt.savefig('songs_by_decade.png', dpi=300, bbox_inches='tight')
plt.show()



plt.figure(figsize=(14, 8))
sns.barplot(data=gender_counts, x='gender', y='count', palette=['steelblue', 'salmon', 'mediumseagreen'])
plt.title('Billboard Top 100 Country Songs by Gender')
plt.xlabel('Artist Classification')
plt.ylabel('Number of Songs')
plt.savefig('songs_by_gender.png', dpi=300, bbox_inches='tight')
plt.show()



plt.figure(figsize=(14, 8))
decade_gender_pivot.plot(kind='bar', stacked=True, color=['salmon', 'mediumseagreen', 'steelblue'], width=0.6, ax=plt.gca())
plt.title('Billboard Top 100 Country Songs: Gender Breakdown by Decade')
plt.xlabel('Decade')
plt.ylabel('Number of Songs')
plt.xticks(ticks=range(len(decade_gender_pivot)), labels=[str(int(d)) + 's' for d in decade_gender_pivot.index], rotation=45)
plt.legend(title='Artist Classification')
plt.savefig('gender_by_decade.png', dpi=300, bbox_inches='tight')
plt.show()