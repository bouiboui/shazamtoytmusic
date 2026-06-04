#!/usr/bin/env python3
"""
Script to convert a Shazam export CSV into a YouTube Music Playlist.

Requirements:
- ytmusicapi
- pandas

Setup:
1. Install dependencies: pip install -r requirements.txt
2. Authenticate with YouTube Music: python -m ytmusicapi oauth
3. Run the script: python shazam_to_youtube_music.py <shazam_csv_file> <playlist_name>
"""

import argparse
import csv
import sys
from typing import List, Dict, Optional
import pandas as pd
from ytmusicapi import YTMusic


def read_shazam_csv(csv_file: str) -> List[Dict[str, str]]:
    """
    Read Shazam export CSV and extract song information.
    
    Expected columns (case-insensitive):
    - Title / Song
    - Artist
    - Album (optional)
    """
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
        skiprows = 1 if first_line == 'Shazam Library' else 0
        df = pd.read_csv(csv_file, skiprows=skiprows)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        sys.exit(1)
    
    # Normalize column names to lowercase
    df.columns = df.columns.str.lower()
    
    # Map possible column names to standard names
    column_map = {}
    for col in df.columns:
        if col in ['title', 'song']:
            column_map[col] = 'title'
        elif col == 'artist':
            column_map[col] = 'artist'
        elif col == 'album':
            column_map[col] = 'album'
    
    if 'title' not in column_map.values() or 'artist' not in column_map.values():
        print("Error: CSV must contain 'Title' and 'Artist' columns")
        print(f"Available columns: {list(df.columns)}")
        sys.exit(1)
    
    # Rename columns
    df = df.rename(columns=column_map)
    
    # Extract relevant columns
    songs = []
    for _, row in df.iterrows():
        song = {
            'title': str(row.get('title', '')).strip(),
            'artist': str(row.get('artist', '')).strip(),
            'album': str(row.get('album', '')).strip() if 'album' in df.columns else ''
        }
        if song['title'] and song['artist']:
            songs.append(song)
    
    return songs


def search_song_on_ytmusic(ytmusic: YTMusic, title: str, artist: str, album: str = '') -> Optional[str]:
    """
    Search for a song on YouTube Music and return the video ID.
    """
    query = f"{artist} {title}"
    if album:
        query += f" {album}"
    
    try:
        results = ytmusic.search(query, filter="songs", limit=5)
        
        if not results:
            print(f"  No results found for: {artist} - {title}")
            return None
        
        # Try to find exact match
        for result in results:
            if 'artists' in result:
                result_artists = [a['name'] for a in result['artists']]
                if artist.lower() in ' '.join(result_artists).lower():
                    return result['videoId']
        
        # If no exact match, return first result
        return results[0]['videoId']
    except Exception as e:
        print(f"  Error searching for {artist} - {title}: {e}")
        return None


def create_youtube_music_playlist(ytmusic: YTMusic, playlist_name: str, song_ids: List[str], description: str = "") -> str:
    """
    Create a YouTube Music playlist with the given song IDs.
    """
    try:
        playlist_id = ytmusic.create_playlist(
            title=playlist_name,
            description=description,
            video_ids=song_ids
        )
        return playlist_id
    except Exception as e:
        print(f"Error creating playlist: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Convert Shazam export CSV to YouTube Music Playlist"
    )
    parser.add_argument(
        "csv_file",
        help="Path to Shazam export CSV file"
    )
    parser.add_argument(
        "playlist_name",
        help="Name for the YouTube Music playlist"
    )
    parser.add_argument(
        "--description",
        default="Created from Shazam export",
        help="Description for the playlist (default: 'Created from Shazam export')"
    )
    parser.add_argument(
        "--oauth-file",
        default="oauth.json",
        help="Path to YouTube Music OAuth token file (default: oauth.json)"
    )
    
    args = parser.parse_args()
    
    # Read Shazam CSV
    print(f"Reading Shazam export from: {args.csv_file}")
    songs = read_shazam_csv(args.csv_file)
    print(f"Found {len(songs)} songs in CSV")
    
    # Initialize YouTube Music
    try:
        ytmusic = YTMusic(args.oauth_file)
    except Exception as e:
        print(f"Error initializing YouTube Music: {e}")
        print(f"Make sure you have authenticated with: python -m ytmusicapi oauth")
        sys.exit(1)
    
    # Search for songs on YouTube Music
    print("\nSearching for songs on YouTube Music...")
    song_ids = []
    skipped = 0
    
    for i, song in enumerate(songs, 1):
        print(f"[{i}/{len(songs)}] Searching: {song['artist']} - {song['title']}")
        video_id = search_song_on_ytmusic(
            ytmusic,
            song['title'],
            song['artist'],
            song['album']
        )
        
        if video_id:
            song_ids.append(video_id)
            print(f"  + Found: {video_id}")
        else:
            skipped += 1
    
    print(f"\nFound {len(song_ids)} songs on YouTube Music (skipped: {skipped})")
    
    if not song_ids:
        print("No songs found. Cannot create empty playlist.")
        sys.exit(1)
    
    # Create playlist
    print(f"\nCreating playlist: {args.playlist_name}")
    playlist_id = create_youtube_music_playlist(
        ytmusic,
        args.playlist_name,
        song_ids,
        args.description
    )
    
    print(f"\n+ Playlist created successfully!")
    print(f"Playlist ID: {playlist_id}")
    print(f"You can access it at: https://music.youtube.com/playlist?list={playlist_id}")


if __name__ == "__main__":
    main()
