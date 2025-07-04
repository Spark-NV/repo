from tmdbhelper.lib.files.ftools import cached_property
from tmdbhelper.lib.addon.plugin import get_localized, executebuiltin
from tmdbhelper.lib.addon.dialog import BusyDialog
from xbmcgui import Dialog


class ItemSyncCachedProperties:
    @cached_property
    def kodi_log(self):
        return self.get_kodi_log()

    @cached_property
    def trakt_api(self):
        return self.get_trakt_api()

    @cached_property
    def query_database(self):
        return self.get_query_database()

    @cached_property
    def trakt_syncdata(self):
        return self.get_trakt_syncdata()

    @cached_property
    def trakt_sync_value(self):
        return self.get_trakt_sync_value()

    @cached_property
    def name_add(self):
        return self.get_name_add()

    @cached_property
    def name_remove(self):
        return self.get_name_remove()

    @cached_property
    def name(self):
        return self.get_name()

    @cached_property
    def is_sync(self):
        return self.get_is_sync()

    @cached_property
    def remove(self):
        return self.get_remove()

    @cached_property
    def is_allowed_type(self):
        return self.get_is_allowed_type()

    @cached_property
    def method(self):
        return self.get_method()

    @cached_property
    def trakt_type(self):
        return self.get_trakt_type()

    @cached_property
    def base_trakt_type(self):
        return self.get_base_trakt_type()

    @cached_property
    def item_id(self):
        return self.get_item_id()

    @cached_property
    def dialog_message(self):
        return self.get_dialog_message()

    @cached_property
    def trakt_slug(self):
        return self.get_trakt_slug()

    @cached_property
    def sync_response(self):
        return self.get_sync_response()

    @cached_property
    def post_response_args(self):
        return self.get_post_response_args()

    @cached_property
    def post_response_data(self):
        return self.get_post_response_data()

    @cached_property
    def post_response_type(self):
        return self.get_post_response_type()

    @cached_property
    def post_response_item(self):
        return self.get_post_response_item()

    @cached_property
    def sync_item(self):
        return self.get_sync_item()

    @cached_property
    def is_successful_sync(self):
        return self.get_is_successful_sync()

    @cached_property
    def dialog_header(self):
        return self.get_dialog_header()


class ItemSyncGetters:
    def get_kodi_log(self):
        from tmdbhelper.lib.addon.logger import kodi_log
        return kodi_log

    def get_trakt_api(self):
        from tmdbhelper.lib.api.trakt.api import TraktAPI
        return TraktAPI()

    def get_query_database(self):
        from tmdbhelper.lib.query.database.database import FindQueriesDatabase
        return FindQueriesDatabase()

    def get_trakt_syncdata(self):
        return self.trakt_api.trakt_syncdata

    def get_trakt_sync_value(self):
        return self.trakt_syncdata.get_value(self.tmdb_type, self.tmdb_id, self.season, self.episode, self.trakt_sync_key)

    def get_name_add(self):
        if not self.localized_name_add:
            return 'FIXME'
        return get_localized(self.localized_name_add)

    def get_name_remove(self):
        if not self.localized_name_rem:
            return 'FIXME'
        return get_localized(self.localized_name_rem)

    def get_name(self):
        if not self.preconfigured:
            if not self.remove:
                return self.name_add
            return self.name_remove
        if not self.localized_name:
            return 'FIXME'
        return get_localized(self.localized_name)

    def get_is_sync(self):
        if self.trakt_sync_value:
            return True
        return False

    def get_remove(self):
        if self.is_sync:
            return True
        return False

    def get_is_allowed_type(self):
        if self.trakt_type == 'episode':
            return bool(self.allow_episodes)
        if self.trakt_type == 'season':
            return bool(self.allow_seasons)
        if self.trakt_type == 'show':
            return bool(self.allow_shows)
        if self.trakt_type == 'movie':
            return bool(self.allow_movies)
        return False

    def get_method(self):
        if not self.remove:
            return self.trakt_sync_url
        return f'{self.trakt_sync_url}/remove'

    def get_trakt_type(self):
        if self.tmdb_type == 'movie':
            return 'movie'
        if self.tmdb_type != 'tv':
            return
        if self.season is None:
            return 'show'
        if self.episode is None:
            return 'season'
        return 'episode'

    def get_base_trakt_type(self):
        if self.tmdb_type == 'movie':
            return 'movie'
        if self.tmdb_type != 'tv':
            return
        return 'show'

    def get_item_id(self):
        return '.'.join([i for i in (self.tmdb_id, self.season, self.episode) if i])

    def get_dialog_message(self):
        if not self.sync_response:
            return
        if self.sync_response.status_code == 420:
            dialog_message = f'{get_localized(32296)}\n{get_localized(32531)}'
        elif not self.is_successful_sync:
            dialog_message = f'{get_localized(32296)}\nHTTP {self.sync_response.status_code}'
        else:
            dialog_message = get_localized(32297)
        return dialog_message.format(self.dialog_header, self.tmdb_type, 'TMDb', self.item_id)

    def get_trakt_slug(self):
        return self.query_database.get_trakt_id(self.tmdb_id, 'tmdb', self.base_trakt_type, output_type='slug')

    def get_sync_response(self):
        """ Called after user selects choice """
        with BusyDialog():
            return self.trakt_api.post_response(*self.post_response_args, postdata=self.post_response_data)

    def get_post_response_args(self):
        return ('sync', self.method, )

    def get_post_response_data(self):
        return {f'{self.post_response_type}': self.post_response_item}

    def get_post_response_type(self):
        if self.trakt_type == 'season':
            return 'episodes'
        return f'{self.trakt_type}s'

    def get_post_response_item(self):
        if isinstance(self.sync_item, list):
            return self.sync_item
        return [self.sync_item]

    def get_sync_item(self):
        if self.season is None:
            return self.trakt_api.get_response_json(f'{self.base_trakt_type}s', self.trakt_slug)
        if self.episode is None:
            return self.trakt_api.get_response_json('shows', self.trakt_slug, 'seasons', self.season)
        return self.trakt_api.get_response_json('shows', self.trakt_slug, 'seasons', self.season, 'episodes', self.episode)

    def get_is_successful_sync(self):
        if not self.sync_response:
            return False
        if self.sync_response.status_code not in [200, 201, 204]:
            return False
        return True

    def get_dialog_header(self):
        return self.name

    def get_self(self):
        """ Method to see if we should return item in menu or not """

        # Check that we allow this content type
        if not self.is_allowed_type:
            return

        # Allow early exit for preconfigured items (e.g. watched history to give both choices)
        if self.preconfigured:
            return self

        # Just check property to check sync now
        if not self.is_sync:
            pass

        return self


class ItemSync(ItemSyncGetters, ItemSyncCachedProperties):
    preconfigured = False
    allow_movies = True
    allow_shows = True
    allow_seasons = False
    allow_episodes = False
    localized_name_add = None
    localized_name_rem = None
    localized_name = None
    trakt_sync_key = None
    trakt_sync_url = None
    convert_episodes = False
    convert_seasons = False

    def __init__(self, tmdb_type, tmdb_id, season=None, episode=None):
        self.tmdb_type = tmdb_type
        self.tmdb_id = tmdb_id
        self.season = None if self.convert_seasons else season
        self.episode = None if self.convert_episodes else episode

    def refresh_containers(self):
        if not self.is_successful_sync:
            return
        from tmdbhelper.lib.script.method.kodi_utils import container_refresh
        container_refresh()

    def display_dialog(self):
        if not self.dialog_message:
            return
        Dialog().ok(self.dialog_header, self.dialog_message)

    def reset_lastactivities(self):
        if not self.is_successful_sync:
            return
        self.trakt_syncdata.reset_lastactivities()

    def sync(self):
        self.reset_lastactivities()
        self.display_dialog()
        self.refresh_containers()
