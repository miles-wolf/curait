import json
import random
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import ast

def load_json_to_dataframe(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    df = pd.DataFrame(data)
    return df

# see if artists for a song match the artists we're looking for
def artist_match(row, artists):
    # Ensure row['artists'] is a list of dictionaries
    if isinstance(row['artists'], str):
        artists_list = ast.literal_eval(row['artists'])
    else:
        artists_list = row['artists']
    
    # Convert artist names to lowercase for case-insensitive comparison
    artists = [artist.lower() for artist in artists]
    return any(artist_dict['artist_name'].lower() in artists for artist_dict in artists_list)

def get_song_ids(song_titles, song_artists, spotify_df, sp):
    song_ids = []
    for title, artist in zip(song_titles, song_artists):
        # Convert title to lowercase for case-insensitive comparison
        title = title.lower()
        
        # Filter the DataFrame for rows where the track name matches the title (case-insensitive)
        title_matches = spotify_df[spotify_df['track_name'].str.lower() == title]
        
        # Check if any of the artist names match (case-insensitive)
        found = False
        for index, row in title_matches.iterrows():
            if artist_match(row, artist):
                song_ids.append(row['track_id'])
                found = True
                break  # Stop searching once a match is found
        
        # If not found in local database, search on Spotify
        if not found:
            results = sp.search(q=f"track:{title} artist:{artist}", type='track', limit=1)
            if results['tracks']['items']:
                track = results['tracks']['items'][0]
                song_ids.append(track['id'])
    
    return song_ids

def get_songs_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    song_titles = []
    song_artists = []
    song_ids = []
    artist_ids = []
    albums = []
    genres = []
    years = []
    notes = []
    
    for song in data:
        song_titles.append(song.get('title', ''))
        song_artists.append(song.get('artists', []))
        song_ids.append(song.get('song_id', ''))  # This will be empty as per your requirement
        artist_ids.append(song.get('artist_ids', []))  # This will be empty as per your requirement
        albums.append(song.get('album', ''))
        genres.append(song.get('genres', []))
        years.append(song.get('year', ''))
        notes.append(song.get('notes', ''))
    
    song_list = {
        'song_titles': song_titles,
        'song_artists': song_artists,
        'song_ids': song_ids,
        'artist_ids': artist_ids,
        'albums': albums,
        'genres': genres,
        'years': years,
        'notes': notes
    }
    
    return song_list

def get_client_info():
    client_id = "bed53f6a46fe4828a9e2a7c6cf2ab1a6"
    client_secret = "524c889675614af9808d8c34e1ae88d5"
    redirect_uri = 'http://localhost'
    scope = "playlist-read-private playlist-read-collaborative"
    client_info = {'client_id': client_id, 'client_secret': client_secret, 'redirect_uri': redirect_uri, 'scope': scope}
    return client_info

# Set up a Spotify connection with retries and timeout
def connect_to_spotify(client_info):
    client_id = client_info['client_id']
    client_secret = client_info['client_secret']
    redirect_uri = client_info['redirect_uri']
    scope = client_info['scope']

    # Create a session and configure retries for the session
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)

    # Mount the retry-enabled adapter to the session
    session.mount("https://", adapter)

    # Use Spotipy's internal session management but inject our retry-enabled session
    auth_manager = SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope=scope)
    
    # Initialize Spotipy with our session configuration and add timeout handling
    sp = spotipy.Spotify(auth_manager=auth_manager, requests_session=session, requests_timeout=10)
    user_info = sp.current_user()
    user_id = user_info['id']
    client_info['user_id'] = user_id
    
    return sp, client_info

def get_user_input(spotify_df):    
    # Ask the user how they want to select the songs
    # o Eventually need to update the playlist name and description info formatting from the input file
    selection_method = input("How would you like to select the songs? (file/input/random): ").strip().lower()
    user_input_file = {}

    if selection_method == 'file':
        file_path = input("Enter the file path: ").strip()
        user_input_file['song_list'] = get_songs_from_file(file_path)
        playlist_name = input("Enter the name of the playlist you'd like to create: ").strip()
        playlist_description = input("Enter a description for the playlist: ").strip()
        if user_input_file['song_list']:
            song_list = user_input_file['song_list']
        else:
            song_list['song_titles'] = get_songs_from_input()
    
    # need to improve this method
    elif selection_method == 'input':
        song_titles = get_songs_from_input()
        song_list['song_titles'] = song_titles
    
    # need to improve this method
    elif selection_method == 'random':
        num_songs = int(input("How many random songs would you like to select? ").strip())
        song_list['song_titles'] = get_random_songs(spotify_df, num_songs)

    else:
        print("Invalid selection method.")
        return
    
    # store all the user input in a dictionary
    user_input = {}
    user_input['playlist_name'] = playlist_name
    user_input['playlist_description'] = playlist_description  
    user_input['song_list'] = song_list

    return user_input
    
def create_playlist(sp, client_info, playlist_details, song_ids):
    # Create the new playlist
    playlist_name = playlist_details['playlist_name']
    playlist_description = playlist_details['playlist_description']
    user_id = client_info['user_id']
    playlist = sp.user_playlist_create(user_id, playlist_name, public=True, description=playlist_description)
    
    # Get the playlist ID
    playlist_id = playlist['id']
    
    # Add songs to the playlist
    sp.playlist_add_items(playlist_id, song_ids)
    
    print(f"Created a new playlist with ID: {playlist_id} and added {len(song_ids)} songs.")

# need to improve this formatting-wise
def get_songs_from_input():
    songs = input("Enter song titles (comma-separated): ").split(',')
    return [song.strip() for song in songs]

# need to improve this formatting-wise
def get_random_songs(spotify_df, num_songs=10):
    return random.sample(spotify_df['track_name'].tolist(), num_songs)

def main():

    # get client info like client_id, client_secret, redirect_uri, and scope
    client_info = get_client_info()

    # Initialize Spotipy with your API credentials
    sp, client_info = connect_to_spotify(client_info)

    # Load the spotify profile data into a DataFrame
    spotify_df = load_json_to_dataframe('spotify_profile_data_by_song.json')
    
    # Get user input
    user_input = get_user_input(spotify_df)

    # Get the song IDs from the spotify profile data
    song_titles = user_input['song_list']['song_titles']
    song_artists = user_input['song_list']['song_artists']  

    # Need to change this to check if it's already in the dataframe
    song_ids = get_song_ids(song_titles, song_artists, spotify_df, sp)
    
    # Create the playlist and add the songs
    playlist_details = {key: user_input[key] for key in ['playlist_name', 'playlist_description']}
    create_playlist(sp, client_info, playlist_details, song_ids)

if __name__ == "__main__":
    main()


# NOTES
# - Need to make this more versatile to be more of a playlist editor/searcher or smt
# - Need to add error handling for invalid song titles or artists
# - Need to add a method to handle the case where a song is not found in the Spotify profile data
# - Need to add a method to handle the case where multiple songs with the same title are found
# - Need to add a method to handle the case where multiple artists with the same name are found
# - Need to add a method to handle the case where the user wants to select songs randomly or by input
# - Need to update this to accept client credentials a different way (if it can be automatically accessed some way..?)
# - Need to add a method to find songs that aren't in the database in which case just search spotify for them
# - Need to add a method to edit an existing playlist
# - Need to add a method to delete an existing playlist
# - Need to add a method to search for a playlist
# - Need to add a method to list all playlists
# - Need to add a method to list all songs in a playlist
# - Need to add a method to list all playlists that contain a specific song
# - Need to add a method to list all playlists that contain songs by a specific artist
# - Need to add option to upload a picture for the playlist
# - Need to add option to set mode for playlist

# CREDENTIALS:

# def main():
#     # Initialize Spotipy with your API credentials
#     sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id='bed53f6a46fe4828a9e2a7c6cf2ab1a6',
#                                                    client_secret='524c889675614af9808d8c34e1ae88d5',
#                                                    redirect_uri='http://localhost',
#                                                    scope='playlist-modify-public'))
