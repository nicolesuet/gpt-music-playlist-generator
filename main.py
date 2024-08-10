import logging
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import sys
import os
from dotenv import load_dotenv
from openai import OpenAI
import time
import json

load_dotenv()

def login():
    try:
        
        logging.info("Logging in to Spotify.")
        
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
            redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
            scope=os.getenv("SPOTIFY_SCOPE")
        ))
        
        logging.info("Login to Spotify successful!")
        return sp
    
    except Exception as e:
        logging.error("Login failed: %s", str(e))
        raise e
        
        
def authenticate_openapi():
    try:
        logging.info("Authenticating to OpenAI...")
        
        openai_client = OpenAI(api_key=os.getenv("OPENAPI_API_KEY"))
        
        logging.info("OpenAI authentication successful!")
        
        return openai_client
    
    except Exception as e:
        logging.error("OpenAI authentication failed: %s", str(e))
        raise e
    
def get_user_tracks(sp):
    try:
        
        logging.info("Getting user tracks...")
        
        user_tracks = []
        tracks = sp.current_user_saved_tracks(limit=50)
        
        if not tracks:
            logging.info("No tracks found!")
            return user_tracks
            
        while(tracks):
            user_tracks.extend(tracks['items'])
            if tracks['next']:
                tracks = sp.next(tracks)
            else:
                break
            
        logging.info("User tracks retrieved!")
        
        return user_tracks
        
    except Exception as e:
        logging.error("Failed to get user tracks: %s", str(e))
        raise e

def prompt_chat_gtp(openai_client: OpenAI, tracks_info, user_prompt):
    
    try:
        
        logging.info("Prompting chat GPT...")
        
        user_content = f"""
            Here are some songs I love:
            {tracks_info}

            Create a playlist based on these songs with the theme: {user_prompt}.

            Return only a json object containing the songs in the playlist and quick description. The object should be in the following format:

            {{
            'playlist': [
                {{
                    'title': 'song1',
                    'artist': 'artist1'
                }},
                {{
                    'title': 'song1',
                    'artist': 'artist1'
                }},
                {{
                    'title': 'song1',
                    'artist': 'artist1'
                }}
            ],
            'description': 'Playlist description'
            }}
        """

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
            {
                "role": "system", 
                "content": "You are an assistant who can generate music playlists."
            },
            {
                "role": "user",
                "content": user_content
            }
            ]
        )
        
        logging.info(f"Response received from gtp model:\n{response.choices[0].message.content}")
        
        return response.choices[0].message.content

    except Exception as e:
        logging.error("Failed to generate playlist: %s", str(e))
        raise e 
 
 
def create_playlist(sp, user_id, name, description):
    try:
        logging.info("Creating playlist...")
        
        # Create the playlist
        playlist = sp.user_playlist_create(user=user_id, name=name, description=description)
        
        # Get the playlist ID
        playlist_id = playlist.get("id")
        
        logging.info("Playlist created successfully!")
        
        return playlist_id

    except Exception as e:
        logging.error("Failed to create playlist: %s", str(e))
        raise e


def format_query(song):
    try:
        title = song.get('title','')
        artist = song.get('artist','')
        artist = song = artist.replace(' ft. ', ', ').replace(' feat ', ', ').replace(' ft ', ', ').replace(' featuring ', ',')        
        return f"track:'{title}' artist:'{artist}' "
    except Exception as e:
        logging.error("Failed to format song query: %s", str(e))
        raise e
    
def search_tracks(sp, song):
    try:
        
        query = format_query(song)
        results = sp.search(q=query, limit=1, type='track')
        return [track['uri'] for track in results['tracks']['items']]
    
    except Exception as e:
        logging.error("Failed to search tracks: %s", str(e))
        raise e
       
def get_playlist_tracks(sp, tracks):
    
    logging.info("Searching playlist tracks on Spotify...")
    
    tracks_to_add = []
    
    for song in tracks:
        try:
            track = search_tracks(sp, song)
            
            if(not track):
                logging.warning(f"Track not found: {song}")

            tracks_to_add.extend(track)
                            
        except Exception as e:
            logging.exception("Failed to search track: %s", str(e), exc_info=False)
            
    logging.info("Playlist tracks found on Spotify!")
    
    return tracks_to_add

def add_songs_to_playlist(sp, tracks, playlist_id):
    try:
        logging.info("Adding songs to the playlist...")
        
        playlist_tracks = get_playlist_tracks(sp, tracks)
        sp.playlist_add_items(playlist_id, playlist_tracks)
        
        logging.info("Songs added to the playlist successfully!")
        
    except Exception as e:
        logging.error("Failed to add songs to the playlist: %s", str(e))
        raise e

def extract_json_content(input_string):
    try:
        
        logging.info("Extracting JSON content...")

        # Find the first and last occurrence of '{' and '}' respectively
        start_index = input_string.find('{')
        end_index = input_string.rfind('}')
        
        # Ensure both '{' and '}' are found
        if start_index == -1 or end_index == -1:
            raise ValueError("The input string does not contain a valid JSON object.")
        
        # Extract the JSON content
        json_content = input_string[start_index:end_index + 1]
        
        logging.info("JSON content extracted successfully!")
        
        return json_content
    except Exception as e:
        logging.error("Failed to extract JSON content: %s", str(e))
        raise e


def load_playlist_from_ai(response: str):
    try:
        logging.info("Loading playlist from AI response...")
        
        json_content = extract_json_content(response)
        playlist_json = json.loads(json_content)       
        
        if(not is_valid_playlist_json(playlist_json)):
            logging.error("Invalid playlist json: %s", playlist_json)
            raise ValueError("Response generated by AI in incorrect format.")
         
        return playlist_json
    
    except Exception as e:
        logging.error("Failed to load playlist from AI response: %s", str(e))
        raise e


def is_valid_playlist_json(data):
    try:

        # Check if the root contains 'playlist' and 'description'
        if 'playlist' not in data or 'description' not in data:
            return False
        
        # Check if 'playlist' is a list and 'description' is a string
        if not isinstance(data['playlist'], list) or not isinstance(data['description'], str):
            return False
        
        # Check each item in 'playlist' for the correct structure
        for song in data['playlist']:
            if not isinstance(song, dict):
                return False
            if 'title' not in song or 'artist' not in song:
                return False
            if not isinstance(song['title'], str) or not isinstance(song['artist'], str):
                return False
        
        return True
    except ValueError:
        return False
     
def main():
    try:

        # Login to Spotify
        sp = login()
        user= sp.me()
        
        # Get all user tracks
        user_tracks = get_user_tracks(sp)
        
        # Create a string of user tracks to pass to Chat-GPT
        user_track_infos = "\n".join([f"{track['track']['name']} by {track['track']['artists'][0]['name']}" for track in user_tracks])

        # Authenticate OpenAI
        openai_client = authenticate_openapi()
        
        # Inform the theme of the playlist
        user_prompt = input("Enter a theme or inspiration for the playlist: :) ")

        # Getting chat-gtp response
        response = prompt_chat_gtp(openai_client, user_track_infos, user_prompt)

        # Load playlist from AI response
        playlist_info = load_playlist_from_ai(response)
        
        # Creating playlist on Spotify
        playlist_id = create_playlist(
            sp, 
            user_id = user.get("id"), 
            name = user_prompt, 
            description = playlist_info.get("description")
        )
        
        # Adding songs to the Spotify playlist
        add_songs_to_playlist(
            sp, 
            playlist_info.get('playlist'), 
            playlist_id
        )
        
    except Exception as e:
        logging.error("Error: %s", str(e))

if __name__ == "__main__":
    
    start_time = time.time()
    
    logging.basicConfig(
        level=logging.INFO, 
        format='%(levelname)s - %(message)s - %(asctime)s',
        filename='logs.log',
        filemode='a'
    )

    try:
        logging.info("Starting the program...")
        main()
    except Exception as e:
        logging.error("Error: %s", str(e))
    finally:
        end_time = time.time()
        elapsed_time = end_time - start_time
        logging.info("Execution time: %.2f seconds", elapsed_time)
        logging.info("Program completed.")
