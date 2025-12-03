# -*- coding: utf-8 -*-
import argparse
import os

from urllib.parse import urlparse, parse_qs
from ncm import config
from ncm.api import CloudApi
from ncm.downloader import get_song_info_by_id
from ncm.downloader import download_song_by_id
from ncm.downloader import download_song_by_song
from ncm.downloader import format_string
from ncm.constants import get_headers

# load the config first
config.load_config()
api = CloudApi(user_cookie=config.USER_COOKIE)


def _parse_disc_number(disc_raw):
    if isinstance(disc_raw, str):
        parts = disc_raw.split('/')
        if parts and parts[0].isdigit():
            return int(parts[0])
    elif isinstance(disc_raw, int):
        return disc_raw
    return None


def _build_disc_map(songs):
    """Return (disc_track_count, disc_total)."""
    disc_track_count = {}
    disc_total = None
    for song in songs:
        disc_raw = song.get('disc') or song.get('cd')
        disc_num = _parse_disc_number(disc_raw)
        disc_total_from_song = None
        if isinstance(disc_raw, str):
            parts = disc_raw.split('/')
            if len(parts) > 1 and parts[1].isdigit():
                disc_total_from_song = int(parts[1])
        if disc_num:
            disc_track_count[disc_num] = disc_track_count.get(disc_num, 0) + 1
        if disc_total is None and disc_total_from_song:
            disc_total = disc_total_from_song
    if disc_total is None and disc_track_count:
        disc_total = max(disc_track_count.keys())
    return disc_track_count, disc_total


def _find_disc_from_album_songs(album_songs, song_id):
    for s in album_songs:
        if s.get('id') == song_id:
            return _parse_disc_number(s.get('disc') or s.get('cd'))
    return None


def download_hot_songs(artist_id):
    songs = api.get_hot_songs(artist_id)
    folder_name = format_string(songs[0]['artists'][0]['name']) + ' - hot50'
    folder_path = os.path.join(config.DOWNLOAD_DIR, folder_name)
    download_count = config.DOWNLOAD_HOT_MAX if (0 < config.DOWNLOAD_HOT_MAX < 50) else config.DOWNLOAD_HOT_MAX_DEFAULT
    for i, song in zip(range(download_count), songs):
        print('{}: {}'.format(i + 1, song['name']))
        download_song_by_song(song, folder_path, False)


def download_album_songs(album_id):
    songs = api.get_album_songs(album_id)
    folder_name = format_string(songs[0]['album']['name']) + ' - album'
    folder_path = os.path.join(config.DOWNLOAD_DIR, folder_name)
    disc_track_count, disc_total = _build_disc_map(songs)

    for i, song in enumerate(songs):
        disc_num = _parse_disc_number(song.get('disc') or song.get('cd'))
        track_total = disc_track_count.get(disc_num) if disc_num else song.get('album', {}).get('size')
        metadata_hint = {
            'disc_number': disc_num,
            'disc_total': disc_total,
            'track_total': track_total
        }

        print('{}: {}'.format(i + 1, song['name']))
        download_song_by_song(song, folder_path, False, metadata_hint=metadata_hint)


def download_program(program_id):
    program = api.get_program(program_id)
    folder_name = format_string(program['dj']['brand']) + ' - program'
    folder_path = os.path.join(config.DOWNLOAD_DIR, folder_name)
    download_song_by_song(program, folder_path, False, True)


def download_playlist_songs(playlist_id):
    songs, playlist_name = api.get_playlist_songs(playlist_id)
    folder_name = format_string(playlist_name) + ' - playlist'
    folder_path = os.path.join(config.DOWNLOAD_DIR, folder_name)
    album_cache = {}
    for i, song in enumerate(songs):
        song_detail = get_song_info_by_id(song['id'])
        album_id = song_detail.get('album', {}).get('id')
        disc_num = _parse_disc_number(song_detail.get('disc') or song_detail.get('cd'))
        track_total = None
        disc_total = None

        if album_id:
            if album_id not in album_cache:
                album_songs = api.get_album_songs(album_id)
                disc_track_count, disc_total_val = _build_disc_map(album_songs)
                album_cache[album_id] = {
                    'songs': album_songs,
                    'disc_track_count': disc_track_count,
                    'disc_total': disc_total_val
                }
            album_info = album_cache[album_id]
            if disc_num is None:
                disc_num = _find_disc_from_album_songs(album_info['songs'], song_detail['id'])
            track_total = album_info['disc_track_count'].get(disc_num) if disc_num else None
            disc_total = album_info['disc_total']

        metadata_hint = {
            'disc_number': disc_num,
            'disc_total': disc_total,
            'track_total': track_total
        }

        print('{}: {}'.format(i + 1, song_detail['name']))
        download_song_by_song(song_detail, folder_path, False, metadata_hint=metadata_hint)


def get_parse_id(song_id):
    # Parse the url
    if song_id.startswith('http'):
        # Not allow fragments, we just need to parse the query string
        return parse_qs(urlparse(song_id, allow_fragments=False).query)['id'][0]
    return song_id


def main():
    parser = argparse.ArgumentParser(description='Welcome to netease cloud music downloader!')
    parser.add_argument('-s', metavar='song_id', dest='song_id',
                        help='Download a song by song_id')
    parser.add_argument('-ss', metavar='song_ids', dest='song_ids', nargs='+',
                        help='Download a song list, song_id split by space')
    parser.add_argument('-hot', metavar='artist_id', dest='artist_id',
                        help='Download an artist hot 50 songs by artist_id')
    parser.add_argument('-a', metavar='album_id', dest='album_id',
                        help='Download an album all songs by album_id')
    parser.add_argument('-dj', metavar='program_id', dest='program_id',
                        help='Download a program by program_id')
    parser.add_argument('-p', metavar='playlist_id', dest='playlist_id',
                        help='Download a playlist all songs by playlist_id')
    parser.add_argument('-ua', metavar='user_agent', dest='user_agent',
                        help='Specify the User-Agent to be used when downloading')
    args = parser.parse_args()
    if args.user_agent:
        # Update global api with custom user agent
        custom_headers = get_headers(config.USER_COOKIE)
        custom_headers.update({'User-Agent': args.user_agent})
        global api
        api = CloudApi(user_cookie=config.USER_COOKIE)
        api.session.headers.update({'User-Agent': args.user_agent})
    if args.song_id:
        download_song_by_id(get_parse_id(args.song_id), config.DOWNLOAD_DIR)
    elif args.song_ids:
        for song_id in args.song_ids:
            download_song_by_id(get_parse_id(song_id), config.DOWNLOAD_DIR)
    elif args.artist_id:
        download_hot_songs(get_parse_id(args.artist_id))
    elif args.album_id:
        download_album_songs(get_parse_id(args.album_id))
    elif args.playlist_id:
        download_playlist_songs(get_parse_id(args.playlist_id))
    elif args.program_id:
        download_program(get_parse_id(args.program_id))


if __name__ == '__main__':
    main()
    
