from tmdbhelper.lib.addon.thread import SafeThread
from tmdbhelper.lib.files.ftools import cached_property


CRONJOB_POLL_TIME = 600


class CronJobMonitor(SafeThread):

    _poll_time = CRONJOB_POLL_TIME

    def __init__(self, parent, update_hour=0):
        SafeThread.__init__(self)
        self.exit = False
        self.update_hour = update_hour
        self.update_monitor = parent.update_monitor

    def _on_startup(self):
        self._do_delete_old_databases()
        self._do_recache_kodidb()
        self._do_trakt_authorization()
        self._do_update_players_first_run()

    def _on_poll(self):
        self._do_database_vacuum()
        self._do_library_update_check()
        self._do_reset_trakt_lastactivities()

    @cached_property
    def trakt_api(self):
        from tmdbhelper.lib.api.trakt.api import TraktAPI
        return TraktAPI()

    @staticmethod
    def _do_database_vacuum():
        from tmdbhelper.lib.script.method.maintenance import vacuum_databases
        vacuum_databases()

    @staticmethod
    def _do_delete_old_databases():
        from tmdbhelper.lib.script.method.maintenance import clean_old_databases
        clean_old_databases()

    @staticmethod
    def _do_recache_kodidb():
        from tmdbhelper.lib.script.method.maintenance import recache_kodidb
        recache_kodidb(notification=False)

    def _do_trakt_authorization(self):
        from jurialmunkey.parser import boolean
        from jurialmunkey.window import get_property
        self.trakt_api.authorize(confirmation=True)
        self.update_monitor.waitForAbort(1)
        if not boolean(get_property('TraktIsAuth')):
            return
        from tmdbhelper.lib.script.method.trakt import get_stats
        get_stats()

    def _do_reset_trakt_lastactivities(self):
        from jurialmunkey.window import get_property
        from tmdbhelper.lib.addon.consts import LASTACTIVITIES_DATA
        get_property(LASTACTIVITIES_DATA, clear_property=True)

    def _do_update_players_first_run(self):
        from tmdbhelper.lib.addon.plugin import executebuiltin
        from tmdbhelper.lib.files.futils import get_file_path
        import os
        
        # Check if this is first run by looking for a marker file
        first_run_marker = get_file_path('', '.first_run_complete')
        if not os.path.exists(first_run_marker):
            # First run - automatically update players
            executebuiltin('RunScript(plugin.video.themoviedb.helper, update_players)')

    def _do_library_update(self):
        from tmdbhelper.lib.addon.plugin import executebuiltin
        from tmdbhelper.lib.addon.tmdate import get_datetime_now, get_timedelta
        executebuiltin('RunScript(plugin.video.themoviedb.helper,library_autoupdate)')
        executebuiltin(f'Skin.SetString(TMDbHelper.AutoUpdate.LastTime,{get_datetime_now().strftime("%Y-%m-%dT%H:%M:%S")})')
        self.library_update_next += get_timedelta(hours=24)  # Set next update for tomorrow

    def _do_library_update_check(self):
        # DISABLED: Automatic library updates are disabled to prevent unwanted updates
        # Manual updates can still be triggered via: RunScript(plugin.video.themoviedb.helper,library_autoupdate,busy_dialog,force=select)
        # This allows skin-based control of when updates occur
        return
        
        # Original automatic update code (commented out):
        # from jurialmunkey.parser import try_int
        # from tmdbhelper.lib.addon.tmdate import convert_timestamp, get_datetime_now, get_timedelta, get_datetime_today, get_datetime_time, get_datetime_combine
        # from tmdbhelper.lib.addon.plugin import get_setting, get_infolabel
        # if not get_setting('library_autoupdate'):
        #     return
        # self.library_update_next = get_datetime_combine(get_datetime_today(), get_datetime_time(try_int(self.update_hour)))
        # self.library_update_last = get_infolabel('Skin.String(TMDbHelper.AutoUpdate.LastTime)')
        # self.library_update_last = convert_timestamp(self.library_update_last) if self.library_update_last else None

        # # If we've already updated the library today then set a new next update time for tomorrow
        # if self.library_update_last and self.library_update_last > self.library_update_next:
        #     self.library_update_next += get_timedelta(hours=24)

        # # If the next update timestamp has elapsed then we should update the library
        # if get_datetime_now() > self.library_update_next:
        #     self._do_library_update()

    def run(self):
        self._on_startup()

        while not self.update_monitor.abortRequested() and not self.exit:
            self.update_monitor.waitForAbort(self._poll_time)
            self._on_poll()
