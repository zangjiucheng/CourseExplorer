import os

from ..Utils.manageDBClass import connectDB

# Default public read-only MongoDB URI; override with MONGODB_URI env var.
DEFAULT_MONGODB_URI = (
    "mongodb+srv://user:hCk2I9rMak6dMKpf@uwdatabase.kcmy6ok.mongodb.net/"
    "?retryWrites=true&w=majority"
)


class dbClass:
    def __init__(self):
        self.ClassCollectionName = "Class2024Winter"

        # Fall back to the default when MONGODB_URI is unset OR set-but-empty
        # (e.g. `MONGODB_URI=` in a .env / compose file), which os.environ.get
        # with a default would otherwise pass through as an empty string.
        self.url = (os.environ.get("MONGODB_URI") or "").strip() or DEFAULT_MONGODB_URI

        self.ClassDATABASE = connectDB(mongo_host=self.url)
        self.ClassDATABASE.connectDataBase('UWRegistrationDB')
        self.ClassDATABASE.selectCollection(self.ClassCollectionName)
        self.ClassSchedule = self.ClassDATABASE.mongo_collection

        self.CourseDetailDB = connectDB(mongo_host=self.url)
        self.CourseDetailDB.connectDataBase("UWRegistrationDB")
        self.CourseDetailDB.selectCollection("CourseDetail")
        self.CourseDescribe = self.CourseDetailDB.mongo_collection

    def switchCollection(self, collectionName):
        self.ClassCollectionName = collectionName
        self.ClassDATABASE.selectCollection(self.ClassCollectionName)
        self.ClassSchedule = self.ClassDATABASE.mongo_collection

    def listClassCollections(self):
        collections = self.ClassDATABASE.listCollections()
        term_order = {"Winter": 0, "Spring": 1, "Fall": 2}

        def sort_key(name):
            if not name.startswith("Class"):
                return (9999, 99, name)
            tail = name[len("Class") :]
            year = tail[:4]
            term = tail[4:]
            try:
                year_value = int(year)
            except ValueError:
                year_value = 9999
            term_value = term_order.get(term, 99)
            return (year_value, term_value, name)

        class_names = [name for name in collections if name.startswith("Class")]
        return sorted(class_names, key=sort_key, reverse=True)
