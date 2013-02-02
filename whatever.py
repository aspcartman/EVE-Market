from dateutil.parser import parse
import datetime
import MySQLdb
from datetime import datetime
import gevent
from gevent.pool import Pool
from gevent import monkey; gevent.monkey.patch_all()
import zmq.green as zmq
import zlib
import eve_types



def arrayList(array): # ['a','b','c'] -> a,b,c
    length = len(array)
    result = '%s' % array[0]
    for x in xrange(1, length):
        result += ', %s' % array[x]
    return result

def arrayOpen(array): # ((a,),(b,)) -> (a,b)
    result = []
    for x in array:
        result.append(x[0])
    return result

def formDict(keys,values):
    if (len(keys) != len(values)):
        return 0
    result = {}
    for x in xrange(len(keys)):
        result[keys[x]] = values[x]
    return result


# bid = 0 - sell, can buy
# bid = 1 - buy, can sell

    
class DatabaseDelegate:
    cursor = object()

    def __init__(self):
        db = MySQLdb.connect(host="192.168.0.111", user="aspcartman", passwd="vicevice",db="EVE")
        self.cursor = db.cursor()


    def runQueryR(self,query):
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def getBuyOrdersAroundSSForItem(self,typeID,solarSystemID): #Founds every buy order around a solarSystem
        sqlQuery = "SELECT `orderID`,`price`,`solarSystemID` FROM  `emdrOrders` WHERE (`typeID` = %d && `solarSystemID` != %d && `bid` = 1) ORDER BY `price` DESC" % (typeID,solarSystemID)
        data = self.runQueryR(sqlQuery)
        return data
    def getBuyOrdersInSSForItem(self,typeID,solarSystemID): #Founds every buy order in a solarSystem
        sqlQuery = "SELECT `orderID`,`price`,`solarSystemID` FROM  `emdrOrders` WHERE (`typeID` = %d && `solarSystemID`  = %d && `bid` = 1) ORDER BY `price` DESC" % (typeID,solarSystemID)
        data = self.runQueryR(sqlQuery)
        return data
    def getSellOrdersAroundSSForItem(self,typeID,solarSystemID): #Founds every sell order around a solarSystem
        sqlQuery = "SELECT `orderID`,`price`,`solarSystemID` FROM  `emdrOrders` WHERE (`typeID` = %d && `solarSystemID` != %d && `bid` = 0) ORDER BY `price`" % (typeID,solarSystemID)
        data = self.runQueryR(sqlQuery)
        return data
    def getSellOrdersInSSForItem(self,typeID,solarSystemID): #Founds every sell order in a solarSystem
        sqlQuery = "SELECT `orderID`,`price`,`solarSystemID` FROM  `emdrOrders` WHERE (`typeID` = %d && `solarSystemID`  = %d && `bid` = 0) ORDER BY `price`" % (typeID,solarSystemID)
        data = self.runQueryR(sqlQuery)
        return data

    # def getBuyOrdersAroundSSs(self,typeID,solarSystemsID): #Founds every buy order around a solarSystem
    #     sqlQuery = "SELECT orderID,price FROM  emdrOrders WHERE (typeID = %d && solarSystemID != %s && bid = 1)" % (typeID,solarSystemID)
    #     data = self.runQueryR(sqlQuery)
    #     return data
    # def getBuyOrdersInSSs(self,typeID,solarSystemsID): #Founds every buy order in a solarSystem
    #     sqlQuery = "SELECT orderID,price FROM  emdrOrders WHERE (typeID = %d && solarSystemID = %s && bid = 1)" % (typeID,solarSystemID)
    #     data = self.runQueryR(sqlQuery)
    #     return data
    # def getSellOrdersAroundSSs(self,typeID,solarSystemsID): #Founds every sell order around a solarSystem
    #     sqlQuery = "SELECT orderID,price FROM  emdrOrders WHERE (typeID = %d && solarSystemID != %s && bid = 0)" % (typeID,solarSystemID)
    #     data = self.runQueryR(sqlQuery)
    #     return data
    # def getSellOrdersInSSs(self,typeID,solarSystemsID): #Founds every sell order in a solarSystem
    #     sqlQuery = "SELECT orderID,price FROM  emdrOrders WHERE (typeID = %d && solarSystemID = %s && bid = 0)" % (typeID,solarSystemID)
    #     data = self.runQueryR(sqlQuery)
    #     return data

    def getSSAroundSS(self,solarSystemID):
        sqlQuery = "SELECT toSolarSystemID FROM mapSolarSystemJumps WHERE fromSolarSystemID = %s" % solarSystemID
        data = self.runQueryR(sqlQuery)
        ssids = []
        for array in data:
            ssids.append(array[0])
        return ssids

    # Get all items, that has sell orders in current SS and buy surrounding ones
    def getUrgentItems(self,solarSystemID):
        ssAround = self.getSSAroundSS(solarSystemID)
        #Should return all 
        sqlQuery = "(SELECT DISTINCT `typeID`,`solarSystemID` FROM `emdrOrders` WHERE (`typeID` IN \
                    (SELECT DISTINCT `typeID` FROM `emdrOrders` WHERE (`solarSystemID` = %d && `BID` = 0))) AND (`solarSystemID` IN (%s) && `BID` = 1))"\
                        % (solarSystemID,arrayList(ssAround))
        data = self.runQueryR(sqlQuery)
        return data

    def getItemsNames(self,itemTypeIDs):
        sqlQuery = "SELECT `typeID`,`typeName` FROM `invTypes` WHERE `typeID` IN (%s)" % arrayList(itemTypeIDs)
        print sqlQuery
        data = self.runQueryR(sqlQuery)
        return data

    def maxProfit1Item(self,typeID,buySS,sellSS):
        sellOrders = self.getSellOrdersInSSForItem(typeID,buySS)
        buyOrders = self.getBuyOrdersInSSForItem(typeID,sellSS)
        return buyOrders[0][1] - sellOrders[0][1]



def printByLine(array):
    for x in array:
        print x


def main():
    db = DatabaseDelegate()

    solarSystemID = 30002187
    money = 17020291.76
    volume = 5280.0
    typeID = 25603

    # Items that we can check in form of [[type,systemID], ...]
    urgentItems = db.getUrgentItems(solarSystemID)
    print urgentItems
    # For every item we get buy/sell orders
    for item in urgentItems:
        profit = db.maxProfit1Item(item[0],solarSystemID,item[1])
        if profit > 0:
            print profit
    # print urgentItems
   


 
if __name__ == '__main__':
    main()
    


