#!/usr/bin/python
import sys
import MySQLdb
import ConfigParser
import urllib2
from multiprocessing import Pool
from multiprocessing import TimeoutError
from multiprocessing import Manager

class PageRank():
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

	def findPages(self):
		self.curs.execute("SELECT pk_id_page,url_page FROM pages WHERE pk_id_site = %s and pagerank_google IS NULL ORDER BY RAND();",
			(self.idSite,))
		pages = self.curs.fetchall()
		return pages

	def updateRank(self,rank,idpage):
		self.curs.execute("UPDATE pages SET pagerank_google = %s WHERE pk_id_page = %s;",
			(rank,idpage))

	def get_pagerank(self,url):
		hsh = self.check_hash(self.hash_url(url))
		gurl = 'http://www.google.com/search?client=navclient-auto&features=Rank:&q=info:%s&ch=%s' % (urllib2.quote(url), hsh)
		try:
			proxy_support = urllib2.ProxyHandler({"http" : "127.0.0.1:8123"})
			opener = urllib2.build_opener(proxy_support)
			opener.addheaders = [('User-agent', 'Mozilla/5.0')]
			f = opener.open(gurl)
			rank = f.read().strip()[9:]
		except Exception as error:
			rank = -1
		if rank == '':
			rank = 0
		return rank

	def int_str(self,string, integer, factor):
		for i in range(len(string)) :
			integer *= factor
			integer &= 0xFFFFFFFF
			integer += ord(string[i])
		return integer

	def hash_url(self,string):
		c1 = self.int_str(string, 0x1505, 0x21)
		c2 = self.int_str(string, 0, 0x1003F)

		c1 >>= 2
		c1 = ((c1 >> 4) & 0x3FFFFC0) | (c1 & 0x3F)
		c1 = ((c1 >> 4) & 0x3FFC00) | (c1 & 0x3FF)
		c1 = ((c1 >> 4) & 0x3C000) | (c1 & 0x3FFF)

		t1 = (c1 & 0x3C0) << 4
		t1 |= c1 & 0x3C
		t1 = (t1 << 2) | (c2 & 0xF0F)

		t2 = (c1 & 0xFFFFC000) << 4
		t2 |= c1 & 0x3C00
		t2 = (t2 << 0xA) | (c2 & 0xF0F0000)

		return (t1 | t2)

	def check_hash(self,hash_int):
		hash_str = '%u' % (hash_int)
		flag = 0
		check_byte = 0

		i = len(hash_str) - 1
		while i >= 0:
			byte = int(hash_str[i])
			if 1 == (flag % 2):
				byte *= 2;
				byte = byte / 10 + byte % 10
			check_byte += byte
			flag += 1
			i -= 1

		check_byte %= 10
		if 0 != check_byte:
			check_byte = 10 - check_byte
			if 1 == flag % 2:
				if 1 == check_byte % 2:
					check_byte += 9
				check_byte >>= 1
		return '7' + str(check_byte) + hash_str

	def getPr(self):
		# find a page
		pages = self.findPages()
		for idpage,urlpage in pages:
			rank = self.get_pagerank(urlpage)
			self.updateRank(rank,idpage)


def pagerank_launch(hostdb,userdb,passworddb,namedb,idSite):
	pageranker = PageRank(hostdb,userdb,passworddb,namedb,idSite)
	pageranker.getPr()

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
	nbWorker = int(config.get('pagerank','nbWorker'))

	pagerank_launch(hostdb,userdb,passworddb,namedb,idSite)