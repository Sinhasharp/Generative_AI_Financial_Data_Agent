import pymongo

CONNECTION_STRING = "mongodb://localhost:27018/"

try:
    client = pymongo.MongoClient(CONNECTION_STRING, serverSelectionTimeoutMS=5000)
    
    client.server_info() 
    print("MongoDB connection successful!")
    
    db_list = client.list_database_names()
    print("Databases found:")
    print(db_list)

except pymongo.errors.ServerSelectionTimeoutError as err:
    print(f"MongoDB connection failed: {err}")
    print("\nPlease ensure MongoDB is running on localhost:27017.")
except Exception as e:
    print(f"An error occurred: {e}")