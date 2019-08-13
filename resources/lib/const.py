#!/usr/bin/python
# -*- coding: utf-8 -*-

CONST = {
	'BASE_URL' 		: 'https://www.joyn.de',
	'PSF_CONFIG_URL'	: 'https://psf.player.v0.maxdome.cloud/config/psf.json',
	'PSF_URL'		: 'https://psf.player.v0.maxdome.cloud/dist/playback-source-fetcher.min.js',
	'MIDDLEWARE_URL'	: 'https://middleware.p7s1.io/joyn/v1/',
	'ENTITLEMENT_URL'	: 'entitlement-token/anonymous',
	'PSF_VARS_IDX'		: {
					'SECRET' : 1184
				  },

	'PATH'			: {

					'SEASON'	: {
								'PATH'	      	: 	'seasons',
								'QUERY_PARAMS' 	: 	{	'tvShowId' 		: '##tvShowId##',
												'sortBy'   		: 'seasonsOrder',
												'sortAscending'		: 'true',

											},
								'SELECTION'	:	'{data{id,channelId,visibilities,duration,metadata{de}}}',
								'TEXTS'		:	{'title' : 'main', 'description' : 'main'},
								'ART'		:	{},
							  },

					'VIDEO'		: {
								'PATH'	      	: 	'videos',
								'QUERY_PARAMS' 	: 	{	'tvShowId' 		: '##tvShowId##',
												'seasonId'   		: '##seasonId##',
												'sortBy'		: 'seasonsOrder',
												'sortAscending'		: 'true',
												'skip'			: '0',
											},
								'SELECTION'	:	'{totalCount,data{id,type,startTime,endTime,agofCode,path(context:"web", region:"de", type:"cmsPath"){path},tvShow,season,episode,duration,metadata{de},visibilities{endsAt}}}',
								'TEXTS'		:	{'title' : 'main', 'description' : 'main'},
								'ART'		:	{'PRIMARY'        : {'thumb'  : 'profile:original'},
											 'ART_LOGO'       : {'icon'   : 'profile:nextgen-web-artlogo-183x75'},
											 'HERO_LANDSCAPE' : {'fanart' : 'profile:nextgen-web-herolandscape-1920x'},
											 'HERO_PORTRAIT'  : {'poster' : 'profile:nextgen-webphone-heroportrait-563x'},
											},

							  },

					'BRAND'		: {
								'PATH'		:	'brands',
								'QUERY_PARAMS' 	: 	{},
								'SELECTION'	:	'{data{id,channelId,agofCodes,metadata{de}}}',
								'TEXTS'		:	{'title' : 'main', 'description' : 'seo'},
								'ART'		:	{'BRAND_LOGO'  : {
													'icon'   : 'profile:nextgen-web-artlogo-183x75',
													'thumb'  : 'profile:original',
												},
											},
							  },

					'TVSHOW'	: {
								'PATH'		:	'tvshows',
								'QUERY_PARAMS' 	: 	{
												'channelId'		: '##channelId##',
												'limit'			: '250',
												'skip'			: '0',
											},
								'SELECTION'	:	'{totalCount,data{id,type,startTime,endTime,metadata{de{ageRatings,copyrights ,numberOfSeasons,seasons,id,genres,images{type,url,accentColors},seo,channelObject{classIdentifier,bundleId},type,bundleId,classIdentifier,titles,descriptions}},baseUrl,path(context:"web", region:"de", type:"cmsPath"),brand,channelId,tvShow,season,episode,status}}',
								'TEXTS'		:	{'title' : 'main', 'description' : 'main'},
								'ART'		:	{'PRIMARY'        : {'thumb'  : 'profile:original'},
											 'ART_LOGO'       : {'icon'   : 'profile:nextgen-web-artlogo-183x75'},
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
								'SELECTION'	: '{totalCount,data{id,title,description,tvShow,type,tvChannelName,channelId,startTime,endTime,video,images(subType:"cover"){url,subType}}}',
								'IMG_PROFILE'	: 'profile:original',
							  },
					'FETCH'		: {	'PATH'		: 'fetch/',
								'QUERY_PARAMS'	: {},
								'SELECTION'	: '{data{id,visibilities, channelId ,agofCodes,duration,metadata{de}}}',
								'TEXTS'		:	{'title' : 'main', 'description' : 'main'},
								'ART'		:	{'PRIMARY'        : {'thumb'  : 'profile:original'},
											 'ART_LOGO'       : {'icon'   : 'profile:nextgen-web-artlogo-183x75'},
											 'HERO_LANDSCAPE' : {'fanart' : 'profile:nextgen-web-herolandscape-1920x'},
											 'HERO_PORTRAIT'  : {'poster' : 'profile:nextgen-webphone-heroportrait-563x'},
											},
							  },
					'TVSHOWS'	: {	'PATH'		: 'tvshows',
								'QUERY_PARAMS'	: {
											'ids' 	: '##ids##',
											'limit'	: '1000',
										},
								'SELECTION'	: '{totalCount,data{id,type,startTime,endTime,metadata{de{ageRatings,copyrights ,numberOfSeasons,seasons,id,genres,images{type,url,accentColors},seo,channelObject{classIdentifier,bundleId},type,bundleId,classIdentifier,titles,descriptions}},baseUrl,path(context:"web", region:"de", type:"cmsPath"),brand,channelId,tvShow,season,episode,status}}',
								'TEXTS'		:	{'title' : 'main', 'description' : 'main'},
								'ART'		:	{'PRIMARY'        : {'thumb'  : 'profile:original'},
											 'ART_LOGO'       : {'icon'   : 'profile:nextgen-web-artlogo-183x75'},
											 'HERO_LANDSCAPE' : {'fanart' : 'profile:nextgen-web-herolandscape-1920x'},
											 'HERO_PORTRAIT'  : {'poster' : 'profile:nextgen-webphone-heroportrait-563x'},
											},
							  },
					'SEASONS'	: {
								'PATH'	      	: 	'seasons',
								'QUERY_PARAMS' 	: 	{	'ids'	: '##ids##',
												'limit'	: '1000',

											},
								'SELECTION'	:	'{data{id,channelId,visibilities,duration,metadata{de}}}',
								'TEXTS'		:	{'title' : 'main', 'description' : 'main'},
								'ART'		:	{},
							  },

				  },
	'EPG'			: {
					'REQUEST_HOURS'		: 20,
					'REQUEST_OFFSET_HOURS'	: 10,
				  },
	'TEXT_TEMPLATES'	: {
					'LIVETV_TITLE'		: '[B]{:s}[/B] - {:s}',
					'LIVETV_UNTIL'		: '[CR]bis {:%H:%M} Uhr[CR][CR]',
					'LIVETV_UNTIL_AND_NEXT'	: '[CR]bis {:%H:%M} Uhr, danach {:s}[CR][CR]',
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
	'INPUTSTREAM_ADDON'	: 'inputstream.adaptive',

}
