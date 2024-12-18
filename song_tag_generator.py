# this script uses the OpenAI API to generate tags for a dataset of songs
# need to remove this api_key and replace with more secure method

import openai
from openai import OpenAI
client = OpenAI(api_key='sk-tq3mh7fRzG5xmbMmoSHjtpuldWtfNGnrI6ZCRoMQnqT3BlbkFJH1R5nBVdLkJcjmyqb1i1MKgTCg6xtnpCjsblCOKBIA')
import pandas as pd
import time
import os
import json
import re
import threading

# load the dataset (full spotify profile data set is default)
def load_dataset(file_path):
    # Check if the file is empty
    if os.path.getsize(file_path) == 0:
        print(f"The file {file_path} is empty.")
        return pd.DataFrame()  # Return an empty DataFrame if the file is empty
    try:
        # Read the JSON file
        with open(file_path, 'r', encoding='utf-8') as file:
        # Parse each line as a separate JSON object
            data = json.load(file)

        # Check if the data is a list (array) or a single object
        if isinstance(data, list):
            return pd.DataFrame(data)
        else:
            return pd.DataFrame([data])
    except ValueError as e:
        print(f"Error reading JSON from {file_path}: {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"An unexpected error occurred while reading JSON from {file_path}: {e}")
        return pd.DataFrame()

def ensure_file_exists(file_path):
    if not os.path.exists(file_path):
        with open(file_path, 'w') as file:
            pass  # Create an empty file

def get_file_paths():
    file_paths = {}
    file_paths['spotify_data'] = r"C:\Users\mltsw\Code\spotify_profile_data_clean.json"
    file_paths['song_data.json'] = r"C:\Users\mltsw\Code\song_data_with_tags.json"
    file_paths['song_data.csv'] = r"C:\Users\mltsw\Code\song_data_with_tags.csv"
    return file_paths

def load_and_ensure_files(file_paths):
    ensure_file_exists(file_paths['spotify_data'])
    ensure_file_exists(file_paths['song_data.json'])
    ensure_file_exists(file_paths['song_data.csv'])

    spotify_data = load_dataset(file_paths['spotify_data'])
    song_data = load_dataset(file_paths['song_data.json'])
    
    return spotify_data, song_data

def ensure_directory_exists(directory_path):
    if not os.path.exists(directory_path):
        print(f"Directory not found: {directory_path}")
        return False
    return True

def get_valid_file_path():
    attempts = 3
    for attempt in range(attempts):
        file_path = input("\nEnter the path to the file containing the list of songs: ").strip().strip('"').strip("'")
        if ensure_directory_exists(file_path):
            return file_path
        else:
            print(f"Attempt {attempt + 1} of {attempts}: Please check the directory path and try again.")
    print("Failed to provide a valid directory path after 3 attempts. Exiting.")
    exit()

# get the categories to generate tags for
def get_categories():
    categories = [
    'Genre','Mood','Energy Level','Style','Instruments Used','Feelings Evoked',
    'Vocals Styles','Lyrical Themes','Production Style','','Target Audience',
    'Cultural Impact','Other Key Characteristics']
    return categories

# select the openai gpt model to use (4o-mini is default)
def get_user_input():
    user_choice = {}

    # get user input to generate new tags or print existing tags
    print("\nWhat would you like to do?: (1) generate new tags, (2) print existing tags")
    user_choice['gen_or_print'] = input("Enter the number corresponding to your choice: ")
    user_choice['map_gen_or_print'] = {
        "1": "generate_new_tags",
        "2": "print_existing_tags"
        }
    
    if user_choice['gen_or_print'] == '1':
        print("Okay. Generating new tags.")
    elif user_choice['gen_or_print'] == '2':
        print("Okay. Printing existing tags.")
        user_choice['gen_or_print_select'] = user_choice['map_gen_or_print'].get(user_choice['gen_or_print'])
    else:
        print("Invalid input. Generating new tags by default.")

    user_choice['gen_or_print_select'] = user_choice['map_gen_or_print'].get(user_choice['gen_or_print'], "generate_new_tags")

    # get user input to summarize or compare tags
    print("\nWould you like to summarize the tags for each song (s) or compare the tags category by category (c) for the selected songs?")
    user_choice['summarize_or_compare'] = input("Enter the letter corresponding to your choice: ")
    user_choice['map_sum_or_comp'] = {
        "s": "summarize_tags",
        "c": "compare_tags"
    }

    user_choice['sum_or_comp_select'] = user_choice['map_sum_or_comp'].get(user_choice['summarize_or_compare'], "summarize_tags")

    if user_choice['sum_or_comp_select'] == 'summarize_tags':
        print("Okay. Summarizing the tags for each song.")
    elif user_choice['sum_or_comp_select'] == 'compare_tags':
        print("Okay. Comparing the tags for each song category by category.")
    else:
        print("Invalid input. Summarizing the tags by default.")
    
    # if the user just wants to print the data, they don't need to answer the questions about overwriting vs appending
    if user_choice['gen_or_print_select'] == 'print_existing_tags':
        return user_choice
    
    # get user input to either append or overwrite. ask for confirmation if they select overwrite
    print("\nSelect if you'd like to: (1) append the data or (2) overwrite the data")
    user_choice['append_or_overwrite'] = input("Enter the number corresponding to your choice: ")
    if user_choice['append_or_overwrite'] == '2':
        print("\nAre you sure you'd like to overwrite the data?")
        user_choice['confirm_overwrite'] = input("Enter 'yes' or 'no': ").strip('"').strip("'").lower()
        if user_choice['confirm_overwrite'] == 'no' or user_choice['confirm_overwrite'] == 'n':
            user_choice['append_or_overwrite'] = 1
            print("\nOkay. Data will be appended instead.")
        elif user_choice['confirm_overwrite'] == 'yes' or user_choice['confirm_overwrite'] == 'y':
            print("\nOkay. Data will be overwritten")
        else:
            print("Invalid choice. Exiting.")
            exit()
    elif user_choice['append_or_overwrite'] == '1':
        print("Okay. Data will be appended.")
    else:
        print("Invalid choice. Data will be appended by default.")
    user_choice['map_app_or_over'] = {
        "1": "append_data",
        "2": "overwrite_data"
        }
    user_choice['app_or_over_select'] = user_choice['map_app_or_over'].get(user_choice['append_or_overwrite'], "append_data")
    
    print("\nSelect the OpenAI model to use: (1) gpt-4o (2) gpt-4o-mini (3) gpt-4o-batch (4) gpt-4o-mini-batch")
    user_choice['model_option'] = input("Enter the number corresponding to your choice: ")
    user_choice['model_map'] = {
        "1": "gpt-4o",
        "2": "gpt-4o-mini",
        "3": "gpt-4o-batch",
        "4": "gpt-4o-mini-batch"
    }
    user_choice['model_name'] = user_choice['model_map'].get(user_choice['model_option'], "gpt-4o-mini")  # Default to gpt-4o-mini if input is invalid
    # Check if the model option is not valid
    if user_choice['model_option'] not in ["1", "2", "3", "4"]:
        print("Invalid input. Defaulting to gpt-4o-mini.")

    print(f"Using model: {user_choice['model_name']}")

    return user_choice

# format the artists into strings for readability (used when printing song data)
def format_artists(artists):
    if len(artists) == 1:
        return artists[0]
    elif len(artists) == 2:
        return f"{artists[0]} and {artists[1]}"
    else:
        return f"{', '.join(artists[:-1])}, and {artists[-1]}"
    
# Function to generate tags for a song using the openai api
def generate_tags_for_song(track_name, artists, categories, model_name):

    prompt = (
            f"Create a detailed list of description tags (5 words max each, but 1, 2 and sometimes 3 words are preferable) "
            f"to describe this song's {', '.join(categories)}. "
            f"Do not include the song name '{track_name}' or artist(s) name(s) '{', '.join(artists)}' in the description. "
            f"Generate 10 tags for each category. "
            f"Every tag should be unique and descriptive. Include enough tags to describe the song in detail but avoid redundancy. "
            f"If a song is cross-genre, try to include genre tags of different types to best encapsulate the full spectrum of genres. "
            f"Example: if applicable, hip hop and r&b would be preferable over hip hop and rap. "
            f"The same can be said for other categories, like if a song evokes different moods or uses different styles. "
            f"Use the genre's in the list provided by https://www.musicgenreslist.com/ as a reference. "
            f"Just provide lists, without any introductory or closing sentences. "
            f"Don't force descriptions you aren't confident about. "
            f"Keep formatting consistent across lists. "
            f"Tags should be grouped by the categories listed above and formatted as follows: "
            f"Each category of tags should be on the same line, with a colon following the category name and the tags separated by commas. "
            f"General example formatting: "
            f"'Category: Tag, Tag, Tag, Tag, Tag, Tag, Tag, Tag, Tag, Tag\n' "
            f"Specific example formatting: "
            f"'Genre: Tag, Tag, Tag, Tag, Tag, Tag, Tag, Tag, Tag, Tag\nMood: Tag, Tag, Tag, Tag, Tag, Tag, Tag, Tag, Tag, Tag\n...'")

    messages = [
        {"role": "user", "content": prompt}
    ]
    
    for attempt in range(5):  # Retry logic for multiple attempts
        try:
            response = client.chat.completions.create(
                messages=messages,
                model=model_name
            )
            tags = response.choices[0].message.content.strip().split('\n')
            print(f"Tags generated for {track_name} by {', '.join(artists)}")
            return tags
        
        except openai.APIError as e:
            print(f"OpenAI API returned an API Error: {e}. Attempt {attempt + 1} of 5.")
            time.sleep(2 ** attempt)  # Exponential backoff
        except openai.APIConnectionError as e:
            print(f"Failed to connect to OpenAI API: {e}. Attempt {attempt + 1} of 5.")
            time.sleep(2 ** attempt)  # Exponential backoff
        except openai.RateLimitError as e:
            print(f"OpenAI API request exceeded rate limit: {e}. Attempt {attempt + 1} of 5.")
            time.sleep(2 ** attempt)  # Exponential backoff
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            break  # Break out of loop for unexpected errors
    return []

def write_to_file(new_data, filename, just_print=True, append=True):
    
    # if just_print is true, don't write to file
    if just_print:
        return
    
       # Check if the file exists
    if os.path.exists(f'{filename}.csv'):
        try:
            # Read the existing data
            existing_data = pd.read_csv(f'{filename}.csv')
        except pd.errors.EmptyDataError:
            print(f"\nThe file {filename}.csv is empty.")
            existing_data = pd.DataFrame()  # Create an empty DataFrame
        # Concatenate the new data with the existing data
        if append:
            combined_data = pd.concat([existing_data, new_data], ignore_index=True)
        else:
            combined_data = new_data
    else:
        combined_data = new_data

    # Write the combined data to the CSV file
    combined_data.to_csv(f'{filename}.csv', index=False)


    # Repeat the same process for JSON
    if os.path.exists(f'{filename}.json'):
        try:
            existing_data = pd.read_json(f'{filename}.json', orient='records')
        except ValueError:
            print(f"The file {filename}.json is empty or invalid.")
            existing_data = pd.DataFrame()  # Create an empty DataFrame
        if append:
            combined_data = pd.concat([existing_data, new_data], ignore_index=True)
        else:
            combined_data = new_data
    else:
        combined_data = new_data

    combined_data.to_json(f'{filename}.json', orient='records', indent=4)

def convert_tags_to_dictionary(tags):
    # Convert tags into dictionaries
    tag_dict = {}
    for tag in tags:
        if isinstance(tag, str):
            # Split the tag string into category and tag value
            parts = tag.split(':', 1)
            if len(parts) == 2:
                category = parts[0].strip()
                tag_values = parts[1].strip().split(',')
                tag_values = [tag_value.strip() for tag_value in tag_values]  # Strip any extra whitespace
                if category in tag_dict:
                    tag_dict[category].extend(tag_values)
                else:
                    tag_dict[category] = tag_values
    return tag_dict

def save_data_periodically(data, file_path, interval=10):
    while True:
        time.sleep(interval)
        df = pd.DataFrame(data)  # Convert list to DataFrame
        df.to_json(file_path, orient='records', lines=True)
        print(f"Data saved to {file_path} at {time.strftime('%Y-%m-%d %H:%M:%S')}")

# Sampling function
def process_songs(dataframe, categories, model_name, full_list=False, specific_songs=None):
    sample_size = 1000
    if full_list:
        sample_data = dataframe
    elif specific_songs:
        sample_data = pd.DataFrame(specific_songs)
    else:
        if len(dataframe) < sample_size:
            sample_size = len(dataframe)
        sample_data = dataframe.sample(n=sample_size, replace=False)

    all_song_descriptors = []

    # need to change this to be an argument passed into the process songs function
    file_path = r"C:\Users\mltsw\Code\song_data_with_tags_preprocessing.json"

    # does this need to be done this way? do we need the threading stuff? 
    # can't we just save the data to the file with normal functions?
    # also this is threading every single song, which is probably not necessary
    # shouldn't it be every 10 if the interval is 10?
    
    # Start a thread to save data periodically
    save_thread = threading.Thread(target=save_data_periodically, args=(all_song_descriptors, file_path))
    save_thread.daemon = True
    save_thread.start()

    try:
        for index, row in sample_data.iterrows():
            track_name = row.get('track_name', '')  # Use .get() to handle missing 'track_name'
            track_id = row.get('track_id', '')  # Use .get() to handle missing 'track_id'
            artists = row.get('artists', [])  # Use .get() to handle missing 'artists'
            artist_ids = row.get('artist_ids', [])  # Use .get() to handle missing 'artist_ids'
            tags = generate_tags_for_song(track_name, artists, categories, model_name)
            tags_dict = convert_tags_to_dictionary(tags)

            new_object = {
                'track_name': track_name,
                'track_id': track_id,
                'artists': artists,
                'artist_ids': artist_ids,
                'tags': tags_dict
            }

            all_song_descriptors.append(new_object)
            time.sleep(1)  # General delay between requests
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        pd.DataFrame(all_song_descriptors).to_json(file_path, orient='records', lines=True)
        print(f"Data saved to {file_path} before exiting.")

    final_data = pd.DataFrame(all_song_descriptors)
    return final_data

# flattens the dataframe so process_songs can access the songs more easily
def expand_df(df):
    expanded_list = []
    for idx, row in df.iterrows():
        for track in row['tracks_metadata']:
            expanded_list.append({
                'track_name': track['track_name'],
                'track_id': track['track_id'],
                'artists': [artist['artist_name'] for artist in track['artists']],
                'artist_ids': [artist['artist_id'] for artist in track['artists']]
            })
    expanded_df = pd.DataFrame(expanded_list)
    return expanded_df

# get the specific songs from the user
def get_specific_songs_from_user():
    songs = []
    while True:
        track_name = input("Enter track name (or 'done' to finish): ").strip()
        if track_name.lower() == 'done':
            break
        # track_id = input("Enter track ID: ").strip()
        artists = input("Enter artist names (comma-separated): ").strip().split(',')
        # artist_ids = input("Enter artist IDs (comma-separated): ").strip().split(',')
        songs.append({
            'track_name': track_name,
            # 'track_id': track_id,
            'artists': artists,
            # 'artist_ids': artist_ids
        })
    return songs

# get the songs from a file
def get_songs_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    songs = []
    for song in data:
        track_name = song.get('title', '')
        artists = song.get('artists', [])
        track_id = song.get('song_id', '')
        artist_ids = song.get('artist_ids', [])
        album = song.get('album', '')
        genres = song.get('genres', [])
        year = song.get('year', '')
        notes = song.get('notes', '')
        
        songs.append({
            'track_name': track_name,
            'track_id': track_id,
            'artists': artists,
            'artist_ids': artist_ids,
            'album': album,
            'genres': genres,
            'year': year,
            'notes': notes
        })
    
    return songs

def compare_tags_for_songs(data, categories):

    if data.empty:
        print("None of the specified songs were found in the dataset.")
        return pd.DataFrame()
    
    # Initialize a dictionary to store tags organized by category > song > tag values
    category_dict = {category: {} for category in categories}
    
    # Iterate through the rows and reorganize the tags
    for index, row in data.iterrows():
        track_name = row.get('track_name', '')
        artists = row.get('artists', [])
        formatted_artists = format_artists(artists)
        tags = row.get('tags', [])
        for category in categories:
            if category in tags:
                if track_name not in category_dict[category]:
                    category_dict[category][track_name] = []
                    category_dict[category][track_name] = {'artists': formatted_artists, 'tags': []}
                category_dict[category][track_name]['tags'].extend(tags[category])
    
    # Print the tags organized by category > song > tag values
    print("\nComparing Tags:")
    for category, songs in category_dict.items():
        print(f"\nCategory: {category}")
        for song, details in songs.items():
            artists = details['artists']
            tag_values = details['tags']
            print(f"{song} by {artists}: {', '.join(tag_values) if tag_values else 'No tags found'}")
    
def summarize_tags_for_songs(data, categories):
    data_for_printing = []
    for index, row in data.iterrows():
        track_name = row.get('track_name', '')
        artists = row.get('artists', [])
        tags = row.get('tags', [])
        
        data_for_printing.append({
            'track_name': track_name,
            'artists': artists,
            'tags': tags
        })

    for song in data_for_printing:
        formatted_artists = format_artists(song['artists'])
        print(f"\n{song['track_name']} by {formatted_artists} \n")
        for category, tag_values in song['tags'].items():
            print(f"{category}: {', '.join(tag_values)}")


# Prompt the user for their choice of songs to generate tags for 
def process_music_data(user_choice, spotify_data, categories, song_data):

    # if the user just wants to print existing tags, follow this logic
    # this logic only searches songs by names, eventually i'll want to add flexibility and specificity to search by artists and ids
    if user_choice['gen_or_print_select'] == 'print_existing_tags':
        print("\nWould you like to print out the results for the entire database (d), a random sample of songs (r), specifc songs (s), or a list of songs from a file (l)? ")
        choice = input("Enter the letter corresponding to your choice: ").strip().lower()
        if choice == 'd':
            processed_data = pd.DataFrame(song_data)
        elif choice == 'r':
            sample_size = 3
            if len(song_data) < sample_size:
                sample_size = len(song_data)
            selected_data = song_data.sample(n=sample_size, replace=False)
            processed_data = pd.DataFrame(selected_data)
        elif choice == 's':
            specific_songs = get_specific_songs_from_user()
            specific_song_names = [song['track_name'].lower() for song in specific_songs]
            filtered_data = song_data[song_data['track_name'].str.lower().isin(specific_song_names)]
            processed_data = pd.DataFrame(filtered_data)
        elif choice == 'l':
            file_path = get_valid_file_path()
            specific_songs = get_songs_from_file(file_path)
            specific_song_names = [song['track_name'].lower() for song in specific_songs]
            filtered_data = song_data[song_data['track_name'].str.lower().isin(specific_song_names)]
            processed_data = pd.DataFrame(filtered_data)
        else:
            print("Invalid choice. Exiting.")
            exit()
        return processed_data

    # if the user wants to generate new tags, follow this logic
    model_name = user_choice['model_name'] # user choice wouldn't be just print it would be the model name
    print("\nWould you like to process the full dataset (f), a random sample (r), specific songs (s), or a list of songs from a file (l)?")
    choice = input("Enter the letter corresponding to your choice: ").strip().lower()
    if choice == 'f':
        full_list = True
        expanded_songs_df = expand_df(spotify_data)
        processed_data = process_songs(expanded_songs_df, categories, model_name, full_list=full_list)
        return processed_data
    elif choice == 'r':
        full_list = False
        expanded_songs_df = expand_df(spotify_data)
        processed_data = process_songs(expanded_songs_df, categories, model_name, full_list=full_list)
        return processed_data
    elif choice == 's':
        specific_songs = get_specific_songs_from_user()
        expanded_songs_df = pd.DataFrame(specific_songs)
        processed_data = process_songs(expanded_songs_df, categories, model_name, full_list=False, specific_songs=specific_songs)
        return processed_data
    elif choice == 'l':
        file_path = get_valid_file_path()
        specific_songs = get_songs_from_file(file_path)
        expanded_songs_df = pd.DataFrame(specific_songs)
        processed_data = process_songs(expanded_songs_df, categories, model_name, full_list=False, specific_songs=specific_songs)
        return processed_data
    else:
        print("Invalid choice. Exiting.")
        exit()

# print the results to the terminal at the end
def print_data(data, user_choice, categories):
    data_for_printing = []
    if user_choice['sum_or_comp_select'] == 'compare_tags':
        compare_tags_for_songs(data, categories)
        return
    elif user_choice['sum_or_comp_select'] == 'summarize_tags':
        summarize_tags_for_songs(data, categories)
    else:
        print("Invalid choice. Exiting.")
        exit()

# check if the user wants to overwrite the data
# if user is just printing the data, they don't need to overwrite
def check_if_tags_generated(user_choice):
    if user_choice['gen_or_print_select'] == 'generate_new_tags':
        just_print = False
        if 'append_or_overwrite' in user_choice and user_choice['app_or_over_select'] == 'overwrite_data':
            append = False
        else:
            append = True
    else:
        just_print = True
        append = False
    return just_print, append

def main():
    # get file paths
    file_paths = get_file_paths()
    
    # Load datasets and ensure files exist, if not, create them
    spotify_data, song_data = load_and_ensure_files(file_paths)

    # Prompt user to specify what they'd like to do (i.e. generate new tags or print existing tags)
    user_choice = get_user_input()

    # categories to generate tags for song
    categories = get_categories()

    # Generate tags for the songs
    processed_data = process_music_data(user_choice, spotify_data, categories, song_data)
    
    # write the processed data to the file if new tags were generated
    just_print, append = check_if_tags_generated(user_choice)
    write_to_file(processed_data, filename='song_data_with_tags', just_print=just_print, append=append)

    # print the tags
    print_data(processed_data, user_choice, categories)

if __name__ == "__main__":
    main()