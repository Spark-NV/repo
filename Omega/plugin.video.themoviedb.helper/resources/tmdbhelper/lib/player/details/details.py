from jurialmunkey.parser import try_int, del_empty_keys
from tmdbhelper.lib.files.ftools import cached_property
from tmdbhelper.lib.api.tmdb.api import TMDb


EXTERNAL_ID_TYPES = ['tmdb', 'tvdb', 'imdb', 'slug', 'trakt']


class PlayerNextEpisodes:
    def __init__(self, tmdb_id, season, episode, player=None):
        self.tmdb_id = try_int(tmdb_id)
        self.season = try_int(season)
        self.episode = try_int(episode)
        self.player = player

    @cached_property
    def lidc(self):
        from tmdbhelper.lib.items.database.listitem import ListItemDetails
        lidc = ListItemDetails()
        lidc.cache_refresh = 'basic'
        lidc.extendedinfo = False
        return lidc

    @cached_property
    def parent_data(self):
        from tmdbhelper.lib.items.database.baseitem_factories.factory import BaseItemFactory
        sync = BaseItemFactory('tvshow')
        sync.tmdb_id = self.tmdb_id
        return sync.data

    @cached_property
    def all_episodes(self):
        from tmdbhelper.lib.items.database.baseview_factories.factory import BaseViewFactory
        sync = BaseViewFactory('flatseasons', 'tv', self.tmdb_id)
        return sync.data

    @cached_property
    def next_episodes(self):
        return [i for i in self.all_episodes if self.is_future_episode(i)]

    @cached_property
    def finalised_items(self):
        return [self.finalise_item(li) for li in self.configured_items if li]

    @cached_property
    def configured_items(self):
        return self.lidc.configure_listitems_threaded(self.next_episodes)

    def is_future_episode(self, i):
        s_number = try_int(i['infolabels'].get('season', -1))
        e_number = try_int(i['infolabels'].get('episode', -1))
        if s_number < self.season:
            return False
        if s_number > self.season:
            return True
        if e_number < self.episode:
            return False
        return True

    def finalise_item(self, li):
        li.finalise()
        if not self.player:
            return li
        li.params['player'] = self.player
        li.params['mode'] = 'play'
        return li

    @cached_property
    def listitems(self):
        if not self.items:
            return
        return [li.get_listitem() for li in self.items if li]

    @cached_property
    def items(self):
        if not self.parent_data:
            return
        if not self.all_episodes:
            return
        if not self.next_episodes:
            return
        if not self.configured_items:
            return
        return self.finalised_items


def get_next_episodes(tmdb_id, season, episode, player=None):
    return PlayerNextEpisodes(tmdb_id, season, episode, player).listitems


def get_external_ids(tmdb_type, tmdb_id, season=None, episode=None):
    from tmdbhelper.lib.api.trakt.api import TraktAPI
    from tmdbhelper.lib.query.database.database import FindQueriesDatabase

    trakt_api = TraktAPI()
    trakt_type = 'movie' if tmdb_type == 'movie' else 'show'
    if not tmdb_id or not trakt_type:
        return

    trakt_slug = FindQueriesDatabase().get_trakt_id(id_type='tmdb', id_value=tmdb_id, item_type=trakt_type, output_type='slug')
    if not trakt_slug:
        return

    details = trakt_api.get_response_json(f'{trakt_type}s', trakt_slug)
    if not details or not details.get('ids'):
        return

    if episode is not None:
        _uids = {f'tvshow.{i}': details['ids'][i] for i in EXTERNAL_ID_TYPES if details['ids'].get(i)}
        _episode_details_ids = trakt_api.get_response_json('shows', trakt_slug, 'seasons', season, 'episodes', episode).get('ids') or {}
        _uids.update({f'{i}': _episode_details_ids[i] for i in EXTERNAL_ID_TYPES if _episode_details_ids.get(i)})
        _uids['tvshow.tmdb'] = tmdb_id
    else:
        _uids = {i: details['ids'][i] for i in EXTERNAL_ID_TYPES if details['ids'].get(i)}
        _uids['tmdb'] = tmdb_id

    return {'unique_ids': _uids}


def get_item_details(tmdb_type, tmdb_id, season=None, episode=None, language=None):
    from tmdbhelper.lib.items.listitem import ListItem
    from tmdbhelper.lib.items.database.listitem import ListItemDetails

    lidc = ListItemDetails()
    lidc.cache_refresh = None
    lidc.extendedinfo = True

    details = lidc.get_item(tmdb_type, tmdb_id, season, episode)

    if not details:
        return

    return ListItem(**details)


def _get_language_details(tmdb_type, tmdb_id, season=None, episode=None, language=None):
    affix = ''
    if tmdb_type == 'tv':
        if season is not None:
            affix = f'{affix}season/{season}/'
            if episode is not None:
                affix = f'{affix}episode/{episode}/'
    affix = f'{affix}translations'
    details = TMDb().get_response_json(tmdb_type, tmdb_id, affix)
    if not details or not details.get('translations'):
        return

    item = {}
    for i in details['translations']:
        if i.get('iso_639_1') == language:
            item['title'] = i.get('data', {}).get('title') or i.get('data', {}).get('name')
            item['plot'] = i.get('data', {}).get('overview')
            return item


def _get_language_item(tmdb_type, tmdb_id, season=None, episode=None, language=None, year=None):
    item = _get_language_details(tmdb_type, tmdb_id, language=language)
    if not item:
        return

    item['showname'] = item['clearname'] = item['tvshowtitle'] = item.get('title')
    item['name'] = f'{item["title"]} ({year})' if item.get('title') and year else None
    if season is None or episode is None:
        return item

    episode = _get_language_details(tmdb_type, tmdb_id, season, episode, language=language)
    if not episode:
        return item

    item['title'] = episode.get('title')
    item['plot'] = episode.get('plot') or item.get('plot')
    item['name'] = f'{item["showname"]} S{try_int(season):02d}E{try_int(episode):02d}' if item.get('showname') else None
    return item


def get_language_details(base, tmdb_type, tmdb_id, season=None, episode=None, language=None, year=None):
    if not language:
        return base
    item = _get_language_item(tmdb_type, tmdb_id, season, episode, language, year)
    if not item:
        return base
    item = {k: v or base.get(k) for k, v in item.items()}  # Fallback to default key in base if translation is empty
    item = _url_encode_item(item)
    for k, v in item.items():
        base[f'{language}_{k}'] = v
    return _url_encode_item(base)


def _url_encode_item(item, base=None):
    from tmdbhelper.lib.addon.consts import PLAYERS_URLENCODE
    from urllib.parse import quote_plus, quote
    from json import dumps
    base = base or item.copy()
    for k, v in base.items():
        if k not in PLAYERS_URLENCODE:
            continue
        v = f'{v}'
        d = {k: v, f'{k}_meta': dumps(v)}
        for key, value in d.items():
            item[key] = value.replace(',', '')
            item[key + '_+'] = value.replace(',', '').replace(' ', '+')
            item[key + '_-'] = value.replace(',', '').replace(' ', '-')
            item[key + '_escaped'] = quote(quote(value))
            item[key + '_escaped+'] = quote(quote_plus(value))
            item[key + '_url'] = quote(value)
            item[key + '_url+'] = quote_plus(value)
    return item


def set_detailed_item(tmdb_type, tmdb_id, season=None, episode=None, details=None):
    from tmdbhelper.lib.addon.tmdate import get_datetime_now
    from collections import defaultdict
    if not details:
        return
    item = defaultdict(lambda: '_')
    item['id'] = item['tmdb'] = tmdb_id
    item['imdb'] = details.unique_ids.get('imdb')
    item['tvdb'] = details.unique_ids.get('tvdb')
    item['trakt'] = details.unique_ids.get('trakt')
    item['slug'] = details.unique_ids.get('slug')
    item['season'] = season
    item['episode'] = episode
    item['originaltitle'] = details.infoproperties.get('tvshow.originaltitle') or details.infolabels.get('originaltitle')
    item['title'] = details.infolabels.get('tvshowtitle') or details.infolabels.get('title')
    item['showname'] = item['clearname'] = item['tvshowtitle'] = item.get('title')
    item['year'] = details.infolabels.get('year')
    item['name'] = f'{item.get("title")} ({item.get("year")})'
    item['premiered'] = item['firstaired'] = item['released'] = details.infolabels.get('premiered')
    item['plot'] = details.infolabels.get('plot')
    item['cast'] = item['actors'] = " / ".join([i.get('name') for i in details.cast if i.get('name')])
    item['thumbnail'] = details.art.get('thumb')
    item['poster'] = details.art.get('poster')
    item['fanart'] = details.art.get('fanart')
    item['now'] = get_datetime_now().strftime('%Y%m%d%H%M%S%f')

    if tmdb_type == 'tv' and season is not None and episode is not None:
        item['id'] = item['epid'] = item['eptvdb'] = item.get('tvdb')
        item['title'] = details.infolabels.get('title')  # Set Episode Title
        item['name'] = f'{item.get("showname")} S{try_int(season):02d}E{try_int(episode):02d}'
        item['season'] = season
        item['episode'] = episode
        item['showpremiered'] = details.infoproperties.get('tvshow.premiered')
        item['showyear'] = details.infoproperties.get('tvshow.year')
        item['eptmdb'] = details.unique_ids.get('tmdb')
        item['epimdb'] = details.unique_ids.get('imdb')
        item['eptrakt'] = details.unique_ids.get('trakt')
        item['epslug'] = details.unique_ids.get('slug')
        item['tmdb'] = details.unique_ids.get('tvshow.tmdb')
        item['imdb'] = details.unique_ids.get('tvshow.imdb')
        item['tvdb'] = details.unique_ids.get('tvshow.tvdb')
        item['trakt'] = details.unique_ids.get('tvshow.trakt')
        item['slug'] = details.unique_ids.get('tvshow.slug')

    return _url_encode_item(item)
