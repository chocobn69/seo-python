#!/usr/bin/python
import sys
import MySQLdb
import ConfigParser
import urllib2
from BeautifulSoup import *
from multiprocessing import Pool
from multiprocessing import TimeoutError
from multiprocessing import Manager
import gc

class Crawler():
	idSite = -1
	def __init__(self,hostdb,userdb,passworddb,namedb,idSite):
		self.idSite = idSite
		self.db = MySQLdb.connect (host = hostdb,
			user = userdb,
			passwd = passworddb,
			db = namedb)
		self.curs = self.db.cursor()

	def __del__(self):
		self.curs.close()
		self.db.close()

	def getSite(self):
		self.curs.execute("SELECT nom_site,url_site FROM sites WHERE pk_id_site = %s;",(self.idSite,)
		sites = self.curs.fetchall()
		urlSite = sites[0][1]
		return urlSite
	
	def addPage(self,urlPage):
		self.curs.execute("INSERT IGNORE INTO pages(pk_id_site,url_page,create_date_page) VALUES(%s,%s,NOW());",
			(str(self.idSite),self.db.escape_string(str(urlPage))) )

	def addLink(self,link,text,idPage):
		self.curs.execute("INSERT IGNORE INTO outlinks(url_link,text_link,pk_id_page) VALUES(%s,%s,%s);",
			(self.db.escape_string(str(link)),self.db.escape_string(str(text)),idPage) )

	def markCrawledPage(self,idPage):
		self.curs.execute("UPDATE pages SET crawled = 1 WHERE pk_id_page = %s;",
			(str(idPage),) )

	def findPage(self,crawled):
		self.curs.execute("SELECT url_page,pk_id_page FROM pages WHERE crawled = %s AND pk_id_site = %s ORDER BY RAND() LIMIT 1;",
			(str(crawled),str(idSite)) )
		page = self.curs.fetchone()
		return page

	def spider(self,url):
		print 'spidering '+url
		f = urllib2.urlopen(url)
		html = f.read()
		parser = BeautifulSoup(html)
		result = parser.findAll('a')
		results = dict()
		for link in result:
			try:
				href = link['href']
				text = link.contents[0]
				results[href] = text
			except:
				continue
		return results

	def crawl(self):		

		# Gets the site we want to crawl
		urlSite = self.getSite()

		# Add a page from this site, this is the root page obviously
		self.addPage(urlSite)

		# find a page
		page = self.findPage(0)
		while page != None:
			urlPage = page[0]
			idPage = page[1]

			# crawl current page
			try:
				links = self.spider(urlPage)
			except:
				self.markCrawledPage(idPage)
				# gets a new page
				page = self.findPage(0)
				continue
	
			# found links ?
			for link in links.keys():
				try:
					link = link.strip()
					# find link text
					text = links[link]
					# insert new out link
					self.addLink(link,text,idPage)

					# I dont want anchor
					if "#" in link or "mailto:" in link:
						continue
	
					if link.startswith(urlSite):
						# insert internal pages
						self.addPage(link)
					elif not link.startswith("http"):
						# insert internal pages
						if link.startswith("/"):
							self.addPage(urlSite+link)
						else:
							self.addPage(urlSite+"/"+link)
				except:
					text = 'unknown'
			# finaly, mark this page crawled
			self.markCrawledPage(idPage)

			# free some memory
			gc.collect()
			
			# gets a new page
			page = self.findPage(0)

def crawl_launch(hostdb,userdb,passworddb,namedb,idSite):
	crawler = Crawler(hostdb,userdb,passworddb,namedb,idSite)
	crawler.crawl()

if sys.argv[1] != None:
	idSite = sys.argv[1]
	
	# gets config param
	config = ConfigParser.RawConfigParser()
	config.read('../includes/init.cfg')
	hostdb = config.get('MySQL','hostdb')
	userdb = config.get('MySQL','userdb')
	passworddb = config.get('MySQL','passworddb')
	namedb = config.get('MySQL','namedb')

	# gets nb workrers we want to run
	nbWorker = int(config.get('crawler','nbWorker'))

	pool = Pool(nbWorker)

	try:
		results = [pool.apply_async(crawl_launch,[hostdb,userdb,passworddb,namedb,idSite]) for cptPool in range(nbWorker)]
		for res in results:
			res.get()
	finally:
		pool.close()
		pool.join()

