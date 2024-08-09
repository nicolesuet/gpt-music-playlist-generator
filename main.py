import logging
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import sys
import os
from dotenv import load_dotenv
from openai import OpenAI
import time

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
    return OpenAI(api_key = os.getenv("OPENAPI_API_KEY"))

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
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
            {"role": "system", "content": "You are an assistant who can generate music playlists."},
            {"role": "user", "content": f"Here are some songs I love:\n{tracks_info}\n\nCreate a playlist based on these songs with the theme: {user_prompt}"}
            ]
        )
        
        logging.info(f"Response:\n{response.choices[0].message.content}")
        
        logging.info("Playlist generated successfully!")
        
        return response

    except Exception as e:
        logging.error("Failed to generate playlist: %s", str(e))
        raise e 


def main():
    try:

        # Login to Spotify
        sp = login()
        
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
