import json
import os

DEFAULT_FILE_NAME = "songs_list.json"

def load_songs(file_name):
    if not os.path.exists(file_name):
        return []
    with open(file_name, "r") as file:
        return json.load(file)

def save_songs(new_songs, file_name, mode):
    if mode == 'append':
        existing_songs = load_songs(file_name)
        updated_songs = existing_songs + new_songs
    else:
        updated_songs = new_songs
    with open(file_name, "w") as file:
        json.dump(updated_songs, file, indent=4)
        print("Songs updated successfully!")

def get_metadata_choice():
    while True:
        print('\n')
        change_metadata = input("Would you like to add/edit additional metadata (album, genres, year, notes) for each song? (yes/no): ").strip().lower()
        if change_metadata in ['yes', 'no']:
            return change_metadata
        else:
            print("Invalid choice. Please enter 'yes' or 'no'.")

def format_artists(artists):
    if len(artists) == 1:
        return artists[0]
    elif len(artists) == 2:
        return f"{artists[0]} and {artists[1]}"
    else:
        return f"{', '.join(artists[:-1])}, and {artists[-1]}"

def get_file_name():
    print('\n')
    use_default = input(f"Would you like to use the default file ({DEFAULT_FILE_NAME})? (yes/no): ").strip().lower()
    if use_default == 'yes':
        return DEFAULT_FILE_NAME
    else:
        return input("Enter the file name you would like to use: ").strip()

def get_add_save_mode():
    while True:
        print('\n')
        mode = input("Would you like to overwrite or append the data? (overwrite/append): ").strip().lower()
        if mode in ['overwrite', 'append']:
            if mode == 'overwrite':
                while True:
                    confirm = input("Are you sure you want to overwrite the data? (yes/no): ").strip().lower()
                    if confirm in ['yes', 'no']:
                        if confirm == 'yes':
                            print("Data will be overwritten.")
                            return mode
                        elif confirm == 'no':
                            print("Data will not be appended.")
                            mode = 'append'
                            return mode
                    else:
                        print("Invalid choice. Please enter 'yes' or 'no'.")
        else:
            print("Invalid choice. Please enter 'overwrite' or 'append'.")

def display_songs(songs):
    print("\nSongs:")
    if not songs:
        print("No songs in the list.")
        return
    for i, song in enumerate(songs, start=1):
        formatted_artists = format_artists(song['artists'])
        print(f"{i}. {song['title']} by {formatted_artists}")

def add_song(new_songs, add_metadata):
    print('\n')
    while True:
        song = {}
        title = input("Enter song title (press Enter to stop adding songs): ").strip()
        if not title:
            break
        artists = input("Enter artist(s) (comma-separated if multiple): ").strip()
        artist_list = [artist.strip() for artist in artists.split(",")]

        if add_metadata == 'yes':
            album = input("Enter album (optional): ").strip()
            genres = input("Enter genre(s) (optional, comma-separated if multiple): ").strip()
            genre_list = [genre.strip() for genre in genres.split(",")]
            year = input("Enter year (optional): ").strip()
            notes = input("Enter notes (optional): ").strip()
        else:
            album = ""
            genre_list = []
            year = ""
            notes = ""
        
        song = {
            "title": title,
            "artists": artist_list,
            "album": album,
            "genres": genre_list,
            "year": year,
            "notes": notes
        }
        new_songs.append(song)
        print(f"Added: {title} by {', '.join(artist_list)}")


def edit_song(songs, edit_metadata):
    display_songs(songs)

    while True:
        try:
            choice = int(input("Enter the number of the song to edit: "))
            if choice < 1 or choice > len(songs):
                print("Invalid choice! Please enter a number between 1 and", len(songs))
            else:
                break
        except ValueError:
            print("Invalid input! Please enter a valid number.")

    song = songs[choice - 1]
    print(f"Editing: {song['title']} by {', '.join(song['artists'])}")
    song['title'] = input(f"New title (leave blank to keep '{song['title']}'): ") or song['title']
    artists = input(f"New artist(s) (leave blank to keep '{', '.join(song['artists'])}'): ")
    if artists:
        song['artists'] = [artist.strip() for artist in artists.split(",")]

    if edit_metadata == 'yes':
        song['album'] = input(f"New album (leave blank to keep '{song['album']}'): ") or song['album']
        genres = input(f"New genre(s) (leave blank to keep '{', '.join(song['genres'])}'): ")
        if genres:
            song['genres'] = [genre.strip() for genre in genres.split(",")]
        song['year'] = input(f"New year (leave blank to keep '{song['year']}'): ") or song['year']
        song['notes'] = input(f"New notes (leave blank to keep '{song['notes']}'): ") or song['notes']
    else:
        song['album'] = ""
        song['genres'] = []
        song['year'] = ""  
        song['notes'] = ""

    print("Song updated successfully!")
    return songs

def delete_song(songs):
    display_songs(songs)

    while True:
        try:
            choice = int(input("Enter the number of the song to delete: "))
            if choice < 1 or choice > len(songs):
                print("Invalid choice! Please enter a number between 1 and", len(songs))
            else:
                break
        except ValueError:
            print("Invalid input! Please enter a valid number.")

    deleted = songs.pop(choice - 1)
    print(f"Deleted: {deleted['title']} by {', '.join(deleted['artists'])}")
    
    return songs

def main():
    file_name = get_file_name()
    add_index = 0
    edit_index = 0

    while True:
        print("\nOptions:")
        print("1. View songs")
        print("2. Add songs")
        print("3. Edit a song")
        print("4. Delete a song")
        print("5. Exit")

        choice = input("Choose an option: ").strip()
        existing_songs = load_songs(file_name)

        if choice == "1":
            display_songs(existing_songs)
        elif choice == "2":
            new_songs = []
            add_index += 1
            if add_index <= 1:
                add_metadata = get_metadata_choice()
                add_save_mode = get_add_save_mode()
            else:
                add_save_mode = 'append'
            add_song(new_songs, add_metadata)
            save_songs(new_songs, file_name, add_save_mode)
        elif choice == "3":
            edit_index += 1
            if edit_index <= 1:
                edit_metadata = get_metadata_choice()
            edited_songs = edit_song(existing_songs, edit_metadata)
            save_mode = 'edit'
            save_songs(edited_songs, file_name, save_mode)
        elif choice == "4":
            new_songs = delete_song(existing_songs)
            save_mode = 'delete'
            save_songs(new_songs, file_name, save_mode)
        elif choice == "5":
            print("Goodbye!")
            break
        else:
            print("Invalid option! Please try again.")

if __name__ == "__main__":
    main()

# Additions
# o Add songs from a text file
# o Add songs from a spotify playlist or youtube playlist/video or any other types of sources
# o gotta figure out what's wrong with delete songs
# o need to change the layout so it only asks about appending if I'm adding songs and it only asks once
# o need to add functionality to add multiple songs at a time 
# o need to add functionality to go from spotify playlist to json file for song list