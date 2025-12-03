# -*- coding: utf-8 -*-

import os
from datetime import datetime

from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3, HeaderNotFoundError
from mutagen.id3 import (
    ID3,
    APIC,
    COMM,
    TCOM,
    TCON,
    TDRC,
    TPE1,
    TPE2,
    TIT2,
    TALB,
    TPOS,
    TRCK,
    TXXX,
    USLT,
    error,
)
from PIL import Image


def resize_img(file_path, max_size=(640, 640), quality=90):
    try:
        img = Image.open(file_path)
    except IOError:
        print('Can\'t open image:', file_path)
        return

    if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        img = img.convert('RGB')
        img.save(file_path, quality=quality)


def add_metadata_to_song(file_path, cover_path, song, is_program=False, lyrics=None, metadata_hint=None):
    """Write metadata (ID3 or Vorbis) and embed cover art."""

    metadata = _build_metadata(song, is_program, lyrics, metadata_hint)
    print('Writing metadata -> title: {title}, artists: {artists}, album: {album}, track: {track}/{track_total}, disc: {disc}/{disc_total}, has_lyrics: {has_lyrics}, has_translation: {has_translation}'.format(
        title=metadata.get('title') or '',
        artists=' / '.join(metadata.get('artists') or []),
        album=metadata.get('album') or '',
        track=metadata.get('track_number') or '-',
        track_total=metadata.get('track_total') or '-',
        disc=metadata.get('disc_number') or '-',
        disc_total=metadata.get('disc_total') or '-',
        has_lyrics=bool(metadata.get('lyrics')),
        has_translation=bool(metadata.get('translated_lyrics'))
    ))
    extension = os.path.splitext(file_path)[1].lower()

    if extension == '.flac':
        _add_flac_metadata(file_path, cover_path, metadata)
    else:
        _add_id3_metadata(file_path, cover_path, metadata)


def _build_metadata(song, is_program, lyrics, metadata_hint=None):
    metadata_hint = metadata_hint or {}
    # artists and album artist
    artists = []
    album_artist = None
    if is_program:
        artists = [song.get('dj', {}).get('nickname', '')]
        album_artist = song.get('dj', {}).get('nickname')
    else:
        artists = [a.get('name') for a in song.get('artists', []) if a.get('name')]
        album_info = song.get('album', {})
        album_artist_candidates = []
        if isinstance(album_info.get('artists'), list):
            album_artist_candidates = [a.get('name') for a in album_info.get('artists') if a.get('name')]
        elif isinstance(album_info.get('artist'), dict):
            if album_info['artist'].get('name'):
                album_artist_candidates = [album_info['artist'].get('name')]
        album_artist = ' / '.join(album_artist_candidates) if album_artist_candidates else None
    artists = [a for a in artists if a]
    if not album_artist and artists:
        album_artist = ' / '.join(artists)

    # title / album
    title = song.get('name', '')
    if is_program:
        album_name = song.get('dj', {}).get('brand', '')
    else:
        album_name = song.get('album', {}).get('name', '')

    # track / disc info
    track_number = metadata_hint.get('track_number') if metadata_hint.get('track_number') is not None else (song.get('no') if not is_program else None)
    track_total = metadata_hint.get('track_total') if metadata_hint.get('track_total') is not None else (song.get('album', {}).get('size') if not is_program else None)
    disc_number = metadata_hint.get('disc_number') if metadata_hint.get('disc_number') is not None else None
    disc_total = metadata_hint.get('disc_total') if metadata_hint.get('disc_total') is not None else None

    if not is_program:
        if disc_number is None or disc_total is None:
            disc_raw = song.get('disc') or song.get('cd')
            disc_number_from_song = None
            disc_total_from_song = None
            if isinstance(disc_raw, str):
                parts = disc_raw.split('/')
                if parts and parts[0].isdigit():
                    disc_number_from_song = int(parts[0])
                if len(parts) > 1 and parts[1].isdigit():
                    disc_total_from_song = int(parts[1])
            elif isinstance(disc_raw, int):
                disc_number_from_song = disc_raw
            if disc_number is None:
                disc_number = disc_number_from_song
            if disc_total is None:
                disc_total = disc_total_from_song
        if disc_total is None:
            disc_total = song.get('album', {}).get('cds')

    # composer / genre / publish info
    composer = song.get('composer')
    if not composer and artists:
        composer = artists[0]
    genres = []
    album_tags = song.get('album', {}).get('tags')
    if isinstance(album_tags, list):
        genres = [g for g in album_tags if isinstance(g, str) and g]
    publish_time = song.get('album', {}).get('publishTime')
    date_str = None
    year = None
    if publish_time:
        try:
            publish_dt = datetime.fromtimestamp(publish_time / 1000)
            date_str = publish_dt.strftime('%Y-%m-%d')
            year = str(publish_dt.year)
        except Exception:
            pass

    # alias / comments
    aliases = song.get('alias') or song.get('alia') or []
    if isinstance(aliases, str):
        aliases = [aliases]
    aliases = [a for a in aliases if isinstance(a, str) and a]
    comment = None
    if not is_program:
        comment = song.get('album', {}).get('company')

    lyric_text = (lyrics or {}).get('lyric') if lyrics else None
    translated_lyric = (lyrics or {}).get('tlyric') if lyrics else None

    return {
        'title': title,
        'album': album_name,
        'artists': artists,
        'album_artist': album_artist,
        'track_number': track_number,
        'track_total': track_total,
        'disc_number': disc_number,
        'disc_total': disc_total,
        'composer': composer,
        'genres': genres,
        'date': date_str,
        'year': year,
        'aliases': aliases,
        'comment': comment,
        'lyrics': lyric_text,
        'translated_lyrics': translated_lyric
    }


def _guess_mime(cover_path):
    lower_path = cover_path.lower()
    if lower_path.endswith('.png'):
        return 'image/png'
    return 'image/jpeg'


def _add_id3_metadata(file_path, cover_path, meta):
    try:
        audio = MP3(file_path, ID3=ID3)
    except HeaderNotFoundError:
        print('Can\'t sync to MPEG frame, not an validate MP3 file!')
        return

    if audio.tags is None:
        print('No ID3 tag, trying to add one!')
        try:
            audio.add_tags()
            audio.save()
        except error as e:
            print('Error occur when add tags:', str(e))
            return

    id3 = ID3(file_path)

    # Remove old frames we fully control
    for frame in ['APIC', 'TPE1', 'TPE2', 'TIT2', 'TALB', 'TRCK', 'TPOS', 'TCOM', 'TCON', 'TDRC', 'COMM', 'USLT']:
        if id3.getall(frame):
            id3.delall(frame)
    for key in ['TXXX:ALIAS', 'TXXX:LYRIC_TRANSLATION']:
        if key in id3:
            del id3[key]

    # Cover art
    with open(cover_path, 'rb') as cover_file:
        cover_data = cover_file.read()

    id3.add(
        APIC(
            encoding=3,
            mime=_guess_mime(cover_path),
            type=3,  # front cover
            data=cover_data
        )
    )

    # Core fields
    if meta['artists']:
        id3.add(TPE1(encoding=3, text=meta['artists']))
    if meta['album_artist']:
        id3.add(TPE2(encoding=3, text=meta['album_artist']))
    if meta['title']:
        id3.add(TIT2(encoding=3, text=meta['title']))
    if meta['album']:
        id3.add(TALB(encoding=3, text=meta['album']))

    # Track / disc
    if meta['track_number']:
        track_text = str(meta['track_number'])
        if meta['track_total']:
            track_text = '{}/{}'.format(meta['track_number'], meta['track_total'])
        id3.add(TRCK(encoding=3, text=track_text))
    if meta['disc_number']:
        disc_text = str(meta['disc_number'])
        if meta['disc_total']:
            disc_text = '{}/{}'.format(meta['disc_number'], meta['disc_total'])
        id3.add(TPOS(encoding=3, text=disc_text))

    # Extra descriptive fields
    if meta['composer']:
        id3.add(TCOM(encoding=3, text=meta['composer']))
    if meta['genres']:
        id3.add(TCON(encoding=3, text=' / '.join(meta['genres'])))
    if meta['date'] or meta['year']:
        id3.add(TDRC(encoding=3, text=meta['date'] or meta['year']))
    if meta['comment']:
        id3.add(COMM(encoding=3, lang='eng', desc='', text=meta['comment']))
    if meta['aliases']:
        id3['TXXX:ALIAS'] = TXXX(encoding=3, desc='ALIAS', text=' / '.join(meta['aliases']))

    # Lyrics
    if meta['lyrics']:
        id3['USLT::eng'] = USLT(encoding=3, lang='eng', desc='', text=meta['lyrics'])
    if meta['translated_lyrics']:
        id3['TXXX:LYRIC_TRANSLATION'] = TXXX(encoding=3, desc='LYRIC_TRANSLATION', text=meta['translated_lyrics'])

    id3.save(v2_version=3)


def _add_flac_metadata(file_path, cover_path, meta):
    try:
        audio = FLAC(file_path)
    except Exception:
        print('Not a valid FLAC file:', file_path)
        return

    # Clear pictures to avoid duplicates
    audio.clear_pictures()

    # Core tags
    if meta['artists']:
        audio['artist'] = meta['artists']
    if meta['album_artist']:
        audio['albumartist'] = [meta['album_artist']]
    if meta['title']:
        audio['title'] = [meta['title']]
    if meta['album']:
        audio['album'] = [meta['album']]

    # Track / disc
    if meta['track_number']:
        audio['tracknumber'] = [str(meta['track_number'])]
    if meta['track_total']:
        audio['tracktotal'] = [str(meta['track_total'])]
    if meta['disc_number']:
        audio['discnumber'] = [str(meta['disc_number'])]
    if meta['disc_total']:
        audio['disctotal'] = [str(meta['disc_total'])]

    # Extra fields
    if meta['composer']:
        audio['composer'] = [meta['composer']]
    if meta['genres']:
        audio['genre'] = [' / '.join(meta['genres'])]
    if meta['date']:
        audio['date'] = [meta['date']]
    elif meta['year']:
        audio['date'] = [meta['year']]
    if meta['comment']:
        audio['comment'] = [meta['comment']]
    if meta['aliases']:
        audio['alias'] = meta['aliases']

    # Lyrics
    if meta['lyrics']:
        audio['lyrics'] = [meta['lyrics']]
    if meta['translated_lyrics']:
        audio['lyrics-translation'] = [meta['translated_lyrics']]

    # Cover art
    picture = Picture()
    picture.type = 3
    picture.desc = 'Cover'
    picture.mime = _guess_mime(cover_path)
    with open(cover_path, 'rb') as img_file:
        picture.data = img_file.read()
    audio.add_picture(picture)

    audio.save()
