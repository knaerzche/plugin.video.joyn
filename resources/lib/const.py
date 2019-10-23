#!/usr/bin/python
# -*- coding: utf-8 -*-

CONST = {
	'BASE_URL' 		: 'https://www.joyn.de',
	'PSF_CONFIG_URL'	: 'https://psf.player.v0.maxdome.cloud/config/psf.json',
	'PSF_URL'		: 'https://psf.player.v0.maxdome.cloud/dist/playback-source-fetcher.min.js',
	'MIDDLEWARE_URL'	: 'https://middleware.p7s1.io/joyn/v1/',
	'ENTITLEMENT_URL'	: 'entitlement-token/anonymous',
	'IP_API_URL'		: 'http://ip-api.com/json?lang={:s}&fields=status,country,countryCode',

	'PSF_VARS_IDX'		: {
					'SECRET' : 1192,
				  },

	'FALLBACK_SECRET'	: '5C7838365C7864665C786638265C783064595C783935245C7865395C7838323F5C7866333D3B5C78386635',

	'COUNTRIES'		: {
					 'DE' : {
							'language'    : 'de',
							'setting_id'  : '1',
						},
				  },

	'PATH'			: {

					'SEASON'	: {
								'PATH'	      	: 	'seasons',
								'QUERY_PARAMS' 	: 	{	'tvShowId' 		: '##tvShowId##',
												'sortBy'   		: 'seasonsOrder',
												'sortAscending'		: 'true',
												'limit'			: '5000',

											},
								'SELECTION'	:	'{data{id,channelId,visibilities,duration,tvShow,metadata{%s}}}',

								'INFOLABELS'	:	{
												'mediatype': 'season',
											},

								'TEXTS'		:	{'title' : 'main', 'description' : 'main'},
								'ART'		:	{},
								'SUBTYPE_ART'	:	{
												'tvShow' : {
														'cover'		: {
																	'fanart'   	: 'profile:nextgen-web-herolandscape-1920x',
																},
														'teaser'	: {
																	'thumb'		: 'profile:nextgen-webphone-heroportrait-563x',
																},
														'heroLandscape' : {
																	'fanart'   	: 'profile:nextgen-web-herolandscape-1920x',
																},
														'primary'	: {
																	'thumb'		: 'profile:nextgen-webphone-heroportrait-563x',
																},
														'heroPortrait' : {
																	'poster' 	: 'profile:nextgen-webphone-heroportrait-563x',
																},
													},
											},
							  },

					'VIDEO'		: {
								'PATH'	      	: 	'videos',
								'QUERY_PARAMS' 	: 	{	'tvShowId' 		: '##tvShowId##',
												'seasonId'   		: '##seasonId##',
												'sortBy'		: 'seasonsOrder',
												'sortAscending'		: 'true',
												'skip'			: '0',
												'limit'			: '5000',
											},
								'SELECTION'	:	'{totalCount,data{id,type,startTime,endTime,tvShow,season,episode,duration,metadata{%s}}}',

								'INFOLABELS'	:	{
												'mediatype': 'episode',
											},

								'TEXTS'		:	{'title' : 'main', 'description' : 'main'},
								'ART'		:	{'PRIMARY'        : {'thumb'  : 'profile:original'},
											 'ART_LOGO'       : {
														'icon'   	: 'profile:nextgen-web-artlogo-183x75',
														'clearlogo'	: 'profile:nextgen-web-artlogo-183x75',
													    },
											 'HERO_LANDSCAPE' : {'fanart' : 'profile:nextgen-web-herolandscape-1920x'},
											 'HERO_PORTRAIT'  : {'poster' : 'profile:nextgen-webphone-heroportrait-563x'},
											},

								'SUBTYPE_ART'	:	{
												'tvShow' : {
														'artLogo'	: {
																	'icon'   	: 'profile:nextgen-web-artlogo-183x75',
																	'clearlogo'	: 'profile:nextgen-web-artlogo-183x75',
																},
														'cover'		: {
																	'fanart'   	: 'profile:nextgen-web-herolandscape-1920x',
																},
														'heroLandscape' : {
																	'fanart'   	: 'profile:nextgen-web-herolandscape-1920x',
																},

													},
											},

							  },

					'BRAND'		: {
								'PATH'		:	'brands',
								'QUERY_PARAMS' 	: 	{},
								'SELECTION'	:	'{data{id,channelId,agofCodes,metadata{%s}}}',
								'TEXTS'		:	{'title' : 'main', 'description' : 'seo'},
								'ART'		:	{'BRAND_LOGO'  : {
													'icon'   	: 'profile:nextgen-web-artlogo-183x75',
													'thumb'  	: 'profile:original',
													'clearlogo'	: 'profile:nextgen-web-artlogo-183x75',
												},
											},
							  },

					'TVSHOW'	: {
								'PATH'		:	'tvshows',
								'QUERY_PARAMS' 	: 	{
												'channelId'		: '##channelId##',
												'limit'			: '5000',
												'skip'			: '0',
											},

								'SELECTION'	: '{totalCount,data{id,type,startTime,endTime,metadata{%s{ageRatings,copyrights,numberOfSeasons,seasons,id,genres,images{type,url,accentColors},type,titles,descriptions}},brand,channelId,tvShow,season,episode,status}}',

								'INFOLABELS'	:	{
												'mediatype': 'tvshow',
											},


								'TEXTS'		:	{'title' : 'main', 'description' : 'main'},
								'ART'		:	{'PRIMARY'        : {'thumb'  : 'profile:original'},
											 'ART_LOGO'       : {
														'icon'   	: 'profile:nextgen-web-artlogo-183x75',
														'clearlogo'	: 'profile:nextgen-web-artlogo-183x75',
													    },
											 'HERO_LANDSCAPE' : {'fanart' : 'profile:nextgen-web-herolandscape-1920x'},
											 'HERO_PORTRAIT'  : {'poster' : 'profile:nextgen-webphone-heroportrait-563x'},
											},

							  },
					'EPG'		: {
								'PATH'		: 'epg',
								'QUERY_PARAMS'	: {
											'skip'	 	: '0',
											'from'	 	: '##from##',
											'to'	 	: '##to##',
											'sortBy' 	: 'startTime',
											'sortAscending'	: 'true',
											'limit'		: '5000',
										  },
								'SELECTION'	: '{totalCount,data{id,title,description,tvShow,type,tvChannelName,channelId,startTime,endTime,video,images}}',
								'IMG_PROFILE'	: 'profile:original',
							  },
					'FETCH'		: {	'PATH'		: 'fetch/',
								'QUERY_PARAMS'	: {},
								'SELECTION'	: '{data{id,visibilities, channelId ,agofCodes,duration,metadata{%s}}}',

								'INFOLABELS'	:	{
												'mediatype': 'tvshow',
											},


								'TEXTS'		:	{'title' : 'main', 'description' : 'main'},
								'ART'		:	{'PRIMARY'        : {'thumb'  : 'profile:original'},
											 'ART_LOGO'       : {
														'icon'   	: 'profile:nextgen-web-artlogo-183x75',
														'clearlogo'	: 'profile:nextgen-web-artlogo-183x75',
													    },
											 'HERO_LANDSCAPE' : {'fanart' : 'profile:nextgen-web-herolandscape-1920x'},
											 'HERO_PORTRAIT'  : {'poster' : 'profile:nextgen-webphone-heroportrait-563x'},
											},
							  },
					'TVSHOWS'	: {	'PATH'		: 'tvshows',
								'QUERY_PARAMS'	: {
											'ids' 	: '##ids##',
											'limit'	: '5000',
										},
								'SELECTION'	: '{totalCount,data{id,type,startTime,endTime,metadata{%s{ageRatings,copyrights,numberOfSeasons,seasons,id,genres,images{type,url,accentColors},type,titles,descriptions}},brand,channelId,tvShow,season,episode,status}}',

								'INFOLABELS'	:	{
												'mediatype': 'tvshow',
											},


								'TEXTS'		:	{'title' : 'main', 'description' : 'main'},
								'ART'		:	{'PRIMARY'        : {'thumb'  : 'profile:original'},
											 'ART_LOGO'       : {
														'icon'   	: 'profile:nextgen-web-artlogo-183x75',
														'clearlogo'	: 'profile:nextgen-web-artlogo-183x75',
													    },
											 'HERO_LANDSCAPE' : {'fanart' : 'profile:nextgen-web-herolandscape-1920x'},
											 'HERO_PORTRAIT'  : {'poster' : 'profile:nextgen-webphone-heroportrait-563x'},
											},
							  },
					'SEASONS'	: {
								'PATH'	      	: 	'seasons',
								'QUERY_PARAMS' 	: 	{	'ids'	: '##ids##',
												'limit'	: '5000',

											},
								'SELECTION'	:	'{data{id,channelId,visibilities,duration,tvShow,metadata{%s}}}',
								'TEXTS'		:	{'title' : 'main', 'description' : 'main'},

								'INFOLABELS'	:	{
												'mediatype': 'season',
											},


								'ART'		:	{},
								'SUBTYPE_ART'	:	{
												'tvShow' : {
														'cover'		: {
																	'fanart'   	: 'profile:nextgen-web-herolandscape-1920x',
																},
														'teaser'	: {
																	'thumb'		: 'profile:nextgen-webphone-heroportrait-563x',
																},
														'heroLandscape' : {
																	'fanart'   	: 'profile:nextgen-web-herolandscape-1920x',
																},
														'primary'	: {
																	'thumb'		: 'profile:nextgen-webphone-heroportrait-563x',
																},
														'heroPortrait' : {
																	'poster' 	: 'profile:nextgen-webphone-heroportrait-563x',
																},
													},
											},
							  },

				  },
	'EPG'			: {
					'REQUEST_HOURS'		: 20,
					'REQUEST_OFFSET_HOURS'	: 10,
				  },

	'CACHE_DIR'		: 'cache',
	'TEMP_DIR'		: 'tmp',
	'DATA_DIR'		: 'data',
	'CACHE'			: {
					'CONFIG'	: { 'key' : 'config', 'expires' : 3600 },
					'EPG'		: { 'key' : 'epg', 'expires': 36000 },
					'BRANDS'	: { 'key' : 'brands', 'expires' : 36000 },
				  },
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
	}

}
