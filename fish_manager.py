
class FishManager():
    def __init__(self):
        self.fishes = list()

    def testFill(self):
        self.fishes.clear()
        for i in range(10):
            self.fishes.append(FishEntry("Fish " + str(i)))

class FishEntry():
    def __init__(self, id):
        self.id = id