import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time

# Set up a Spotify connection with retries and timeout
def connect_to_spotify():
    client_id = "bed53f6a46fe4828a9e2a7c6cf2ab1a6"
    client_secret = "524c889675614af9808d8c34e1ae88d5"
    redirect_uri = 'http://localhost'
    scope = "playlist-read-private playlist-read-collaborative"

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
    return sp


# Get all playlist IDs in a profile
def get_playlist_ids(sp):
    offset = 0
    limit = 50  # Max number of playlists to retrieve per request
    all_playlists_ids = []

    while True:
        playlists = sp.current_user_playlists(limit=limit, offset=offset)
        if not playlists['items']:
            break
        all_playlists_ids.extend([playlist['id'] for playlist in playlists['items']])
        offset += limit

    return all_playlists_ids


# Batch request for track data (Spotify allows up to 50 tracks at once)
def get_playlist_tracks_data_batched(sp, track_ids):
    track_data = []
    index = 1  # Initialize track index starting at 1

    # Filter out invalid track IDs before processing
    valid_track_ids = [track_id for track_id in track_ids if isinstance(track_id, str) and track_id]

    for i in range(0, len(valid_track_ids), 50):
        batch_ids = valid_track_ids[i:i + 50]
        try:
            track_batch_data = sp.tracks(batch_ids)
            for track in track_batch_data['tracks']:
                # Ensure the track is not None and has an 'id'
                if track and 'id' in track:
                    track['index'] = index  # Add track index
                    track_data.append(track)  # Append each valid track to track_data
                    index += 1  # Increment track index by 1 for each track
        except requests.exceptions.RequestException as e:
            print(f"Error fetching tracks: {e}. Retrying...")
            time.sleep(2)  # Delay between retries
    return track_data

# Batch request for audio features data (Spotify allows up to 100 tracks at once)
def get_audio_features_batched(sp, track_ids):
    audio_features_data = []

    # Filter out invalid track IDs before processing
    valid_track_ids = [track_id for track_id in track_ids if isinstance(track_id, str) and track_id]

    for i in range(0, len(valid_track_ids), 100):
        batch_ids = valid_track_ids[i:i + 100]
        try:
            audio_features_batch = sp.audio_features(batch_ids)
            
            # Check if the batch contains valid data
            if audio_features_batch:
                # Filter out None values in the audio_features_batch
                valid_audio_features = [features for features in audio_features_batch if features]
                audio_features_data.extend(valid_audio_features)
                
        except requests.exceptions.RequestException as e:
            print(f"Error fetching audio features: {e}. Retrying...")
            time.sleep(2)  # Delay between retries
            
    return audio_features_data

# Get all track IDs from the playlist data
def get_playlist_track_ids(playlist_data):
    if playlist_data.get('tracks') and playlist_data['tracks'].get('items'):
        track_ids = [track['track']['id'] for track in playlist_data['tracks']['items'] if track['track'] is not None]
        return track_ids
    else:
        print(f"Warning: Playlist '{playlist_data['name']}' has no tracks or invalid track data.")
        return []


# Get playlist metadata and track data, with timing and progress updates
def get_playlist_data(sp, playlist_id, batch_start_time, processed_playlists, total_playlists, index, start_index):
    try:
        playlist_data = sp.playlist(playlist_id)
        playlist_data['index'] = index

        track_ids = get_playlist_track_ids(playlist_data)
        tracks_metadata = get_playlist_tracks_data_batched(sp, track_ids)
        audio_features = get_audio_features_batched(sp, track_ids)

        for track, features in zip(tracks_metadata, audio_features):
            if features:
                track['track_features'] = features

        playlist_data['tracks_metadata'] = tracks_metadata

        # Every 10 playlists, calculate timing and forecast remaining time
        if (processed_playlists - start_index) % 10 == 0:  # Adjust processed_playlists relative to start_index
            batch_end_time = time.time()
            batch_duration = int(batch_end_time - batch_start_time)
            elapsed_time = int(batch_end_time - global_start_time)

            # Forecast remaining time based on processed playlists since the start of this run
            playlists_processed_in_run = processed_playlists - start_index  # Playlists processed after resuming
            avg_time_per_playlist = elapsed_time / playlists_processed_in_run
            remaining_playlists = total_playlists - processed_playlists
            forecast_remaining_time = int((avg_time_per_playlist * remaining_playlists))

            print(f"Processed {processed_playlists}/{total_playlists} playlists.")
            print(f"Time for last 10 playlists: {batch_duration} seconds")
            print(f"Total elapsed time: {elapsed_time} seconds")
            print(f"Estimated time remaining: {forecast_remaining_time} seconds")
            print(f"Last playlist processed: {playlist_data['name']}\n")

            # Reset batch start time for the next batch of 10 playlists
            batch_start_time = time.time()

        return playlist_data, batch_start_time

    except requests.exceptions.RequestException as e:
        print(f"Error fetching playlist {playlist_id}: {e}. Retrying...")
        return None, batch_start_time


# Helper function to tidy and clean playlist data
def tidy_data(playlist):
    cleaned_data = {
        'playlist_name': playlist['name'],
        'playlist_description': playlist['description'],
        'playlist_index': playlist['index'],
        'playlist_id': playlist['id'],
        'playlist_url': playlist['external_urls']['spotify'],
        'playlist_owner': playlist['owner']['display_name'],
        'playlist_followers': playlist['followers']['total'],
        'tracks_metadata': []
    }
    
    for track in playlist['tracks_metadata']:
        # Extract the song artists
        artists_info = []
        for artist in track['artists']:
            artists_info.append({
                'artist_name': artist['name'],
                'artist_id': artist['id']
            })

        # Prepare track metadata
        track_metadata = {
            'track_name': track['name'],
            'track_index': track['index'],  # This will now reflect the accurate track index
            'track_id': track['id'],
            'artists': artists_info, # Add the artists and their IDs here
            'album_name': track['album']['name'],
            'track_url': track['external_urls']['spotify'],
            'track_popularity': track['popularity'],
            'track_features': track.get('track_features', {})
        }
        
        cleaned_data['tracks_metadata'].append(track_metadata)

    
    return cleaned_data



# Clean and save playlist data
def clean_profile_playlists_data(profile_playlists_data):
    cleaned_data = []
    for playlist in profile_playlists_data:
        cleaned_data.append(tidy_data(playlist))
    return cleaned_data


# Split function to get profile data (Spotify or local)
def get_profile_data(sp):
    # Ask the user if they want to fetch from Spotify or use local data
    fetch_from_spotify = input("\nDo you want to fetch playlist data from Spotify? (yes/no): ").strip().lower()

    if fetch_from_spotify == 'yes':
        profile_playlists_data = []
        all_playlist_ids = get_playlist_ids(sp)

        # Ask user how many playlists they want
        number_of_playlists = input("\nHow many playlists do you want? Just press enter if you want them all: ").strip().lower()
        number_of_playlists = len(all_playlist_ids) if not number_of_playlists else int(number_of_playlists)

        # Get the playlist IDs you want to process
        desired_playlist_ids = all_playlist_ids[:number_of_playlists]

        total_playlists = len(desired_playlist_ids)

        # Ask user if they want to resume from a specific playlist
        start_from_playlist = input("\nEnter the playlist number to start from (e.g., 850) or press Enter to start from the beginning: ").strip()

        # If a starting point is provided, adjust the desired_playlist_ids list and total_playlists
        if start_from_playlist:
            start_index = int(start_from_playlist) - 1  # Adjust start index to be 0-based
            desired_playlist_ids = desired_playlist_ids[start_index:]
        else:
            start_index = 0  # If no start point, default to beginning

        processed_playlists = start_index

        global_start_time = time.time()  # Track total time
        batch_start_time = time.time()  # Track time for each batch of 10 playlists

        # Get data for each playlist
        for index, playlist_id in enumerate(desired_playlist_ids, start=start_index + 1):
            playlist_data, batch_start_time = get_playlist_data(sp, playlist_id, batch_start_time, processed_playlists, total_playlists, index, start_index)

            if playlist_data:
                profile_playlists_data.append(playlist_data)
                processed_playlists += 1

        # Save raw profile data to a file
        with open('raw_profile_playlists_data.json', 'w') as f:
            json.dump(profile_playlists_data, f)

        print(f"\nData fetched and saved for {processed_playlists} playlists.")
        
    else:
        # If the user chooses not to fetch from Spotify, load from file
        print("\nLoading raw profile data from file...")
        with open('raw_profile_playlists_data.json', 'r') as f:
            profile_playlists_data = json.load(f)

    return profile_playlists_data


# Clean and save playlist data to a file
def clean_and_save_profile_data(profile_playlists_data):
    cleaned_data = clean_profile_playlists_data(profile_playlists_data)

    with open('cleaned_profile_playlists_data.json', 'w') as f:
        json.dump(cleaned_data, f)

    print("\nCleaned data has been saved.")

# Fetch raw playlist data from Spotify
def get_profile_data(sp):
    profile_playlists_data = []
    all_playlist_ids = get_playlist_ids(sp)

    # Ask user how many playlists they want
    number_of_playlists = input("\nHow many playlists do you want? Just press enter if you want them all: ").strip().lower()
    number_of_playlists = len(all_playlist_ids) if not number_of_playlists else int(number_of_playlists)

    # Get the playlist IDs you want to process
    desired_playlist_ids = all_playlist_ids[:number_of_playlists]

    total_playlists = len(desired_playlist_ids)
    
    # Ask user if they want to resume from a specific playlist
    start_from_playlist = input("\nEnter the playlist number to start from (e.g., 850) or press Enter to start from the beginning: ").strip()

    # If a starting point is provided, adjust the desired_playlist_ids list and total_playlists
    if start_from_playlist:
        start_index = int(start_from_playlist) - 1  # Adjust for 0-based index
    else:
        start_index = 0
    
    desired_playlist_ids = desired_playlist_ids[start_index:]
    total_playlists = len(desired_playlist_ids)

    print(f"\nProcessing {total_playlists} playlists...\n")

    global global_start_time
    global_start_time = time.time()  # Start global timer
    batch_start_time = time.time()  # Start timer for the first batch of 10
    processed_playlists = 0  # Count of processed playlists in the current session
    
    for i, playlist_id in enumerate(desired_playlist_ids, start=1):
        processed_playlists = i  # i is the relative index in this session (starting from 1)

        # Call get_playlist_data and handle timing updates within it
        playlist_data, batch_start_time = get_playlist_data(
            sp, playlist_id, batch_start_time, processed_playlists, total_playlists, i, start_index
        )

        if playlist_data:
            profile_playlists_data.append(playlist_data)

    # Save the raw data once all playlists are processed
    save_data(profile_playlists_data, 'raw')  # Save raw data

    return profile_playlists_data


# Clean and save the profile data
def clean_and_save_profile_data(profile_playlists_data):
    save_start_time = time.time()  # Start timer for the cleaning and saving process

    # Save the data once all playlists are processed
    save_data(profile_playlists_data, 'raw')  # Save raw data
    clean_data = clean_profile_playlists_data(profile_playlists_data)
    save_data(clean_data, 'clean')  # Save cleaned data

    save_end_time = time.time()  # End timer
    saving_duration = int(save_end_time - save_start_time)

    print(f"\nCleaned data has been saved. Time spent cleaning and saving: {saving_duration} seconds.")


    # Helper to save data
def save_data(data, data_type):
    file_path = f"C:/Users/mltsw/Code/spotify_profile_data_{data_type}.json"
    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, indent=2, ensure_ascii=False)



# Main execution logic
if __name__ == "__main__":
    use_spotify = input("Do you want to import data from Spotify (yes/no)? ").strip().lower()
    if use_spotify == 'yes':
        sp = connect_to_spotify()
        profile_playlists_data = get_profile_data(sp)
    else:
        # Load raw data from a file instead of requesting from Spotify
        with open('C:/Users/mltsw/Code/spotify_profile_data_raw.json', 'r', encoding='utf-8') as json_file:
            profile_playlists_data = json.load(json_file)

    # Clean and save the data
    clean_and_save_profile_data(profile_playlists_data)


# ------------------------------------------------------------------
# ------------------------------------------------------------------
# # notes
# ------------------------------------------------------------------
# ------------------------------------------------------------------


# ------------------------------------------------------------------
# questions for remy
# -------------------------------------------------------------------

# what's the best way to organize these embedded dictionaries so i can browse through them more easily?
# should they actually be lists or objects with dictionary and list properties? subclasses? idk

# why don't i have to pass sp through any functions? sp is a non-global variable, 
# but the other functions still have no problem accessing its contents

# how about what i'm using as function inputs vs specified inside function like file path/name/etc

# -----------------------------------------------------------------
# remy comments
# -----------------------------------------------------------------

# each function should only do one thing
# decorator functions

# you can add default values to functions because file_path should be an input but if no input then its this path
# config files

# ------------------------------------------------------------------
# # personal comments
# ------------------------------------------------------------------

# line 124: for playlist_id in playlist_ids:
# doesn't seem to work when there's only one playlist id.. need to add logic to fix this and make more robust

# is this the best way to connect to spotify or should i take user inputs.. have the option?

# could get track data but not metadata by just using the playlist request

# current_user_playlists returns all the playlist data but no useful track data other than number of tracks
    # it gives the playlist tracks href which is nice because that is what you use to make get requests to the spotify api

# ------------------------------------------------------------------
# to-do
# ------------------------------------------------------------------

# fix the time forecasting to be accurate
# make it possible to be more selective about which playlist data is downloaded (names, or custom ranges, not that important)
# custom downloads like only my playlists, only my privates (scope definition capabilities)
# but whats more important is sorting these songs by tags and descriptions and making new playlists and preview urls

# gotta save playlist data (name and what else so i can tell wtf is what - change the get_playlist_ids function)
# probably better to save song name too instead of just index (i) bc same issue as above
# save the index inside the dictionary bc it's nice to know for sure

# need to fix the line 124 issue: add logic to fix this and make more robust

# add timer to requests to figure how long it's all taking

# be able to request specific playlist data from spotify instead of all at once.. maybe just use the other code for this? idk

# need to add a function that asks if you wanna get rid of the 'maybe useful' data and the default is to get rid
# also.. just clean this up some

# similarity vector on the spotify provided data that would be really easy to analyze and work with
# 1 or 0 if tag is active or not

# should come back and make the getting user input better with a while and try statement

# could simplify this code by just running the playlist function which already returns the tracks data
# instead of running two get requests but save that for another time

# gotta restructure this big time to get it to reduce the number of sp requests.. 
    # sp.get_user_playlists - for playlist data (save stuff immediate) .. 
        # or maybe get just the playlist id's from this and then use sp.playlist on each id to get the playlist data and song data bc this has everything
        # including playlist followers, track data (excluding audio features)
    # use the tracks href or the playlist id and get_playlist_tracks to access track features


# current number of sp requests being made is about 10000 ... we can get it down to about 5000 by just doing audio_features request and to about 4000 by taking track id's from playlist request..
# looks like we want to still get all the playlist ids and get the data for each playlist individually.. extract the track ids and main data.. then extract audio features 1 by 1
# get_playlist_ids: 15 - batches of 50 for however many playlists (50 x 15 = 750)
# get_playlist_data: 750 - however many playlists
# get_track_ids: 750 - playlist_tracks obtains all the track ids
# get_track_data: 750x50 + 750x50 - however many tracks times 2 bc we're doing an audio_features request and a track request





