# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
from tmdbhelper.lib.script.method.decorators import get_tmdb_id, map_kwargs


def play_using(play_using, mode='play', **kwargs):
    from tmdbhelper.lib.addon.plugin import get_infolabel
    from tmdbhelper.lib.files.futils import read_file
    from jurialmunkey.parser import parse_paramstring

    def _update_from_listitem(dictionary):
        url = get_infolabel('ListItem.FileNameAndPath') or ''
        if url[-5:] == '.strm':
            url = read_file(url)
        params = {}
        if url.startswith('plugin://plugin.video.themoviedb.helper/?'):
            params = parse_paramstring(url.replace('plugin://plugin.video.themoviedb.helper/?', ''))
        if params.pop('info', None) == 'play':
            dictionary.update(params)
        if dictionary.get('tmdb_type'):
            return dictionary
        dbtype = get_infolabel('ListItem.DBType')
        if dbtype == 'movie':
            dictionary['tmdb_type'] = 'movie'
            dictionary['tmdb_id'] = get_infolabel('ListItem.UniqueId(tmdb)')
            dictionary['imdb_id'] = get_infolabel('ListItem.UniqueId(imdb)')
            dictionary['query'] = get_infolabel('ListItem.Title')
            dictionary['year'] = get_infolabel('ListItem.Year')
            if dictionary['tmdb_id'] or dictionary['imdb_id'] or dictionary['query']:
                return dictionary
        elif dbtype == 'episode':
            dictionary['tmdb_type'] = 'tv'
            dictionary['query'] = get_infolabel('ListItem.TVShowTitle')
            dictionary['ep_year'] = get_infolabel('ListItem.Year')
            dictionary['season'] = get_infolabel('ListItem.Season')
            dictionary['episode'] = get_infolabel('ListItem.Episode')
            if dictionary['query'] and dictionary['season'] and dictionary['episode']:
                return dictionary

    if 'tmdb_type' not in kwargs and not _update_from_listitem(kwargs):
        return
    kwargs['mode'] = mode
    kwargs['player'] = play_using
    from tmdbhelper.lib.player.method.play import play_external
    play_external(**kwargs)


def update_players():
    from xbmcgui import Dialog
    from tmdbhelper.lib.files.downloader import Downloader
    from tmdbhelper.lib.addon.plugin import set_setting
    from tmdbhelper.lib.addon.plugin import get_setting
    from tmdbhelper.lib.addon.plugin import get_localized
    from tmdbhelper.lib.files.futils import get_file_path
    import os
    
    # Check if this is first run by looking for a marker file
    first_run_marker = get_file_path('', '.first_run_complete')
    is_first_run = not os.path.exists(first_run_marker)
    
    if is_first_run:
        # First run - automatically use the default URL
        players_url = 'https://github.com/Spark-NV/repo/raw/refs/heads/main/TMDB_Players/json.openplayers.zip'
    else:
        # Not first run - show dialog for user input
        players_url = get_setting('players_url', 'str')
        players_url = Dialog().input(get_localized(32313), defaultt=players_url)
        if not Dialog().yesno(
                get_localized(32032),
                get_localized(32314).format(players_url)):
            return
    
    set_setting('players_url', players_url, 'str')
    downloader = Downloader(
        extract_to='special://profile/addon_data/plugin.video.themoviedb.helper/players',
        download_url=players_url)
    
    # On first run, automatically clear the directory without prompting and suppress success message
    downloader.get_extracted_zip(auto_clear=is_first_run, show_success=not is_first_run)
    
    # Create marker file after successful first run
    if is_first_run:
        try:
            with open(first_run_marker, 'w') as f:
                f.write('')
        except:
            pass  # Ignore errors if we can't create the marker file
        
        # Set default players on first run
        set_setting('default_player_movies', 'umbrella.select.json play_movie', 'str')
        set_setting('default_player_episodes', 'umbrella.select.json play_episode', 'str')


def set_defaultplayer(**kwargs):
    from tmdbhelper.lib.player.players import Players
    from tmdbhelper.lib.addon.plugin import set_setting
    tmdb_type = kwargs.get('set_defaultplayer')
    setting_name = 'default_player_movies' if tmdb_type == 'movie' else 'default_player_episodes'
    default_player = Players(tmdb_type).select_player(detailed=True, clear_player=True)
    if not default_player:
        return
    if not default_player.get('file') or not default_player.get('mode'):
        return set_setting(setting_name, '', 'str')
    set_setting(setting_name, f'{default_player["file"]} {default_player["mode"]}', 'str')


def set_chosenplayer(tmdb_type, tmdb_id, season=None, episode=None, **kwargs):
    """
    Prompts user to select (or clear) a default player for a single movie or tvshow
    """
    from xbmcgui import Dialog
    from tmdbhelper.lib.player.players import Players
    from tmdbhelper.lib.addon.consts import PLAYERS_CHOSEN_DEFAULTS_FILENAME
    from tmdbhelper.lib.files.futils import get_json_filecache, set_json_filecache
    from tmdbhelper.lib.addon.plugin import get_localized

    if tmdb_type not in ['movie', 'tv'] or not tmdb_id:
        return

    obj = get_json_filecache(PLAYERS_CHOSEN_DEFAULTS_FILENAME) or {}
    lvl = obj
    itm = obj.setdefault(tmdb_type, {}).setdefault(tmdb_id, {})
    nme = kwargs.get('set_chosenplayer') or ''
    itm['name'] = nme

    # If theres a season/episode value then ask user if want to set for whole tvshow or just season/episode
    x = 0
    if season is not None:
        func = Dialog()
        opts = {'nolabel': get_localized(20364), 'yeslabel': get_localized(20373)}

        if episode is not None:
            func = func.yesnocustom
            opts['customlabel'] = get_localized(20359)
        else:
            func = func.yesno

        x = func(f'{tmdb_type} - {tmdb_id}', get_localized(32477), **opts)

        if x == -1:
            return
        if x in [1, 2]:
            lvl = itm.setdefault('season', {})
            itm = lvl.setdefault(f'{season}', {})
        if x == 2:
            lvl = itm.setdefault('episode', {})
            itm = lvl.setdefault(f'{episode}', {})

    chosen_player = Players(tmdb_type).select_player(detailed=True, clear_player=True)
    if not chosen_player:
        return

    if chosen_player.get('file') and chosen_player.get('mode'):
        itm['file'] = chosen_player["file"]
        itm['mode'] = chosen_player["mode"]
        msg = get_localized(32474).format(f"{itm['file']} {itm['mode']}", nme)

    else:
        obj[tmdb_type].pop(f'{tmdb_id}')
        msg = get_localized(32475).format(nme)

    set_json_filecache(obj, PLAYERS_CHOSEN_DEFAULTS_FILENAME, 0)
    Dialog().ok(f'{tmdb_type} - {tmdb_id}', msg)
