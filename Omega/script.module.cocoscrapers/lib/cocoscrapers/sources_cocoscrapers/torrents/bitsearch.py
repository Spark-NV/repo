# -*- coding: utf-8 -*-
# created by Venom for Fenomscrapers (updated 7-19-2022)
"""
	Fenomscrapers Project
"""

import re
from urllib.parse import quote_plus, unquote_plus
from cocoscrapers.modules import client
from cocoscrapers.modules import source_utils
from cocoscrapers.modules import workers
from cocoscrapers.modules import log_utils
from time import time


class source:
	priority = 3
	pack_capable = True
	hasMovies = True
	hasEpisodes = True
	def __init__(self):
		self.language = ['en']
		self.base_link = "https://bitsearch.to"
		# self.search_link = '/search?q=%s&category=1&subcat=2&sort=seeders'
# (1=other/video, 2=movies, 3=TV) but seem to produce bogus results, do not use
		self.search_link = '/search?q=%s&sort=size'
		self.item_totals = {
			'4K': 0,
			'1080p': 0,
			'720p': 0,
			'SD': 0,
			'CAM': 0 
			}
		self.min_seeders = 0

	def sources(self, data, hostDict):
		self.sources = []
		if not data: return self.sources
		self.sources_append = self.sources.append
		try:
			startTime = time()
			self.aliases = data['aliases']
			self.year = data['year']
			if 'tvshowtitle' in data:
				self.title = data['tvshowtitle'].replace('&', 'and').replace('Special Victims Unit', 'SVU').replace('/', ' ').replace('$', 's')
				self.episode_title = data['title']
				self.hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode']))
			else:
				self.title = data['title'].replace('&', 'and').replace('/', ' ').replace('$', 's')
				self.episode_title = None
				self.hdlr = self.year
			query = '%s %s' % (re.sub(r'[^A-Za-z0-9\s\.-]+', '', self.title), self.hdlr)
			urls = []
			url = '%s%s' % (self.base_link, self.search_link % quote_plus(query))
			urls.append(url)
			urls.append(url + '&page2')
			# log_utils.log('urls = %s' % urls)
			self.undesirables = source_utils.get_undesirables()
			self.check_foreign_audio = source_utils.check_foreign_audio()
			# from cocoscrapers.modules.Thread_pool import run_and_wait
			# from functools import partial
			# bound_get_sources = partial(self.get_sources)
			# run_and_wait(bound_get_sources, urls)
			threads = []
			append = threads.append
			for url in urls:
				append(workers.Thread(self.get_sources, url))
			[i.start() for i in threads]
			[i.join() for i in threads]
			logged = False
			for quality in self.item_totals:
				if self.item_totals[quality] > 0:
					log_utils.log('#STATS - BITSEARCH found {0:2.0f} {1}'.format(self.item_totals[quality],quality) )
					logged = True
			if not logged: log_utils.log('#STATS - BITSEARCH found nothing')
			endTime = time()
			log_utils.log('#STATS - BITSEARCH took %.2f seconds' % (endTime - startTime))
			return self.sources
		except:
			source_utils.scraper_error('BITSEARCH')
			return self.sources

	def get_sources(self, url):
		try:
			results = client.request(url, timeout=7)
			if not results or 'card search-result my-2' not in results: return
			rows = client.parseDOM(results, 'li', attrs={'class': 'card search-result my-2'})
		except:
			source_utils.scraper_error('BITSEARCH')
		for row in rows:
			try:
				if 'magnet:' not in row: continue
				columns = re.findall(r'<div.*?>(.*?)</div>', row, re.DOTALL)
				magnet_index = len(columns)-1 # likes might be added so magnet is in last index
				url = re.search(r'href\s*=\s*["\'](magnet:.+?)["\']', columns[magnet_index], re.I).group(1)
				url = unquote_plus(url).replace('&amp;', '&').replace('&#x3D;', '=')
				url = re.sub(r'(&tr=.+)&dn=', '&dn=', url).replace(' ', '.') # some links on bitsearch &tr= before &dn=
				hash = re.search(r'btih:(.*?)&', url, re.I).group(1)
				name = source_utils.clean_name(url.split('&dn=')[1])
				if not source_utils.check_title(self.title, self.aliases, name, self.hdlr, self.year): continue
				name_info = source_utils.info_from_name(name, self.title, self.year, self.hdlr, self.episode_title)
				if source_utils.remove_lang(name_info, self.check_foreign_audio): continue
				if self.undesirables and source_utils.remove_undesirables(name_info, self.undesirables): continue

				if not self.episode_title: #filter for eps returned in movie query (rare but movie and show exists for Run in 2020)
					ep_strings = [r'[.-]s\d{2}e\d{2}([.-]?)', r'[.-]s\d{2}([.-]?)', r'[.-]season[.-]?\d{1,2}[.-]?']
					name_lower = name.lower()
					if any(re.search(item, name_lower) for item in ep_strings): continue

				try:
					seeders = re.search(r'>([0-9]+|[0-9]+,[0-9]+|[0-9]+\.[0-9]+K)<', columns[2], re.S | re.I).group(1)
					if 'K' in seeders: seeders = float(seeders.rstrip('K')) * 1000
					seeders = int(seeders)
					if self.min_seeders > seeders: continue
				except: seeders = 0

				quality, info = source_utils.get_release_quality(name_info, url)
				try:
					size = re.search(r'>(.*?)$', columns[1]).group(1).replace(',', '')
					dsize, isize = source_utils._size(size)
					info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				self.sources_append({'provider': 'bitsearch', 'source': 'torrent', 'seeders': seeders, 'hash': hash, 'name': name, 'name_info': name_info,
												'quality': quality, 'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize})
				self.item_totals[quality]+=1
			except:
				source_utils.scraper_error('BITSEARCH')

	def sources_packs(self, data, hostDict, search_series=False, total_seasons=None, bypass_filter=False):
		self.sources = []
		if not data: return self.sources
		self.sources_append = self.sources.append
		try:
			startTime = time()
			self.search_series = search_series
			self.total_seasons = total_seasons
			self.bypass_filter = bypass_filter

			self.title = data['tvshowtitle'].replace('&', 'and').replace('Special Victims Unit', 'SVU').replace('/', ' ').replace('$', 's')
			self.aliases = data['aliases']
			self.imdb = data['imdb']
			self.year = data['year']
			self.season_x = data['season']
			self.season_xx = self.season_x.zfill(2)
			self.undesirables = source_utils.get_undesirables()
			self.check_foreign_audio = source_utils.check_foreign_audio()

			query = re.sub(r'[^A-Za-z0-9\s\.-]+', '', self.title)
			if search_series:
				queries = [
						self.search_link % quote_plus(query + ' Season'),
						self.search_link % quote_plus(query + ' Complete')]
			else:
				queries = [
						self.search_link % quote_plus(query + ' S%s' % self.season_xx),
						self.search_link % quote_plus(query + ' Season %s' % self.season_x)]
			# from cocoscrapers.modules.Thread_pool import run_and_wait
			# from functools import partial
			# bound_get_sources_packs = partial(self.get_sources_packs)
			# links = []
			# for url in queries:
			# 	links.append('%s%s' % (self.base_link, url))
			# run_and_wait(bound_get_sources_packs, links)
			threads = []
			append = threads.append
			for url in queries:
				link = '%s%s' % (self.base_link, url)
				append(workers.Thread(self.get_sources_packs, link))
			[i.start() for i in threads]
			[i.join() for i in threads]
			logged = False
			for quality in self.item_totals:
				if self.item_totals[quality] > 0:
					log_utils.log('#STATS - BITSEARCH(pack) found {0:2.0f} {1}'.format(self.item_totals[quality],quality) )
					logged = True
			if not logged: log_utils.log('#STATS - BITSEARCH(pack) found nothing')
			endTime = time()
			log_utils.log('#STATS - BITSEARCH(pack) took %.2f seconds' % (endTime - startTime))
			return self.sources
		except:
			source_utils.scraper_error('BITSEARCH')
			return self.sources

	def get_sources_packs(self, link):
		try:
			results = client.request(link, timeout=7)
			if not results or 'card search-result my-2' not in results: return
			rows = client.parseDOM(results, 'li', attrs={'class': 'card search-result my-2'})
		except:
			source_utils.scraper_error('BITSEARCH')
		for row in rows:
			try:
				if 'magnet:' not in row: continue
				columns = re.findall(r'<div.*?>(.*?)</div>', row, re.DOTALL)
				magnet_index = len(columns)-1 # likes might be added so magnet is in last index
				url = re.search(r'href\s*=\s*["\'](magnet:.+?)["\']', columns[magnet_index], re.I).group(1)
				url = unquote_plus(url).replace('&amp;', '&').replace('&#x3D;', '=')
				url = re.sub(r'(&tr=.+)&dn=', '&dn=', url).replace(' ', '.') # some links on bitsearch &tr= before &dn=
				hash = re.search(r'btih:(.*?)&', url, re.I).group(1)
				name = source_utils.clean_name(url.split('&dn=')[1])

				episode_start, episode_end = 0, 0
				if not self.search_series:
					if not self.bypass_filter:
						valid, episode_start, episode_end = source_utils.filter_season_pack(self.title, self.aliases, self.year, self.season_x, name)
						if not valid: continue
					package = 'season'

				elif self.search_series:
					if not self.bypass_filter:
						valid, last_season = source_utils.filter_show_pack(self.title, self.aliases, self.imdb, self.year, self.season_x, name, self.total_seasons)
						if not valid: continue
					else: last_season = self.total_seasons
					package = 'show'

				name_info = source_utils.info_from_name(name, self.title, self.year, season=self.season_x, pack=package)
				if source_utils.remove_lang(name_info, self.check_foreign_audio): continue
				if self.undesirables and source_utils.remove_undesirables(name_info, self.undesirables): continue

				try:
					seeders = re.search(r'>([0-9]+|[0-9]+,[0-9]+|[0-9]+\.[0-9]+K)<', columns[2], re.S | re.I).group(1)
					if 'K' in seeders: seeders = float(seeders.rstrip('K')) * 1000
					seeders = int(seeders)
					if self.min_seeders > seeders: continue
				except: seeders = 0

				quality, info = source_utils.get_release_quality(name_info, url)
				try:
					size = re.search(r'>(.*?)$', columns[1]).group(1).replace(',', '')
					dsize, isize = source_utils._size(size)
					info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				item = {'provider': 'bitsearch', 'source': 'torrent', 'seeders': seeders, 'hash': hash, 'name': name, 'name_info': name_info, 'quality': quality,
							'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize, 'package': package}
				if self.search_series: item.update({'last_season': last_season})
				elif episode_start: item.update({'episode_start': episode_start, 'episode_end': episode_end}) # for partial season packs
				self.sources_append(item)
				self.item_totals[quality]+=1
			except:
				source_utils.scraper_error('BITSEARCH')