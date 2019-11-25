# -*- coding: utf-8 -*-

CONST = {
	'BASE_URL' 		: 'https://www.joyn.de',
	'PSF_CONFIG_URL'	: 'https://psf.player.v0.maxdome.cloud/config/psf.json',
	'PSF_URL'		: 'https://psf.player.v0.maxdome.cloud/dist/playback-source-fetcher.min.js',
	'ENTITLEMENT_URL'	: 'entitlement-token/anonymous',
	'IP_API_URL'		: 'http://ip-api.com/json?lang={:s}&fields=status,country,countryCode',
	'AUTH_URL'		: 'https://auth.joyn.de/auth',
	'AUTH_ANON_URL'		: '/anonymous',
	'AUTH_REFRESH'		: '/refresh',

	'PSF_VAR_DEFS'		: {
					'SECRET' : {
							'INDEX'		: 1192,
							'VAL_BEFORE'	: 'vas',
							'VAL_AFTER'	: '@oasis/vas-sdk',
							'FALLBACK'	: '5C7838365C7864665C786638265C783064595C783935245C7865395C7838323F5C7866333D3B5C78386635',
						   },
				  },


	'COUNTRIES'		: {
					 'DE' : {
							'language'    : 'de',
							'setting_id'  : '1',
						},
				  },

	'CACHE_DIR'		: 'cache',
	'TEMP_DIR'		: 'tmp',
	'DATA_DIR'		: 'data',
	'CACHE'			: {
					'CONFIG'	: { 'key' : 'config', 'expires' : 3600 },
					'EPG'		: { 'key' : 'epg', 'expires': 36000 },
					'LANDINGPAGE'	: { 'key' : 'landingpage', 'expires' : 600},
					'ETAGS'		: { 'key' : 'etags', 'expires': None},
				  },

	'ETAGS_TTL'		: 1209600, #14 days

	'LASTSEEN_ITEM_COUNT'	: 20,
	'UPEG_REFRESH_INTERVAL'	: 7200,
	'UPEG_ROWCOUNT'		: 5,
	'INPUTSTREAM_ADDON'	: 'inputstream.adaptive',

	'MSG_IDS'		: {
					'ADD_TO_WATCHLIST'		: 30651,
					'ADD_TO_WATCHLIST_PRX'		: 30653,
					'REMOVE_FROM_WATCHLIST'		: 30652,
					'REMOVE_FROM_WATCHLIST_PRFX'	: 30654,
					'MEDIA_LIBRARY'			: 30622,
					'CATEGORY'			: 30623,
					'TV_SHOW'			: 30624,
					'SEASON'			: 30625,
					'EPISODE'			: 30625,
					'WATCHLIST'			: 30601,
					'MEDIA_LIBRARIES'		: 30602,
					'CATEGORIES'			: 30603,
					'SEARCH'			: 30604,
					'LIVE_TV'			: 30605,
					'TV_GUIDE'			: 30606,
					'MEDIA_LIBRARIES_PLOT'		: 30608,
					'CATEGORIES_PLOT'		: 30609,
					'WATCHLIST_PLOT'		: 30607,
					'SEARCH_PLOT'			: 30610,
					'LIVE_TV_PLOT'			: 30611,
					'TV_GUIDE_PLOT'			: 30612,
					'WL_TYPE_ADDED'			: 30526,
					'WL_TYPE_REMOVED'		: 30527,
					'MSG_INPUSTREAM_NOT_ENABLED'	: 30501,
					'MSG_WIDEVINE_NOT_FOUND'	: 30502,
					'MSG_NO_SEARCH_RESULTS'		: 30525,
					'MSG_NO_FAVS_YET'		: 30528,
					'MSG_FAVS_UNAVAILABLE'		: 30529,
					'ERROR'				: 30521,
					'MSG_ERR_TRY_AGAIN'		: 30522,
					'MSG_ERROR_CONFIG_DECRYPTION'	: 30523,
					'MSG_ERROR_NO_VIDEOSTEAM'   	: 30524,
					'LIVETV_TITLE'			: 30655,
					'LIVETV_UNTIL'			: 30656,
					'LIVETV_UNTIL_AND_NEXT'		: 30657,
					'MIN_AGE'			: 30658,
					'VIDEO_AVAILABLE'		: 30650,
					'SEASON_NO'			: 30621,
					'MSG_CONFIG_VALUES_INCOMPLETE'	: 30530,
					'MSG_NO_ACCESS_TO_URL'		: 30531,
					'MSG_COUNTRY_NOT_DETECTED'	: 30532,
					'MSG_COUNTRY_INVALID'		: 30533,
					'CANCEL'			: 30503,
					'OPEN_ADDON_SETTINGS'		: 30504,
					'CACHE_WAS_CLEARED'		: 30659,
					'CACHE_COULD_NOT_BE_CLEARED'	: 30660,
					'LANG_CODE'			: 30661,
					'MSG_VIDEO_UNAVAILABLE'         : 30662,
					'MSG_GAPHQL_ERROR'              : 30663,
					'MSG_NO_CONTENT'		: 30664,
					'CONTINUE_WATCHING'		: 30665,
					'RECOMMENDATION'		: 30666,
					'MOVIE'				: 30667,
					'SERIES'			: 30668,
					'TITLE_LABEL'			: 30669,

				},

	'VIEW_MODES'		: {
					'Standard'	:  {
								'skin.estuary' : '0',
							  },
					'List'		: {
								'skin.estuary' : '50',
							  },
					'Poster'	: {
								'skin.estuary' : '51',
							  },
					'IconWall'	: {
								'skin.estuary' : '52',
							  },

					'Shift'		: {
								'skin.estuary' : '53',
							  },
					'InfoWall'	: {
								'skin.estuary' : '54',
							  },
					'WideList'	: {
								'skin.estuary' : '55',
							  },
					'Wall'		: {
								'skin.estuary' : '500',
							  },
					'Banner'	: {
								'skin.estuary' : '501',
							  },
					'Fanart'	: {
								'skin.estuary' : '502',
							  },

				},


	'FOLDERS'		: {

					'INDEX'		: {
								'content_type'	: 'tags',
								'view_mode'	: 'categories_view',
							},

					'CATEORIES'	: {
								'content_type'	: 'tags',
								'view_mode'	: 'categories_view',
								'cacheable'	: True,
							},

					'MEDIA_LIBS'	: {
								'content_type'	: 'tags',
								'view_mode'	: 'categories_view',
								'cacheable'	: True,
							},

					'WATCHLIST'	: {
								'content_type'	: 'videos',
								'view_mode'	: 'watchlist_view',
							},


					'CATEGORY'	: {
								'content_type'	: 'tvshows',
								'view_mode'	: 'category_view',
								'cacheable'	: True,
							},

					'LIVE_TV'	: {
								'content_type'	: 'videos',
								'view_mode'	: 'livetv_view',
							},

					'TV_SHOWS'	: {

								'content_type'	: 'tvshows',
								'view_mode'	: 'tvshow_view',
								'cacheable'	: True,
							},


					'SEASONS'	: {
								'content_type'	: 'seasons',
								'view_mode'	: 'season_view',
								'sort'		: {
											'order_type'	: '7', #SortByTitle
											'setting_id'	: 'season_order',
										},
								'cacheable'	: True,
							},

					'EPISODES'	: {
								'content_type'	: 'episodes',
								'view_mode'	: 'episode_view',
								'sort'		: {
											'order_type' 	: '23', #SortByEpisodeNumber
											'setting_id'	: 'episode_order',
										},
								'cacheable'	: True,

							},


			},

	'SETTING_VALS'	: {

			'SORT_ORDER_DEFAULT'	: '0',
			'SORT_ORDER_ASC'	: '1',
			'SORT_ORDER_DESC'	: '2',
	},

	'GRAPHQL'	: {

			'API_URL'		: 'https://api.joyn.de/graphql',

			'REQUIRED_HEADERS'	: ['x-api-key', 'joyn-platform'],


			'STATIC_VARIABLES'	: {
							'first':	1000,
							'offset':	0,
						},

			'METADATA'		: {
							'TVCHANNEL'	: {
										'TEXTS' : {'title' : 'title'},
										'ART'	: {'logo' : {
													'BRAND_LOGO' : {
														'icon'   	: 'profile:nextgen-web-artlogo-183x75',
														'thumb'  	: 'profile:original',
														'clearlogo'	: 'profile:nextgen-web-artlogo-183x75',
													},
												},
											},
							},

							'TVSHOW'	: {
										'TEXTS' : {'title' : 'title', 'description' : 'plot'},
										'ART'	: {'images' : {
													'PRIMARY'        : {
														'thumb'		: 'profile:original'
														},
													'ART_LOGO' : {
														'icon'		: 'profile:nextgen-web-artlogo-183x75',
														'clearlogo'	: 'profile:nextgen-web-artlogo-183x75',
														'clearart'	: 'profile:nextgen-web-artlogo-183x75',
														},
													'HERO_LANDSCAPE' : {
														'fanart'	: 'profile:nextgen-web-herolandscape-1920x',
														'landscape'	: 'profile:nextgen-web-herolandscape-1920x',
														},
													'HERO_PORTRAIT'  : {
														'poster'	: 'profile:nextgen-webphone-heroportrait-563x',
														},
											},

										},
							},

							'EPISODE'	: {
										'TEXTS' : {'title': 'title', 'description' : 'plot'},
										'ART'	: {'images' : {
													'PRIMARY'        : {
														'thumb'		: 'profile:original'
													},
													'ART_LOGO'       : {
														'icon'   	: 'profile:nextgen-web-artlogo-183x75',
														'clearlogo'	: 'profile:nextgen-web-artlogo-183x75',
													},
													'HERO_LANDSCAPE' : {
														'fanart' 	: 'profile:nextgen-web-herolandscape-1920x',
													},
											 '		HERO_PORTRAIT'  : {
														'poster' 	: 'profile:nextgen-webphone-heroportrait-563x'
													},
											},

										},
							},

							'EPG'	: {
										'TEXTS' : {'title': 'title', 'secondaryTitle' : 'plot'},
										'ART'	: {'images' : {
													'LIVE_STILL'        : {
														'poster'	: 'profile:original',
														'thumb'		: 'profile:original',
													},
											},

										},
							},


			},

			'GET_BONUS'		: {
							'QUERY' : '($seriesId: ID!, $first: Int!, $offset: Int!) { series(id: $seriesId) { __typename id ageRating { __typename '\
								'label minAge ratingSystem } extras(first: $first, offset: $offset) { __typename id title video { __typename duration id } '\
								'images { __typename id copyright type url accentColor } tracking { __typename primaryAirdateBrand agofCode trackingId '\
								'visibilityStart webExclusive adfree brand url } }  }}',

							'OPERATION' : 'getBonus',
							'REQUIRED_VARIABLES'	: ['seriesId', 'first', 'offset']
						},

			'GET_BRANDS'		: {	'QUERY'	: '{ brands { __typename id livestream { __typename id agofCode title quality } logo { __typename accentColor url } '\
								'hasVodContent title } }',

							'OPERATION' : 'getBrands',
							'REQUIRED_VARIABLES'	: [],

			},

			'LANDINGPAGE'		: {
							'QUERY' : '($path: String!) { page(path: $path) {__typename... on LandingPage { blocks { __typename id isPersonalized ... '\
								'on StandardLane { headline } ... on FeaturedLane { headline } ... on LiveLane { headline } ... on ResumeLane { headline } ... on '\
								'ChannelLane { headline } ... on BookmarkLane { headline } }} }}',

							'OPERATION' : 'LandingPage',
							'REQUIRED_VARIABLES' : ['path'],
			},

			'SINGLEBLOCK'		: {
							'QUERY' : '($blockId: String!, $offset: Int!, $first: Int!) { block(id: $blockId) { __typename id assets(offset: $offset, first: $first) '\
								'{ __typename ...MovieCoverFragment ...SeriesCoverFragment ...BrandCoverFragment ...EpisodeCoverFragment ...EpgFragment '\
								'...CompilationCoverFragment } ... on HeroLane { heroLaneAssets: assets { __typename ... on Series { id ageRating { __typename '\
								'label minAge ratingSystem } nextEpisode { __typename id resumePosition { __typename position } video { __typename id duration '\
								'quality } number season { __typename number } title endsAt genres { __typename name type } tracking { __typename primaryAirdateBrand '\
								'agofCode trackingId visibilityStart brand } airdate } isBingeable subtype } } } } } fragment MovieCoverFragment on Movie { __typename '\
								'id brands { __typename id title logo { __typename url } } images { __typename accentColor type url } title tagline video { __typename '\
								'id duration } resumePosition { __typename position } description genres { __typename name } ageRating { __typename label minAge '\
								'ratingSystem } tracking { __typename primaryAirdateBrand agofCode trackingId visibilityStart brand } } fragment SeriesCoverFragment '\
								'on Series { __typename id brands { __typename id title logo { __typename url } } images { __typename accentColor type url } ageRating '\
								'{ __typename label minAge ratingSystem } title tagline numberOfSeasons description genres { __typename name } } fragment '\
								'BrandCoverFragment on Brand { __typename id title path logo { __typename type accentColor url } } fragment EpisodeCoverFragment on '\
								'Episode { __typename id title number endsAt resumePosition { __typename position } season { __typename number } video { __typename id '\
								'duration quality licenses { __typename startDate endDate type } } series { __typename id images { __typename accentColor url type } '\
								'brands { __typename id title logo { __typename url } } title tagline description genres { __typename name } ageRating { __typename '\
								'label minAge ratingSystem } } genres { __typename name type } tracking { __typename primaryAirdateBrand agofCode trackingId '\
								'visibilityStart brand } } fragment EpgFragment on EpgEntry { __typename id startDate endDate images { __typename type url accentColor'\
								'} title secondaryTitle livestream { __typename id brand { __typename id logo { __typename url accentColor } title } } } fragment '\
								'CompilationCoverFragment on Compilation { __typename id brands { __typename id title logo { __typename url } } images { __typename '\
								'accentColor type url } title numberOfItems path ageRating { __typename label minAge ratingSystem } }',

							'OPERATION' : 'SingleBlockQuery',
							'REQUIRED_VARIABLES' : ['blockId', 'offset', 'first'],


			},

			'CHANNEL'		: {
							'QUERY': '($path: String!, $offset: Int!, $first: Int!) { page(path: $path) { __typename ... on ChannelPage { assets(offset: $offset, '\
							'first: $first) { __typename ...MovieCoverFragment ...SeriesCoverFragment ...EpisodeCoverFragment ...CompilationCoverFragment } } } } '\
							'fragment MovieCoverFragment on Movie { __typename id brands { __typename id title logo { __typename url } } images { __typename accentColor '\
							'type url } title tagline video { __typename id duration } resumePosition { __typename position } description genres { __typename name } '\
							'ageRating { __typename label minAge ratingSystem } tracking { __typename primaryAirdateBrand agofCode trackingId visibilityStart brand } } '\
							'fragment SeriesCoverFragment on Series { __typename id brands { __typename id title logo { __typename url } } images { __typename '\
							'accentColor type url } ageRating { __typename label minAge ratingSystem } title tagline numberOfSeasons description genres { __typename '\
							'name } } fragment EpisodeCoverFragment on Episode { __typename id title number endsAt resumePosition { __typename position } '\
							'season { __typename number } video { __typename id duration quality licenses { __typename startDate endDate type } } series { '\
							'__typename id images { __typename accentColor url type } brands { __typename id title logo { __typename url } } title tagline description '\
							'genres { __typename name } ageRating { __typename label minAge ratingSystem } } genres { __typename name type } tracking { __typename '\
							'primaryAirdateBrand agofCode trackingId visibilityStart brand } } fragment CompilationCoverFragment on Compilation { __typename id brands '\
							'{ __typename id title logo { __typename url } } images { __typename accentColor type url } title numberOfItems path ageRating { __typename '\
							'label minAge ratingSystem } }',

							'OPERATION' : 'ChannelPageQuery',
							'REQUIRED_VARIABLES' : ['path', 'offset', 'first']
			},

			'SEASONS'		: {
							'QUERY': '($seriesId: ID!) { series(id: $seriesId) { __typename id title description images { __typename type url accentColor '\
								'} numberOfSeasons brands { __typename id logo { __typename id url accentColor } title }  trailer { __typename id title images '\
								'{ __typename id url } video { __typename id duration } } seasons { __typename id number numberOfEpisodes } genres { __typename '\
								'name type } ageRating { __typename label minAge ratingSystem } copyrights tagline isBingeable subtype } }',
							'OPERATION' : 'getSeries',
							'REQUIRED_VARIABLES' : ['seriesId'],
			},

			'EPISODES'		: {
							'QUERY': '($seasonId: ID!, $first: Int!, $offset: Int!) { season(id: $seasonId) { __typename number title episodes(first: $first, offset: '\
								'$offset) { __typename id number images { __typename id copyright type url accentColor } '\
								'series { __typename id title ageRating { __typename label minAge ratingSystem } images { __typename accentColor url type } } endsAt '\
								'airdate title description video { __typename id duration licenses { __typename startDate endDate type } } brands { __typename id '\
								'title } season { __typename number id numberOfEpisodes } genres { __typename name type } tracking { __typename primaryAirdateBrand '\
								'agofCode trackingId visibilityStart brand } } } }',

							'OPERATION' : 'getSeries',
							'REQUIRED_VARIABLES' : ['seasonId', 'first', 'offset'],

			},

			'COMPILATION_ITEMS'	: {
							'QUERY': '($id: ID!, $offset: Int!, $first: Int!) { compilation(id: $id) { __typename compilationItems(first: $first, offset: $offset) '\
								'{ __typename ... on CompilationItem {   ...CompilationItemCoverFragment } } } } fragment CompilationItemCoverFragment on '\
								'CompilationItem { __typename id compilation { __typename id title brands { __typename id logo {   __typename   url } title } path '\
								'images { __typename accentColor type url } ageRating { __typename label minAge ratingSystem } } description endsAt genres { '\
								'__typename name type } images { __typename accentColor type url } path startsAt title video '\
								'{ __typename id duration licenses { __typename startDate endDate type } } tracking { __typename primaryAirdateBrand agofCode '\
								'trackingId visibilityStart brand } }',
							'OPERATION' : 'GetCompilationItemsQuery',
							'REQUIRED_VARIABLES' : ['id', 'first', 'offset'],
			},

			'EPG'			: {
							'QUERY': '{ brands { __typename id livestream { __typename id title quality epg(first: 30) { __typename id startDate endDate '\
								'title secondaryTitle images { __typename id accentColor type url } } } logo { __typename type accentColor url } title } }',

							'OPERATION' : 'getEpg',
							'REQUIRED_VARIABLES'	: [],

			},

			'SEARCH'		: {
							'QUERY': '($text: String!) { search(term: $text, first: 50) { __typename results '\
								'{ __typename ...BrandCoverFragment ...SeriesCoverFragment ...MovieCoverFragment ...CompilationCoverFragment } } } fragment '\
								'BrandCoverFragment on Brand { __typename id title path logo { __typename type accentColor url } } fragment SeriesCoverFragment on '\
								'Series { __typename id brands { __typename id title logo { __typename url } } images { __typename accentColor type url } ageRating '\
								'{ __typename label minAge ratingSystem } title tagline numberOfSeasons description genres { __typename name } } fragment '\
								'MovieCoverFragment on Movie { __typename id brands { __typename id title logo { __typename url } } images { __typename accentColor '\
								'type url } title tagline video { __typename id duration } resumePosition { __typename position } description genres { __typename '\
								'name } ageRating { __typename label minAge ratingSystem } tracking { __typename primaryAirdateBrand agofCode trackingId '\
								'visibilityStart brand } } fragment CompilationCoverFragment on Compilation { __typename id brands { __typename id title logo '\
								'{ __typename url } } images { __typename accentColor type url } title numberOfItems path ageRating { __typename label minAge '\
								'ratingSystem } }',
							'OPERATION': 'searchQuery',
							'REQUIRED_VARIABLES': ['text'],
			},

	},

	'CATEGORY_LANES'			: ['StandardLane', 'FeaturedLane'],
	'NETBLOCKS'				: {
							'DE' : ['5.10.48.0/21', '5.1.128.0/17', '62.220.0.0/19', '84.19.192.0/20', '84.44.128.0/17'],
						},

}
