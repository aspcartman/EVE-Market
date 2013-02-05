import eve

def main():
    db = eve.DatabaseDelegate()

    solarSystemID = 30002510
    money = 17020291.76
    volume = 5280.0
    typeID = 25603
    
    # db.getAllOrdersInRadius(solarSystemID,2)
    db.getDealsAroundSS(solarSystemID,10)

    
if __name__ == '__main__':
    main()